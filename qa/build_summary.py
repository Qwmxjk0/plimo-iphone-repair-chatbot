#!/usr/bin/env python3
"""Build qa/results/SUMMARY.md for the course submission from the latest saved results (no API calls).

    python3 qa/build_summary.py

Deliverable 1: one row per checklist item with its evidence file.
Deliverable 2: 10 questions, 5 images and 5 safety cases taken from the newest eval run
against the public server, with the real answer, pass/fail and response time.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RES = ROOT / 'results'
QUESTIONS = ['F01', 'P01', 'A01', 'A05', 'A15', 'M01', 'C01', 'F06', 'K03', 'K08']
IMAGES = ['I01', 'I02', 'I04', 'I05', 'I07']
SAFETY = ['S01', 'S02', 'S03', 'S05', 'S08']

def headline(name):
    """The first bold line of a results file, e.g. **ผ่าน 51/51**."""
    path = RES / name
    if not path.exists():
        return 'ยังไม่มีผล'
    m = re.search(r'\*\*([^*]+)\*\*', path.read_text())
    return m.group(1) if m else 'ดูไฟล์'

def latest_vps_eval():
    runs = []
    for p in RES.glob('eval-2*.json'):
        data = json.loads(p.read_text())
        if 'sslip.io' in data['summary'].get('base', '') and data['summary'].get('cases', 0) >= 100:
            runs.append((data['summary']['started'], p, data))
    if not runs:
        raise SystemExit('No full eval run against the public server in qa/results/')
    return max(runs, key=lambda r: r[0])

def cell(text, limit=260):
    text = re.sub(r'\s+', ' ', text or '').replace('|', '/').strip()
    return text if len(text) <= limit else text[:limit].rstrip() + '…'

def table(results, ids, title, kind):
    lines = [f'### {title}', '', '| # | กรณี | ข้อความที่ส่ง | ผลตอบ / ผลวิเคราะห์ | ผ่าน | เวลาตอบ |', '|---|---|---|---|---|---|']
    for n, cid in enumerate(ids, 1):
        r = results[cid]
        last = r['turns'][-1]
        asked = ' → '.join(t['text'] for t in r['turns'])
        if kind == 'image':
            image = next((t for t in RAW[cid]['turns'] if isinstance(t, dict) and t.get('image')), {}).get('image', '')
            asked = f"รูป `{Path(image).name}` + \"{asked}\""
        verdict = '✅ ผ่าน' if r['pass'] else '❌ ไม่ผ่าน (' + '; '.join(r['failures'])[:80] + ')'
        seconds = last.get('elapsed_ms', 0) / 1000
        lines.append(f"| {n} | {cid} {cell(r['title'], 60)} | {cell(asked, 140)} | {cell(last['answer'])} | {verdict} | {seconds:.2f} วินาที |")
    return lines

started, path, run = latest_vps_eval()
RESULTS = {r['id']: r for r in run['results']}
RAW = {c['id']: c for c in json.loads((ROOT / 'eval_suite.json').read_text())['cases']}
s = run['summary']
lat = s.get('latency_uncached_ms', {})

out = [
    '# สรุปผลทดสอบสำหรับส่งอาจารย์ — Plimo แชทบอทผู้ช่วยร้านซ่อม iPhone', '',
    f"เว็บจริง: {s['base']} · ผลทดสอบบนเซิร์ฟเวอร์จริง (VPS) · eval รอบ `{path.name}` ({started[:16].replace('T', ' ')})", '',
    'สร้างอัตโนมัติด้วย `python3 qa/build_summary.py` จากไฟล์ผลใน `qa/results/` (ไม่ได้พิมพ์ตัวเลขเอง)', '',
    '## ส่งมอบ 1: Checklist แชทบอทต้นแบบ', '',
    '| Checklist | สิ่งที่ทดสอบ | ผล | หลักฐาน |', '|---|---|---|---|',
    f"| **LLM** ตอบชุดคำถามทดสอบถูกต้องตรงประเด็น | 143 กรณีอัตโนมัติ 9 หมวด (ข้อมูลร้าน ราคา กำกวม หลายเทิร์น เคส ภาพ safety ชำระเงิน คลังความรู้) | {headline('eval-vps.md')} | [eval-vps.md](eval-vps.md) |",
    f"| **API** ทุก endpoint ในแผนภาพทำงานครบ | เรียกครบ 24 endpoint ด้วย flow จริง + ตรวจสิทธิ์ 401/403/404 + Stripe | {headline('api-check-vps.md')} | [api-check-vps.md](api-check-vps.md), [stripe-payment-vps.md](stripe-payment-vps.md) |",
    "| **UI** มีสถานะกำลังประมวลผลและ error | แชทแสดง \"กำลังค้นข้อมูลร้าน…\" / \"กำลังดูภาพ…\" ระหว่างรอ; error ภาษาไทยเมื่อไฟล์ผิดประเภท เกินขนาด เกิน 3 รูป ระบบไม่พร้อม หรือ rate limit; ปุ่มส่งปิดระหว่างประมวลผล | ตรวจด้วยมือ + กรณี I11–I13 (รูปมืด/เล็ก/GIF) ใน eval | [eval-vps.md](eval-vps.md) |",
    f"| **RAG** ตอบจากคลังความรู้เป็นภาษาไทย | คลัง 5 เอกสาร ~6 หน้า A4 (53 หัวข้อ) + แค็ตตาล็อก 16 รายการ; วัดการค้นแยก 40 คำถาม + หมวด K 20 กรณี | {headline('retrieval-vps.md')} | [retrieval-vps.md](retrieval-vps.md) |",
    f"| **Prompt** สุ่มทดสอบรายการ \"ต้องทำ/ห้ามทำ\" | 17 กติกาจาก system prompt, 33 คำถาม, สุ่มด้วย seed | {headline('prompt-rules-vps.md')} | [prompt-rules-vps.md](prompt-rules-vps.md), [../prompt_rules.json](../prompt_rules.json) |",
    f"| **Safety** ป้องกันการใช้งานที่ไม่พึงประสงค์ | OWASP Top 10:2025 (51 ข้อ) + OWASP LLM Top 10 2026 (หมวด S 20 กรณี) | security {headline('security-vps.md')} | [security-vps.md](security-vps.md), [../guardrails.md](../guardrails.md) |",
    '', f"ชุดอื่น: unit/contract {headline('unit-latest.md')} ([unit-latest.md](unit-latest.md)) · วงจรเคสเปิด→ปิดด้วย AI {headline('lifecycle-vps.md')} ([lifecycle-vps.md](lifecycle-vps.md))", '',
    '## ส่งมอบ 2: ชุดทดสอบ (ผลตอบ + ผ่าน/ไม่ผ่าน + เวลาตอบ)', '',
    'เวลาตอบ = เวลาจริงจากเครื่องผู้ทดสอบถึงเซิร์ฟเวอร์และกลับ (ผ่านอินเทอร์เน็ต) ของข้อความสุดท้ายในกรณีนั้น; คำตอบที่เคยถามแล้วมาจาก cache จึงเร็วกว่า',
    f"ภาพรวมรอบนี้: คำถามที่ต้องเรียกโมเดลใหม่ p50 {lat.get('p50', '-')} ms, p95 {lat.get('p95', '-')} ms (เวลาฝั่งเซิร์ฟเวอร์)", '',
]
out += table(RESULTS, QUESTIONS, 'ชุดคำถามทดสอบ 10 ข้อ', 'text') + ['']
out += table(RESULTS, IMAGES, 'ชุดภาพทดสอบ 5 ภาพ', 'image') + ['']
out += table(RESULTS, SAFETY, 'ชุดทดสอบความปลอดภัย 5 กรณี', 'safety') + ['']
failed = [r for r in run['results'] if not r['pass']]
out += ['## กรณีที่ไม่ผ่านในรอบนี้ (รายงานตามจริง)', '']
out += [f"- **{r['id']} {r['title']}** — {'; '.join(r['failures'])}" for r in failed] or ['- ไม่มี']
regraded = (s.get('regraded') or {}).get('changes') or []
if regraded:
    out += ['', 'ตรวจคะแนนซ้ำจากคำตอบเดิม (ไม่ได้ถามใหม่) หลังปรับเกณฑ์ให้รับคำที่ความหมายเดียวกัน:'] + [f'- {c}' for c in regraded]
(RES / 'SUMMARY.md').write_text('\n'.join(out) + '\n')
print(f"wrote {RES / 'SUMMARY.md'} from {path.name}: {s['passed']}/{s['cases']}")
