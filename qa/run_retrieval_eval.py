"""Score LightRAG retrieval alone: does the right source come back, and how high?

    docker compose exec -T api python - < qa/run_retrieval_eval.py

Runs inside the api container (LightRAG is internal). Same query settings as the
app. Prints hit@1, hit@3, hit@5 and MRR, plus every miss, as Markdown.
"""
import os, time, httpx
from datetime import datetime, timedelta, timezone

MODE = os.getenv('RAG_MODE', 'naive')
PREFIX = os.getenv('RETRIEVE_PREFIX', '')
CASES = [
    ('ร้านเปิดกี่โมง', 'shop'), ('ร้านหยุดวันไหน', 'shop'), ('ตรวจเช็คเสียเงินไหม', 'shop'),
    ('รับซ่อมรุ่นไหนบ้าง', 'shop'), ('ซ่อมแล้วรับประกันกี่เดือน', 'shop'), ('ชำระเงินยังไง', 'shop'),
    ('ถ้ามีค่าอะไหล่เพิ่มต้องทำยังไง', 'shop'), ('อุปกรณ์เสริมมีของพร้อมขายไหม', 'shop'),
    ('เปลี่ยนหน้าจอ iPhone 11 ราคาเท่าไหร่', 'slot-1.json'), ('เปลี่ยนหน้าจอ iPhone 12 ราคาเท่าไหร่', 'slot-2.json'),
    ('เปลี่ยนหน้าจอ iPhone 13 ราคาเท่าไหร่', 'slot-3.json'), ('เปลี่ยนหน้าจอ iPhone 14 ราคาเท่าไหร่', 'slot-4.json'),
    ('เปลี่ยนหน้าจอ iPhone 15 ราคาเท่าไหร่', 'slot-5.json'), ('เปลี่ยนหน้าจอ iPhone 16 ราคาเท่าไหร่', 'slot-6.json'),
    ('เปลี่ยนหน้าจอ iPhone 17 ราคาเท่าไหร่', 'slot-7.json'), ('เปลี่ยนแบตเตอรี่ iPhone 12 ราคาเท่าไหร่', 'slot-8.json'),
    ('เปลี่ยนแบตเตอรี่ iPhone 16 ราคาเท่าไหร่', 'slot-9.json'), ('ทำความสะอาดช่องชาร์จราคาเท่าไหร่', 'slot-10.json'),
    ('ลำโพงเสียงแตกเปลี่ยนเท่าไหร่', 'slot-11.json'), ('เปลี่ยนกล้องหลังราคาเท่าไหร่', 'slot-12.json'),
    ('ฟิล์มกระจกราคาเท่าไหร่', 'slot-13.json'), ('เคสใสราคาเท่าไหร่', 'slot-14.json'),
    ('สาย Lightning ราคาเท่าไหร่', 'slot-15.json'), ('สายชาร์จ USB-C ราคาเท่าไหร่', 'slot-16.json'),
    ('iPhone 13 แบตเสื่อม เปลี่ยนเท่าไหร่', 'slot-8.json'), ('จอ iPhone 15 แตก ซ่อมกี่บาท', 'slot-5.json'),
]

def main():
    headers = {'X-API-Key': os.environ['LIGHTRAG_API_KEY']}
    ranks, misses, times = [], [], []
    with httpx.Client(timeout=120) as client:
        for question, expected in CASES:
            t = time.perf_counter()
            r = client.post('http://lightrag:9621/query/data', headers=headers, json={'query': PREFIX + question, 'mode': MODE, 'chunk_top_k': 5, 'top_k': 10,
                            'max_entity_tokens': 800, 'max_relation_tokens': 800, 'max_total_tokens': 5000, 'enable_rerank': False}).json()
            times.append((time.perf_counter() - t) * 1000)
            files = [c.get('file_path', '') for c in r.get('data', {}).get('chunks', [])[:5]]
            rank = next((i + 1 for i, f in enumerate(files) if expected in f.split('-', 1)[-1]), None)
            ranks.append(rank)
            if rank != 1:
                misses.append(f'| {question} | {expected} | {rank or "ไม่พบใน 5"} | {", ".join(f.split("-", 1)[-1] for f in files[:3])} |')
    n = len(CASES)
    hit = lambda k: sum(1 for r in ranks if r and r <= k) / n
    mrr = sum(1 / r for r in ranks if r) / n
    stamp = datetime.now(timezone(timedelta(hours=7)))
    print('\n'.join([f'# Retrieval eval — {stamp:%Y-%m-%d %H:%M} (เวลาไทย) · KB `{os.getenv("KB_VERSION")}` · mode `{MODE}`', '',
                     f'{n} คำถาม: **hit@1 {hit(1):.0%} · hit@3 {hit(3):.0%} · hit@5 {hit(5):.0%} · MRR {mrr:.2f}** · เวลาค้น p50 {sorted(times)[n // 2]:.0f} ms', '',
                     '| คำถาม | แหล่งที่ควรได้ | อันดับจริง | 3 อันดับแรกที่ได้ |', '|---|---|---|---|'] + (misses or ['| — | — | ทุกข้อได้อันดับ 1 | — |'])))

main()
