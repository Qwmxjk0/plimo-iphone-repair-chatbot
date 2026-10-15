"""Indexes approved facts; explicitly include labeled demo records for demo mode."""
import asyncio
import hashlib
import json
import os
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

async def main():
    texts, sources = [], []
    for path in sorted(Path('/app/knowledge').glob('*.md')):
        section_texts, section_sources = markdown_sections(path.read_text(), path.name)
        texts.extend(section_texts); sources.extend(section_sources)
    catalog = json.loads(Path('/app/catalog.json').read_text())
    catalog_texts, catalog_sources = catalog_documents(catalog, include_demo='--include-demo' in __import__('sys').argv)
    texts.extend(catalog_texts)
    sources.extend(catalog_sources)
    key = os.environ.get('LIGHTRAG_API_KEY')
    if not key or not os.environ.get('OPENAI_API_KEY'):
        raise SystemExit('Set OPENAI_API_KEY and LIGHTRAG_API_KEY in .env first')
    # Use a NEW RAG workspace for changed knowledge to avoid obsolete policies.
    sources = [hashlib.sha256(text.encode()).hexdigest()[:12] + '-' + source for text, source in zip(texts,sources)]
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(os.getenv('LIGHTRAG_URL','http://lightrag:9621')+'/documents/texts', headers={'X-API-Key':key}, json={'texts':texts,'file_sources':sources})
        response.raise_for_status()
        result=response.json()
        print(json.dumps({'status':result.get('status'),'track_id':result.get('track_id'),'document_count':len(texts)},ensure_ascii=False))
        print('Submission is asynchronous. Check LightRAG document status before testing chat.')

if __name__=='__main__':
    asyncio.run(main())
