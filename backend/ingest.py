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

async def prune(client, base, headers, sources):
    """Delete indexed sections that no longer exist in knowledge/ or the catalog (edited or removed),
    so an edit replaces text instead of leaving the old version searchable. Deleting costs no model call."""
    stale, page = [], 1
    while True:
        r = await client.post(base + '/documents/paginated', headers=headers, json={'page': page, 'page_size': 200})
        r.raise_for_status(); data = r.json()
        stale += [d['id'] for d in data['documents'] if d.get('file_path') not in sources]
        if not data['pagination'].get('has_next'):
            break
        page += 1
    if stale:
        (await client.request('DELETE', base + '/documents/delete_document', headers=headers, json={'doc_ids': stale})).raise_for_status()
    return len(stale)

async def counts(client, base, headers):
    r = await client.get(base + '/documents/status_counts', headers=headers)
    r.raise_for_status()
    return r.json()['status_counts']

async def indexed(client, base, headers):
    """file_path -> status for every document LightRAG holds."""
    out, page = {}, 1
    while True:
        r = await client.post(base + '/documents/paginated', headers=headers, json={'page': page, 'page_size': 200})
        r.raise_for_status(); data = r.json()
        out.update({d.get('file_path'): d.get('status') for d in data['documents']})
        if not data['pagination'].get('has_next'):
            return out
        page += 1

async def wait_idle(client, base, headers, deadline):
    """Until LightRAG's pipeline (indexing AND deletions) is idle. Status counts alone miss deletions."""
    await asyncio.sleep(2)
    last = 0
    while time.monotonic() < deadline:
        busy_pipeline = (await client.get(base + '/documents/pipeline_status', headers=headers)).json().get('busy')
        c = await counts(client, base, headers)
        if not busy_pipeline and not sum(c.get(k, 0) for k in BUSY):
            return True
        if time.monotonic() - last > 15:
            print(f"  indexing: {c.get('processed', 0)}/{c.get('all', 0)} done", flush=True); last = time.monotonic()
        await asyncio.sleep(5)
    return False

async def ensure(client, base, headers, texts, sources):
    """Make LightRAG hold exactly these documents, paying only for what is new or failed.
    Complete store: list + compare only, no model call. Returns the final file_path -> status map."""
    deadline = time.monotonic() + int(os.getenv('INGEST_WAIT_SECONDS', '1500'))
    wanted = dict(zip(sources, texts))
    for _ in range(3):
        await wait_idle(client, base, headers, deadline)
        if plan(await counts(client, base, headers)) == 'retry':
            (await client.post(base + '/documents/reprocess_failed', headers=headers)).raise_for_status()
            print('Retrying documents that failed before (for example while OpenAI credit was empty).')
            await wait_idle(client, base, headers, deadline)
        removed = await prune(client, base, headers, set(sources))
        if removed:
            print(f'Removed {removed} replaced section(s).')
            await wait_idle(client, base, headers, deadline)
        have = await indexed(client, base, headers)
        missing = [s for s in sources if s not in have]
        if not missing:
            break
        added = await submit(client, base, headers, [wanted[s] for s in missing], missing)
        print(f'Adding {added} new or changed section(s); {len(sources) - len(missing)} already indexed.')
        await wait_idle(client, base, headers, deadline)
    return await indexed(client, base, headers)

async def main():
    key = os.environ.get('LIGHTRAG_API_KEY')
    if not key or not os.environ.get('OPENAI_API_KEY'):
        raise SystemExit('Set OPENAI_API_KEY and LIGHTRAG_API_KEY in .env first')
    base, headers = os.getenv('LIGHTRAG_URL', 'http://lightrag:9621'), {'X-API-Key': key}
    texts, sources = documents()
    async with httpx.AsyncClient(timeout=120) as client:
        if '--ensure' not in sys.argv:
            added = await submit(client, base, headers, texts, sources)
            print(json.dumps({'documents': len(texts), 'added': added, 'already_indexed': len(texts) - added}, ensure_ascii=False))
            print('Submission is asynchronous. Check LightRAG document status before testing chat.')
            return
        have = await ensure(client, base, headers, texts, sources)
        missing = [s for s in sources if have.get(s) != 'processed']
        extra = [s for s in have if s not in set(sources)]
        print(json.dumps({'sections': len(sources), 'indexed': len(sources) - len(missing), 'not_indexed': missing[:5], 'stale': extra[:5]}, ensure_ascii=False))
        if missing or extra:
            raise SystemExit('Knowledge base is NOT complete (check OpenAI credit, then deploy again: failed documents are retried).')

if __name__=='__main__':
    asyncio.run(main())
