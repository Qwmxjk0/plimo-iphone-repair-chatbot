"""Indexes approved facts; explicitly include labeled demo records for demo mode."""
import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path
import httpx

# Words customers actually type, so a short item chunk matches everyday phrasing.
SEARCH_WORDS = [('หน้าจอ', 'จอแตก จอเสีย จอเป็นเส้น ทัชไม่ได้ เปลี่ยนจอ'), ('แบตเตอรี่', 'แบต แบตเสื่อม แบตหมดไว แบตบวม เปลี่ยนแบต'),
                ('ช่องชาร์จ', 'ชาร์จไม่เข้า ช่องชาร์จสกปรก รูชาร์จ'), ('ลำโพง', 'เสียงแตก เสียงเบา ลำโพงเสีย'),
                ('กล้องหลัง', 'กล้องเบลอ กล้องเสีย กล้องหลังแตก'), ('ฟิล์ม', 'กระจกกันรอย ฟิล์มกันรอย'),
                ('เคสใส', 'เคสกันกระแทก เคสมือถือ'), ('Lightning', 'สายชาร์จ สายไลท์นิ่ง'), ('USB-C', 'สายชาร์จ สาย Type-C')]

def catalog_text(item):
    """One short, specific chunk per item: shared policy text lives once in knowledge/shop.md."""
    models = item.get('models') or []
    base_only = models and not any('Pro' in m for m in models)
    lines = [item['name'], 'ประเภท: ' + ('บริการซ่อม' if item.get('kind') == 'service' else 'สินค้าอุปกรณ์เสริม')]
    if isinstance(item.get('price'), (int, float)):
        label = 'ราคาประเมินเบื้องต้นเริ่มต้น' if item.get('price_status') == 'estimate' else 'ราคา'
        lines.append(f"{label} {item['price']:,} บาท")
    if models:
        lines.append('รุ่นที่รองรับ: ' + ', '.join(models) + (' (ไม่รวม Pro / Pro Max ซึ่งต้องประเมินแยก)' if base_only else ''))
    lines.append('รายละเอียด: ' + item['description'])
    words = ' '.join(w for key, w in SEARCH_WORDS if key in item['name'])
    if words:
        lines.append('คำที่ลูกค้าใช้: ' + words)
    return '\n'.join(lines)

def catalog_documents(catalog, include_demo=False):
    texts, sources = [], []
    for item in catalog:
        demo = item.get('demo') is True
        if (item.get('confirmed') is True and not demo) or (demo and include_demo):
            if not item.get('name') or not item.get('description'):
                raise ValueError('Catalog entries need name and description')
            prefix = 'ข้อมูลสาธิตเท่านั้น ต้องบอกว่าเป็นราคาสาธิต ไม่ใช่ราคาจริงของร้าน ไม่รับจองหรือยืนยันสต็อก\n' if demo else ''
            texts.append(prefix + catalog_text(item))
            sources.append(('demo-' if demo else '') + item['id'] + '.json')
    return texts, sources

def markdown_sections(text, name):
    """Split a knowledge file at '## ' headings so each topic is its own retrievable document."""
    title, parts, current = '', [], []
    for line in text.splitlines():
        if line.startswith('# ') and not title:
            title = line
        elif line.startswith('## ') and current:
            parts.append(current); current = [line]
        else:
            current.append(line)
    parts.append(current)
    stem = name.rsplit('.', 1)[0]
    bodies = [(title + '\n' + '\n'.join(p)).strip() for p in parts if '\n'.join(p).strip()]
    return bodies, [f'{stem}-{i + 1}.md' for i in range(len(bodies))]

BUSY = ('pending', 'parsing', 'analyzing', 'processing', 'preprocessed')

def plan(counts):
    """What a deploy should do for the knowledge base, from LightRAG's status counts.
    'submit' sends every document (already-indexed ones are skipped for free), 'retry'
    reprocesses failed ones, 'wait' lets running work finish. Nothing here calls OpenAI."""
    if any(counts.get(k, 0) for k in BUSY):
        return 'wait'
    if counts.get('failed', 0):
        return 'retry'
    return 'submit'

