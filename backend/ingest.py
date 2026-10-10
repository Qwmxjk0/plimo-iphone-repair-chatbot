"""Indexes approved facts; explicitly include labeled demo records for demo mode."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import httpx

def catalog_documents(catalog, include_demo=False):
    texts, sources = [], []
    for item in catalog:
        demo = item.get('demo') is True
        if (item.get('confirmed') is True and not demo) or (demo and include_demo):
            if not item.get('name') or not item.get('description'):
                raise ValueError('Catalog entries need name and description')
            prefix = 'ข้อมูลสาธิตเท่านั้น ต้องบอกว่าเป็นราคาสาธิต ไม่ใช่ราคาจริงของร้าน ไม่รับจองหรือยืนยันสต็อก\n' if demo else ('ราคาประเมินเบื้องต้นที่เจ้าของอนุญาต ต้องตรวจเครื่องก่อนยืนยันราคาสุทธิและให้ลูกค้าอนุมัติค่าใช้จ่ายเพิ่มเติมก่อนเริ่มซ่อม\n' if item.get('price_status') == 'estimate' else 'ข้อมูลที่ร้านยืนยัน\n')
            texts.append(prefix + json.dumps(item, ensure_ascii=False))
            sources.append(('demo-' if demo else '') + item['id'] + '.json')
    return texts, sources

async def main():
    paths = sorted(Path('/app/knowledge').glob('*.md'))
    texts = [p.read_text() for p in paths]
    sources = [p.name for p in paths]
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
