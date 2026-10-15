"""Load test straight against the API (inside the api container), past nginx's per-IP limits.

    docker compose exec -T api python - < qa/load_test.py

1. Cached FAQ traffic: 20 concurrent visitors, each request a new session.
2. Burst of 20 identical NEW questions at once: single-flight should make one
   router call, one retrieval and one answer, not 20 of each.
Prints a Markdown report; token deltas come from the app's own Redis counters.
"""
import asyncio, json, os, statistics, time, uuid
from datetime import datetime, timedelta, timezone
import httpx
from redis.asyncio import Redis

BASE = os.getenv('LOAD_BASE', 'http://127.0.0.1:8000')
FAQ = ['ร้านเปิดกี่โมง', 'เปลี่ยนจอ iPhone 13 ราคาเท่าไหร่', 'แบต iPhone 12 เท่าไหร่', 'ตรวจเช็คเสียเงินไหมครับ', 'สาย Lightning ใช้กับ iPhone 15 ได้ไหม']
WORKERS, PER_WORKER = 20, 12
TH = timezone(timedelta(hours=7))

def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(q * (len(values) - 1))))]

async def metrics(redis):
    return {k: int(v) for k, v in (await redis.hgetall('metrics:' + datetime.now(TH).strftime('%Y%m%d'))).items()}

async def worker(n, results, questions):
    async with httpx.AsyncClient(timeout=120) as client:
        for i in range(PER_WORKER):
            client.cookies.clear()
            text = questions[(n + i) % len(questions)]
            t = time.perf_counter()
            r = await client.post(BASE + '/api/chat', data={'text': text})
            ms = (time.perf_counter() - t) * 1000
            body = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
            results.append((r.status_code, ms, bool(body.get('cache', {}).get('answer'))))

async def burst(text, n):
    async def one():
        async with httpx.AsyncClient(timeout=120) as client:
            t = time.perf_counter(); r = await client.post(BASE + '/api/chat', data={'text': text})
            return r.status_code, (time.perf_counter() - t) * 1000, r.json().get('answer', '')
    return await asyncio.gather(*[one() for _ in range(n)])

async def main():
    redis = Redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'), decode_responses=True)
    async with httpx.AsyncClient(timeout=120) as client:
        for q in FAQ:  # warm the shared cache
            client.cookies.clear(); await client.post(BASE + '/api/chat', data={'text': q})
    results = []
    t = time.perf_counter()
    await asyncio.gather(*[worker(n, results, FAQ) for n in range(WORKERS)])
    wall = time.perf_counter() - t
    ok = [ms for status, ms, _ in results if status == 200]
    hits = sum(1 for status, _, hit in results if status == 200 and hit)
    errors = {s: sum(1 for st, _, _ in results if st == s) for s in {st for st, _, _ in results if st != 200}}
    before = await metrics(redis)
    question = f'ฟิล์มกระจก iPhone 16 ราคาเท่าไหร่ครับ รอบทดสอบ {uuid.uuid4().hex[:6]}'
    t = time.perf_counter()
    burst_results = await burst(question, 20)
    burst_wall = time.perf_counter() - t
    after = await metrics(redis)
    calls = after.get('llm_calls', 0) - before.get('llm_calls', 0)
    rmiss = after.get('retrieval_miss', 0) - before.get('retrieval_miss', 0)
    answers = {a for _, _, a in burst_results}
    lines = [f'# Load test — {datetime.now(TH):%Y-%m-%d %H:%M} (เวลาไทย)', '', f'เป้าหมาย: `{BASE}` (API ตรง ไม่ผ่าน nginx)', '',
             '## 1. คำถามยอดฮิตที่อยู่ใน cache', '',
             f'- {len(results)} คำขอ, พร้อมกัน {WORKERS} ผู้ใช้, ทุกคำขอเป็น session ใหม่, ใช้เวลารวม {wall:.1f} วินาที ({len(results) / wall:.1f} คำขอ/วินาที)',
             f'- สำเร็จ {len(ok)}/{len(results)} · hit cache {hits}/{len(ok)} · error {errors or "ไม่มี"}',
             f'- latency ฝั่ง client: p50 {pct(ok, .5):.0f} ms, p95 {pct(ok, .95):.0f} ms, p99 {pct(ok, .99):.0f} ms, max {max(ok):.0f} ms', '',
             '## 2. คำถามใหม่เดียวกัน 20 คำขอพร้อมกัน (single-flight)', '',
             f'- สำเร็จ {sum(1 for s, _, _ in burst_results if s == 200)}/20 ใน {burst_wall:.1f} วินาที · คำตอบต่างกัน {len(answers)} แบบ',
             f'- เรียก OpenAI รวม {calls} ครั้ง (ถ้าไม่มี single-flight จะเป็นประมาณ 40) · เรียก LightRAG {rmiss} ครั้ง (แทน 20)',
             f'- latency: p50 {pct([ms for _, ms, _ in burst_results], .5):.0f} ms, max {max(ms for _, ms, _ in burst_results):.0f} ms']
    print('\n'.join(lines))
    await redis.aclose()

asyncio.run(main())