def documents():
    texts, sources = [], []
    for path in sorted(Path('/app/knowledge').glob('*.md')):
        section_texts, section_sources = markdown_sections(path.read_text(), path.name)
        texts.extend(section_texts); sources.extend(section_sources)
    catalog = json.loads(Path('/app/catalog.json').read_text())
    catalog_texts, catalog_sources = catalog_documents(catalog, include_demo='--include-demo' in sys.argv)
    texts.extend(catalog_texts)
    sources.extend(catalog_sources)
    # Content hash in the name: a changed section is a new document; changed knowledge still needs a NEW RAG volume to drop old text.
    return texts, [hashlib.sha256(text.encode()).hexdigest()[:12] + '-' + source for text, source in zip(texts, sources)]

async def submit(client, base, headers, texts, sources):
    url = base + '/documents/texts'
    response = await client.post(url, headers=headers, json={'texts': texts, 'file_sources': sources})
    if response.status_code != 409:
        response.raise_for_status()
        return len(texts)
    # Some documents are already indexed: send one by one, duplicates are refused without any model call.
    added = 0
    for text, source in zip(texts, sources):
        one = await client.post(url, headers=headers, json={'texts': [text], 'file_sources': [source]})
        if one.status_code != 409:
            one.raise_for_status(); added += 1
    return added

async def counts(client, base, headers):
    r = await client.get(base + '/documents/status_counts', headers=headers)
    r.raise_for_status()
    return r.json()['status_counts']

async def main():
    key = os.environ.get('LIGHTRAG_API_KEY')
    if not key or not os.environ.get('OPENAI_API_KEY'):
        raise SystemExit('Set OPENAI_API_KEY and LIGHTRAG_API_KEY in .env first')
    base, headers = os.getenv('LIGHTRAG_URL', 'http://lightrag:9621'), {'X-API-Key': key}
    ensure = '--ensure' in sys.argv
    texts, sources = documents()
    async with httpx.AsyncClient(timeout=120) as client:
        action, added = (plan(await counts(client, base, headers)) if ensure else 'submit'), 0
        if action == 'retry':
            (await client.post(base + '/documents/reprocess_failed', headers=headers)).raise_for_status()
            print('Retrying documents that failed before (for example while OpenAI credit was empty).')
        elif action == 'submit':
            added = await submit(client, base, headers, texts, sources)
            print(json.dumps({'documents': len(texts), 'added': added, 'already_indexed': len(texts) - added}, ensure_ascii=False))
        if not ensure:
            print('Submission is asynchronous. Check LightRAG document status before testing chat.')
            return
        # --ensure: wait until LightRAG has finished, and fail loudly if anything did not index.
        # LightRAG starts work in the background: right after a submit or retry the counts may not move yet,
        # so "idle" only counts once work was seen or after a grace period.
        started, queued = time.monotonic(), action == 'retry' or added > 0
        deadline = started + int(os.getenv('INGEST_WAIT_SECONDS', '1500'))
        seen = False
        while True:
            c = await counts(client, base, headers)
            busy = sum(c.get(k, 0) for k in BUSY)
            seen = seen or busy > 0
            if (not busy and (seen or not queued or time.monotonic() - started > 45)) or time.monotonic() > deadline:
                break
            print(f"  indexing: {c.get('processed', 0)}/{c.get('all', 0)} done", flush=True)
            await asyncio.sleep(15)
        print(json.dumps({'processed': c.get('processed', 0), 'failed': c.get('failed', 0), 'all': c.get('all', 0)}))
        if busy or c.get('failed', 0) or c.get('processed', 0) < len(texts):
            raise SystemExit('Knowledge base is NOT complete (check OpenAI credit, then deploy again: failed documents are retried).')

if __name__=='__main__':
    asyncio.run(main())
