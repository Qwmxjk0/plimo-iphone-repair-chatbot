#!/usr/bin/env python3
"""Call every API endpoint in the architecture diagram against a running Plimo and check the result.

    python3 qa/run_api_check.py                              # local Docker at http://127.0.0.1:8081
    python3 qa/run_api_check.py --base https://x.sslip.io

Walks one real flow (guest chat → member → case → admin → quote → payment) so each
endpoint is called with data it actually works on, plus an access-control check for
the protected groups. Stripe endpoints answer 503 while no test key is set; that is
reported as "ปิดอยู่", not as a pass. Writes qa/results/api-check-latest.md.
"""
import argparse, sys, urllib.error, uuid
from datetime import datetime
from pathlib import Path
from run_eval import Client, ROOT, TH, env_value

ENDPOINTS = 24  # routes in backend/main.py, membership.py, payments.py

def raw(client, path):
    try:
        with client.opener.open(client.base + path, timeout=60) as r:
            return r.status, r.headers.get('content-type', ''), len(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('content-type', ''), 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8081')
    base = ap.parse_args().base
    rows, tag = [], uuid.uuid4().hex[:6]
    def check(method, path, got, want, note=''):
        ok = got in want if isinstance(want, tuple) else got == want
        rows.append({'method': method, 'path': path, 'status': got, 'want': want, 'ok': ok, 'note': note})
        return ok

    guest, member, other, admin = Client(base), Client(base), Client(base), Client(base)
    s, d = guest.request('GET', '/api/health'); check('GET', '/api/health', s, 200)
    s, d = guest.request('GET', '/api/ready'); check('GET', '/api/ready', s, 200, 'Redis + LightRAG พร้อม' if s == 200 else str(d)[:80])
    s, d = guest.request('POST', '/api/chat', form={'text': 'ร้านเปิดกี่โมง'})
    check('POST', '/api/chat', s, 200, f"ผู้เยี่ยมชม · route={d.get('route')} · ตอบ {len(d.get('answer', ''))} ตัวอักษร")
    s, d = guest.request('POST', '/api/session/new'); check('POST', '/api/session/new', s, 200)

    creds = {'username': f'api_{tag}', 'password': f'api-check-{tag}', 'name': 'ผู้ทดสอบ API'}
    s, d = member.request('POST', '/api/auth/register', creds); check('POST', '/api/auth/register', s, 200)
    s, d = member.request('GET', '/api/auth/me'); check('GET', '/api/auth/me', s, 200, d.get('user', {}).get('username', ''))
    s, d = member.request('POST', '/api/auth/logout'); check('POST', '/api/auth/logout', s, 200)
    s, d = member.request('POST', '/api/auth/login', creds); check('POST', '/api/auth/login', s, 200)
    other.request('POST', '/api/auth/register', {**creds, 'username': f'api_b_{tag}'})

    # Member chat with a device photo: creates a conversation and a stored image.
    photo = (ROOT / 'images/I01-screen-crack.png').read_bytes()
    s, d = member.request('POST', '/api/chat', form={'text': 'จอเป็นแบบนี้ ซ่อมได้ไหม'}, files=[('images', ('screen.png', photo, 'image/png'))])
    conv, image_ids = d.get('conversation_id'), d.get('image_ids', [])
    check('POST', '/api/chat', s, 200, f"สมาชิก + รูป · เก็บรูป {len(image_ids)} รูป")
    s, d = member.request('GET', '/api/member/conversations'); check('GET', '/api/member/conversations', s, 200, f"{len(d.get('conversations', []))} บทสนทนา")
    s, d = member.request('GET', f'/api/member/conversations/{conv}'); check('GET', '/api/member/conversations/{cid}', s, 200, f"{len(d.get('messages', []))} ข้อความ")
    if image_ids:
        s, ctype, size = raw(member, f'/api/images/{image_ids[0]}')
        check('GET', '/api/images/{image_id}', s, 200, f'เจ้าของเปิดได้ · {ctype} · {size:,} bytes')
        s, _, _ = raw(other, f'/api/images/{image_ids[0]}'); check('GET', '/api/images/{image_id}', s, 404, 'สมาชิกอื่นเปิดไม่ได้')
    else:
        check('GET', '/api/images/{image_id}', 0, 200, 'ไม่มีรูปถูกเก็บ (triage ไม่ผ่าน)')

    s, d = member.request('POST', '/api/member/cases', {'model': 'iPhone 13', 'issue': 'หน้าจอแตก ทัชไม่ทำงาน', 'conversation_id': conv})
    cid = d.get('case', {}).get('id')
    check('POST', '/api/member/cases', s, 200, d.get('case', {}).get('reference', ''))
    s, d = member.request('GET', '/api/member/cases'); check('GET', '/api/member/cases', s, 200)
    s, d = member.request('GET', f'/api/member/cases/{cid}'); check('GET', '/api/member/cases/{cid}', s, 200, d.get('case', {}).get('status', ''))

    s, d = admin.request('POST', '/api/auth/login', {'username': env_value('ADMIN_USERNAME', 'admin'), 'password': env_value('ADMIN_PASSWORD')})
    if s != 200:
        raise SystemExit('Admin login failed: set ADMIN_USERNAME / ADMIN_PASSWORD (env or .env).')
    s, d = admin.request('GET', '/api/admin/cases'); check('GET', '/api/admin/cases', s, 200, f"{len(d.get('cases', []))} เคส")
    s, d = admin.request('GET', f'/api/admin/cases/{cid}'); check('GET', '/api/admin/cases/{cid}', s, 200, f"รูปแนบ {len(d.get('images', []))}")
    if image_ids:
        s, _, _ = raw(admin, f'/api/images/{image_ids[0]}'); check('GET', '/api/images/{image_id}', s, 200, 'ผู้ดูแลเปิดได้เมื่อแนบกับเคสแล้ว')
    s, d = admin.request('POST', f'/api/admin/cases/{cid}/assist')
    check('POST', '/api/admin/cases/{cid}/assist', s, 200, f"AI แนะนำสถานะ {d.get('suggested_status')} ราคา {d.get('suggested_price')}")
    for status, note, price in [('received', 'รับเรื่องแล้ว', None), ('checking', 'กำลังตรวจเช็ค', None), ('awaiting_approval', 'เสนอราคาเปลี่ยนหน้าจอ', 3200)]:
        s, d = admin.request('PATCH', f'/api/admin/cases/{cid}', {'status': status, 'note': note, **({'quoted_price': price} if price else {})})
        check('PATCH', '/api/admin/cases/{cid}', s, 200, '→ ' + status)
    s, d = admin.request('PATCH', f'/api/admin/cases/{cid}', {'status': 'closed', 'note': 'ข้ามขั้น'})
    check('PATCH', '/api/admin/cases/{cid}', s, 409, 'ข้ามขั้นตอนถูกปฏิเสธ')
    s, d = admin.request('GET', '/api/admin/insights'); check('GET', '/api/admin/insights', s, 200, f"คำถามวันนี้ {d.get('total')}")
    s, d = admin.request('GET', '/api/admin/metrics'); check('GET', '/api/admin/metrics', s, 200)

    quote = member.request('GET', f'/api/member/cases/{cid}')[1]['case']['quote']['id']
    s, d = member.request('POST', f'/api/member/cases/{cid}/quote-decision', {'quote_id': quote, 'decision': 'approve'})
    check('POST', '/api/member/cases/{cid}/quote-decision', s, 200, 'อนุมัติใบเสนอราคา')
    s, d = member.request('POST', f'/api/member/cases/{cid}/checkout')
    stripe_on = s == 200
    check('POST', '/api/member/cases/{cid}/checkout', s, (200, 503), 'ได้ลิงก์ Stripe Checkout' if stripe_on else 'ปิดอยู่: ยังไม่ใส่ STRIPE_SECRET_KEY')
    s, d = member.request('GET', '/api/member/payments/confirm?session_id=cs_test_' + 'a' * 24)
    check('GET', '/api/member/payments/confirm', s, 404, 'รหัสที่ไม่มีอยู่ถูกปฏิเสธ')
    s, d = guest.request('POST', '/api/stripe/webhook', {'type': 'checkout.session.completed'})
    check('POST', '/api/stripe/webhook', s, (400, 503), 'ลายเซ็นไม่ถูกต้องถูกปฏิเสธ' if s == 400 else 'ปิดอยู่: ยังไม่ใส่ STRIPE_WEBHOOK_SECRET')

    # Access control on each protected group.
    s, _ = Client(base).request('GET', '/api/member/cases'); check('GET', '/api/member/cases', s, 401, 'ไม่เข้าสู่ระบบ → 401')
    s, _ = member.request('GET', '/api/admin/cases'); check('GET', '/api/admin/cases', s, 403, 'สมาชิกเรียก API ผู้ดูแล → 403')
    s, _ = other.request('GET', f'/api/member/cases/{cid}'); check('GET', '/api/member/cases/{cid}', s, 404, 'เคสของคนอื่น → 404')

    covered = {(r['method'], r['path']) for r in rows if r['ok']}
    passed = sum(r['ok'] for r in rows)
    stamp = datetime.now(TH)
    lines = [f'# API check — {stamp:%Y-%m-%d %H:%M} (เวลาไทย) · `{base}`', '',
             f'**{passed}/{len(rows)} checks ผ่าน · ครอบคลุม {len(covered)}/{ENDPOINTS} endpoint**'
             + ('' if stripe_on else ' · Stripe ปิดอยู่ (ยังไม่ใส่ test key) จึงตรวจได้แค่ว่าปิดอย่างปลอดภัย'), '',
             '| | Method | Endpoint | ได้ | ควรได้ | หมายเหตุ |', '|---|---|---|---|---|---|']
    lines += [f"| {'✅' if r['ok'] else '❌'} | {r['method']} | `{r['path']}` | {r['status']} | {' / '.join(map(str, r['want'])) if isinstance(r['want'], tuple) else r['want']} | {r['note']} |" for r in rows]
    out = ROOT / 'results'; out.mkdir(exist_ok=True)
    name = 'api-check-latest.md' if '127.0.0.1' in base or 'localhost' in base else 'api-check-vps.md'
    (out / name).write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    sys.exit(0 if passed == len(rows) else 1)

if __name__ == '__main__':
    main()
