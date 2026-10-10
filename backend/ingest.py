"""Indexes confirmed records only; run manually after setting API keys."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import httpx

async def main():
    paths = sorted(Path('/app/knowledge').glob('*.md'))
    texts = [p.read_text() for p in paths]
    sources = [p.name for p in paths]
    catalog = json.loads(Path('/app/catalog.json').read_text())
    for item in catalog:
        if item.get('confirmed') is True:
            if not item.get('name') or not item.get('description'):
                raise ValueError('Confirmed catalog entries need name and description')
            texts.append(json.dumps(item, ensure_ascii=False))
            sources.append(item['id'] + '.json')
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
