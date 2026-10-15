#!/usr/bin/env python3
"""End-to-end case lifecycle with the real AI: open by chat -> AI-assisted admin -> approve by chat -> close.

    python3 qa/run_lifecycle_eval.py [--base http://127.0.0.1:8081]

Standard library only; reuses run_eval's HTTP client. Writes qa/results/lifecycle-latest.md.
"""
import time, argparse, json, re, sys, uuid
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_eval import Client, env_value, ROOT, TH

STEPS = []
def step(name, ok, detail=''):
    STEPS.append((name, bool(ok), str(detail)[:300])); print(('PASS' if ok else 'FAIL'), name, '' if ok else detail, flush=True)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--base', default='http://127.0.0.1:8081'); args = ap.parse_args()
    admin, member, conv = Client(args.base), Client(args.base), {}
    admin.request('POST', '/api/auth/login', {'username': env_value('ADMIN_USERNAME', 'admin'), 'password': env_value('ADMIN_PASSWORD')})
    tag = uuid.uuid4().hex[:6]
    member.request('POST', '/api/auth/register', {'username': f'life_{tag}', 'password': f'life-password-{tag}'})
    def say(text):
        form = {'text': text, **({'conversation_id': conv['id']} if conv.get('id') else {})}
        for _ in range(6):  # another suite (security K04) may have just used up this IP's per-minute chat limit
            status, data = member.request('POST', '/api/chat', form=form)
            if status != 429:
                break
            time.sleep(15)
        if status != 200:
            data = {**data, 'answer': f"HTTP {status}: {data.get('detail', '')}"}
        conv['id'] = data.get('conversation_id') or conv.get('id')
        return status, data
    def case(cid): return member.request('GET', f'/api/member/cases/{cid}')[1]['case']
    def assist(cid): return admin.request('POST', f'/api/admin/cases/{cid}/assist')[1]
    def apply(cid, a, fallback_status, fallback_note):
        body = {'status': a.get('suggested_status') or fallback_status, 'note': a.get('customer_note') or fallback_note}
        if a.get('suggested_price') is not None: body['quoted_price'] = a['suggested_price']
        return admin.request('PATCH', f'/api/admin/cases/{cid}', body)

    # 1. Customer opens a case in chat (two turns, then explicit confirmation).
    _, d = say('ไอโฟน 13 จอแตกครับ ทัชบางจุดไม่ได้')
    _, d = say('อยากส่งซ่อมครับ') if not d.get('pending') else (200, d)
    step('AI เสนอเปิดเคสพร้อมรุ่นและอาการ (ยังไม่สร้างเคส)', d.get('pending') and 'iPhone 13' in d['answer'], d.get('answer'))
    cases_before = member.request('GET', '/api/member/cases')[1]['cases']
    step('ยังไม่มีเคสก่อนยืนยัน', not cases_before, len(cases_before))
    _, d = say('ยืนยัน')
    ref = re.search(r'PLM-(\d+)', d.get('answer', ''))
    step('ยืนยันแล้วได้เลขเคส', ref, d.get('answer'))
    if not ref:
        return write(args.base)
    cid = int(ref.group(1)); c = case(cid)
    step('เคสถูกสร้างตรงรุ่นและผูกบทสนทนา', c['model'] == 'iPhone 13' and c['status'] == 'submitted' and c['conversation_id'] == conv['id'], c)

    # 2. Admin: receive, inspect, then AI suggests the quote from the catalog.
    for st in ['received', 'checking']:
        admin.request('PATCH', f'/api/admin/cases/{cid}', {'status': st, 'note': 'รับเครื่องและตรวจเช็ค'})
    a = assist(cid)
    step('AI สรุปเคสจากแชทจริง (มีรุ่นและอาการ)', '13' in a.get('summary', '') and ('จอ' in a.get('summary', '') or 'ทัช' in a.get('summary', '')), a.get('summary'))
    step('AI แนะนำส่งใบเสนอ 3,200 บาทจากแค็ตตาล็อก', a.get('suggested_status') == 'awaiting_approval' and a.get('suggested_price') == 3200, {k: a.get(k) for k in ('suggested_status', 'suggested_price', 'warnings')})
    status, _ = apply(cid, a, 'awaiting_approval', 'เสนอราคาเปลี่ยนหน้าจอ')
    step('แอดมินกดใช้คำแนะนำได้', status == 200 and (case(cid)['quote'] or {}).get('amount') == 3200, status)

    # 3. Customer checks status and approves by chat (with confirmation).
    _, d = say(f'PLM-{cid:05d} ถึงไหนแล้ว')
    step('ลูกค้าเห็นสถานะและราคาเสนอจากระบบ', 'รออนุมัติราคา' in d['answer'] and '3,200' in d['answer'], d['answer'])
    _, d = say('โอเค อนุมัติราคานี้ครับ')
    step('AI เสนอให้อนุมัติใบเสนอ (รอยืนยัน)', d.get('pending') and (case(cid)['quote'] or {}).get('status') == 'pending', d.get('answer'))
    _, d = say('ยืนยัน')
    step('ยืนยันแล้วใบเสนอเป็นอนุมัติ', (case(cid)['quote'] or {}).get('status') == 'approved', d.get('answer'))
    _, d = say('จ่ายเงินยังไงครับ')
    step('ถามการชำระได้คำตอบจากระบบ (ไม่รับเลขบัตรในแชท)', d.get('route') == 'payment' or 'ชำระ' in d['answer'], d['answer'])

    # 4. Admin: AI suggests starting the repair, then ready, then a closing summary.
    a = assist(cid)
    step('AI แนะนำเริ่มซ่อมหลังลูกค้าอนุมัติ', a.get('suggested_status') == 'repairing', {k: a.get(k) for k in ('suggested_status', 'warnings', 'reason')})
    apply(cid, a, 'repairing', 'เริ่มซ่อมตามราคาที่อนุมัติ')
    admin.request('PATCH', f'/api/admin/cases/{cid}', {'status': 'ready', 'note': 'เปลี่ยนหน้าจอเสร็จแล้ว ทดสอบทัชครบทุกจุด พร้อมรับเครื่อง'})
    _, d = say('รับเครื่องได้ยังครับ')
    step('ลูกค้าถามรับเครื่อง ได้สถานะพร้อมรับ', 'พร้อมรับเครื่อง' in d['answer'], d['answer'])
    a = assist(cid)
    step('AI แนะนำปิดเคสพร้อมโน้ตสรุปงาน', a.get('suggested_status') == 'closed' and len(a.get('customer_note', '')) > 10, {k: a.get(k) for k in ('suggested_status', 'customer_note', 'warnings')})
    status, _ = apply(cid, a, 'closed', 'ลูกค้ารับเครื่องแล้ว ปิดเคส')
    step('ปิดเคสสำเร็จ', status == 200 and case(cid)['status'] == 'closed', status)

    # 5. Owner insights reflect the day's questions without personal data.
    status, ins = admin.request('GET', '/api/admin/insights')
    step('Insight รายวันใช้งานได้และมีคำแนะนำ', status == 200 and ins.get('total', 0) > 0 and ins.get('advice'), {k: ins.get(k) for k in ('total', 'routes')})
    write(args.base)

def write(base):
    passed = sum(ok for _, ok, _ in STEPS)
    stamp = datetime.now(TH)
    lines = [f'# Lifecycle eval (เปิด → ปิดเคสด้วย AI) — {stamp:%Y-%m-%d %H:%M} (เวลาไทย)', '', f'เป้าหมาย: `{base}` · **ผ่าน {passed}/{len(STEPS)} ขั้น**', '',
             '| ขั้น | ผล | รายละเอียด |', '|---|---|---|'] + [f"| {n} | {'ผ่าน' if ok else '**ไม่ผ่าน**'} | {d.replace('|', '/').replace(chr(10), ' ')[:160] if not ok else ''} |" for n, ok, d in STEPS]
    (ROOT / 'results' / 'lifecycle-latest.md').write_text('\n'.join(lines) + '\n')
    print(f'\n{passed}/{len(STEPS)} passed')

if __name__ == '__main__':
    main()
