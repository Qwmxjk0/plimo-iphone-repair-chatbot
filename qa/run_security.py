#!/usr/bin/env python3
"""Security checks mapped to OWASP Top 10:2025 against a running Plimo (no paid AI calls).

    python3 qa/run_security.py [--base http://127.0.0.1:8081] [--docker]

--docker also scans the API container logs for secrets/card numbers (local or on the VPS).
Writes qa/results/security-latest.md and security-*.json.
"""
import argparse, hashlib, hmac, json, re, subprocess, time, uuid, urllib.error, urllib.request, http.cookiejar
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
TH = timezone(timedelta(hours=7))

class Client:
    def __init__(self, base):
        self.base, self.jar = base.rstrip('/'), http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
    def call(self, method, path, body=None, headers=None, raw=None, ctype=None):
        headers = dict(headers or {})
        data = raw
        if body is not None:
            data, headers['Content-Type'] = json.dumps(body).encode(), 'application/json'
        if ctype:
            headers['Content-Type'] = ctype
        try:
            with self.opener.open(urllib.request.Request(self.base + path, data=data, method=method, headers=headers), timeout=60) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

def env_value(name, default=''):
    path = PROJECT / '.env'
    if path.exists():
        for line in path.read_text().splitlines():
            if line.startswith(name + '='):
                return line.split('=', 1)[1].strip()
    return default

def multipart(fields, files):
    b = '----sec' + uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, name, data, ctype in files:
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode() + data + b'\r\n'
    out += f'--{b}--\r\n'.encode()
    return bytes(out), 'multipart/form-data; boundary=' + b

RESULTS = []
def check(owasp, test_id, title, ok, detail=''):
    RESULTS.append({'owasp': owasp, 'id': test_id, 'title': title, 'pass': bool(ok), 'detail': detail})
    print(('PASS' if ok else 'FAIL'), test_id, title, '' if ok else detail, flush=True)

def register(base, prefix):
    c = Client(base); name = f'{prefix}_{uuid.uuid4().hex[:6]}'
    c.call('POST', '/api/auth/register', {'username': name, 'password': 'sec-test-password-' + name})
    return c, name

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--base', default='http://127.0.0.1:8081'); ap.add_argument('--docker', action='store_true')
    args = ap.parse_args(); base = args.base.rstrip('/')
    guest = Client(base)
    admin = Client(base)
    admin_ok = admin.call('POST', '/api/auth/login', {'username': env_value('ADMIN_USERNAME', 'admin'), 'password': env_value('ADMIN_PASSWORD')})[0] == 200
    a, _ = register(base, 'sec_a'); b, _ = register(base, 'sec_b')

    # A01 Broken Access Control
    st, _, body = a.call('POST', '/api/member/cases', {'model': 'iPhone 13', 'issue': '<img src=x onerror=alert(1)> จอแตก'})
    case_id = json.loads(body)['case']['id']
    for label, (method, path) in {'อ่านเคสคนอื่น': ('GET', f'/api/member/cases/{case_id}'), 'ตัดสินใบเสนอของคนอื่น': ('POST', f'/api/member/cases/{case_id}/quote-decision'),
                                  'สร้าง checkout ของคนอื่น': ('POST', f'/api/member/cases/{case_id}/checkout')}.items():
        body = {'quote_id': 1, 'decision': 'approve'} if 'quote' in path else None
        st = b.call(method, path, body)[0]
        check('A01', 'W01', f'IDOR: {label}', st in (404, 503) and st != 200, f'HTTP {st}')
    st = b.call('GET', '/api/member/conversations/' + uuid.uuid4().hex)[0]
    check('A01', 'W01', 'IDOR: บทสนทนาที่ไม่ใช่ของตัวเอง', st == 404, f'HTTP {st}')
    for path in ['/api/admin/cases', '/api/admin/metrics', '/api/admin/insights', f'/api/admin/cases/{case_id}']:
        st_member, st_guest = a.call('GET', path)[0], guest.call('GET', path)[0]
        check('A01', 'W02', f'สิทธิ์ admin: {path}', st_member == 403 and st_guest == 401, f'member {st_member}, guest {st_guest}')
    st_m, st_g = a.call('POST', f'/api/admin/cases/{case_id}/assist')[0], guest.call('POST', f'/api/admin/cases/{case_id}/assist')[0]
    check('A01', 'W02', 'สิทธิ์ admin: AI วิเคราะห์เคส', st_m == 403 and st_g == 401, f'member {st_m}, guest {st_g}')
    st = a.call('POST', '/api/auth/logout', headers={'Origin': 'https://evil.example'})[0]
    check('A01', 'W13', 'CSRF: POST ข้าม origin ถูกปฏิเสธ', st == 403, f'HTTP {st}')

    # A02 Security Misconfiguration
    st, headers, _ = guest.call('GET', '/')
    h = {k.lower(): v for k, v in headers.items()}
    csp = h.get('content-security-policy', '')
    check('A02', 'W03', 'CSP ไม่มี unsafe-inline/eval และห้าม frame จากเว็บอื่น', "default-src 'self'" in csp and 'unsafe' not in csp and "frame-ancestors 'self'" in csp, csp[:80])
    for name, expected in [('x-content-type-options', 'nosniff'), ('x-frame-options', 'SAMEORIGIN'), ('referrer-policy', 'strict-origin-when-cross-origin'), ('permissions-policy', 'camera=()')]:
        check('A02', 'W03', f'header {name}', expected.lower() in h.get(name, '').lower(), h.get(name, 'missing'))
    check('A02', 'W03', 'ไม่เปิดเผยเวอร์ชัน server', not re.search(r'\d', h.get('server', '')), h.get('server', ''))
    if base.startswith('https://'):
        check('A04', 'W06', 'HSTS บน HTTPS', 'max-age=' in h.get('strict-transport-security', ''), h.get('strict-transport-security', 'missing'))
    for path in ['/.env', '/.git/config', '/backend/main.py', '/compose.yaml', '/nginx.conf', '/docs', '/openapi.json', '/redoc', '/api/docs', '/api/openapi.json']:
        st, _, body = guest.call('GET', path)
        leaked = b'OPENAI_API_KEY' in body or b'[core]' in body or b'"openapi"' in body
        check('A02', 'W04', f'ไม่ serve {path}', st in (403, 404) and not leaked, f'HTTP {st}')
    st, _, body = guest.call('GET', '/api/does-not-exist')
    check('A10', 'W12', 'error ไม่มี stack trace', st == 404 and b'Traceback' not in body, f'HTTP {st}')

    # A03 Software Supply Chain (static, from the repository being deployed)
    compose = (PROJECT / 'compose.yaml').read_text() + (PROJECT / 'compose.prod.yaml').read_text()
    images = re.findall(r'image:\s*\$?\{?[A-Z_]*:?-?([^}\s]+)', compose)
    check('A03', 'W05', 'image ทุกตัว pin เวอร์ชัน (ไม่มี latest)', images and all(':latest' not in i and (('@sha256:' in i) or re.search(r':\d', i)) for i in images), ', '.join(images))
    for dockerfile in ['Dockerfile', 'backend/Dockerfile']:
        text = (PROJECT / dockerfile).read_text()
        check('A03', 'W05', f'{dockerfile} base image pin เวอร์ชัน', re.search(r'^FROM \S+:\d', text, re.M) is not None, text.splitlines()[0])
    api_df = (PROJECT / 'backend/Dockerfile').read_text()
    check('A03', 'W05', 'Python dependency ล็อกเวอร์ชันตรงที่ทดสอบ', 'requirements.lock' in api_df and all('==' in l for l in (PROJECT / 'backend/requirements.lock').read_text().split() if l), 'requirements.lock')
    check('A02', 'W05', 'API container ไม่รันเป็น root', '\nUSER app' in api_df, '')

    # A04 Cryptographic Failures / A07 Authentication Failures
    c = Client(base); name = 'sec_c_' + uuid.uuid4().hex[:6]
    st, headers, _ = c.call('POST', '/api/auth/register', {'username': name, 'password': 'sec-test-password-123'})
    cookie = headers.get('set-cookie') or headers.get('Set-Cookie') or ''
    check('A04', 'W06', 'cookie สมาชิก HttpOnly + SameSite=Strict', 'httponly' in cookie.lower() and 'samesite=strict' in cookie.lower(), cookie[:60])
    if base.startswith('https://'):
        check('A04', 'W06', 'cookie มี Secure บน HTTPS', 'secure' in cookie.lower(), cookie[:60])
    st = Client(base).call('POST', '/api/auth/register', {'username': 'short_' + uuid.uuid4().hex[:4], 'password': '123'})[0]
    check('A07', 'W09', 'ปฏิเสธรหัสผ่านสั้น', st == 422, f'HTTP {st}')
    target = 'sec_bf_' + uuid.uuid4().hex[:6]
    Client(base).call('POST', '/api/auth/register', {'username': target, 'password': 'right-password-123'})
    codes = []
    for _ in range(11):
        codes.append(Client(base).call('POST', '/api/auth/login', {'username': target, 'password': 'wrong-password-123'})[0])
        time.sleep(3.1)  # stay under nginx's login rate so the app's own lockout is what we observe
    check('A07', 'W09', 'brute force บัญชีเดียวถูกล็อก', codes[-1] == 429 and 401 in codes, ','.join(map(str, codes)))
    st = c.call('POST', '/api/auth/login', {'username': name, 'password': 'sec-test-password-123'})[0]
    check('A07', 'W09', 'บัญชีอื่นจาก IP เดียวกันยังเข้าได้ (NAT ห้องเรียน)', st == 200, f'HTTP {st}')

    # A05 Injection
    st = Client(base).call('POST', '/api/auth/login', {'username': "admin' OR '1'='1", 'password': "x' OR '1'='1' --"})[0]
    check('A05', 'W07', 'SQL injection ที่ login', st in (401, 422), f'HTTP {st}')
    st, _, body = a.call('GET', f'/api/member/cases/{case_id}')
    check('A05', 'W07', 'stored XSS เก็บเป็นข้อความเดิม', st == 200 and '<img src=x onerror=alert(1)>' in json.loads(body)['case']['issue'], f'HTTP {st}')
    unsafe = [f.name for f in (PROJECT / 'dist').glob('*.js') if re.search(r'innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(', f.read_text())]
    check('A05', 'W07', 'frontend ไม่ใช้ innerHTML/eval กับข้อมูล', not unsafe, ', '.join(unsafe))

    # A06 Insecure Design: state machine
    if admin_ok:
        for status in ['received', 'checking']:
            admin.call('PATCH', f'/api/admin/cases/{case_id}', {'status': status, 'note': 'ตรวจความปลอดภัย'})
        st = admin.call('PATCH', f'/api/admin/cases/{case_id}', {'status': 'repairing', 'note': 'ข้ามการอนุมัติ', 'quoted_price': 3200})[0]
        check('A06', 'W08', 'เริ่มซ่อมก่อนลูกค้าอนุมัติราคาไม่ได้', st == 409, f'HTTP {st}')
        admin.call('PATCH', f'/api/admin/cases/{case_id}', {'status': 'awaiting_approval', 'note': 'ราคาแรก', 'quoted_price': 3200})
        old_quote = json.loads(a.call('GET', f'/api/member/cases/{case_id}')[2])['case']['quote']['id']
        admin.call('PATCH', f'/api/admin/cases/{case_id}', {'status': 'awaiting_approval', 'note': 'ราคาใหม่', 'quoted_price': 3900})
        st = a.call('POST', f'/api/member/cases/{case_id}/quote-decision', {'quote_id': old_quote, 'decision': 'approve'})[0]
        check('A06', 'W08', 'อนุมัติใบเสนอเก่าไม่ได้', st == 409, f'HTTP {st}')
        st = a.call('POST', f'/api/member/cases/{case_id}/checkout')[0]
        check('A06', 'W08', 'ชำระก่อนอนุมัติไม่ได้', st in (409, 503), f'HTTP {st}')
    else:
        check('A06', 'W08', 'state machine (ต้องมีรหัส admin)', False, 'admin login failed')

    # A08 Software or Data Integrity: forged webhook
    payload = json.dumps({'id': 'evt_forged', 'type': 'checkout.session.completed', 'livemode': False, 'data': {'object': {'id': 'cs_test_forged'}}}).encode()
    stamp = str(int(time.time()))
    forged = hmac.new(b'whsec_guess', stamp.encode() + b'.' + payload, hashlib.sha256).hexdigest()
    st = guest.call('POST', '/api/stripe/webhook', raw=payload, headers={'Stripe-Signature': f't={stamp},v1={forged}', 'Content-Type': 'application/json'})[0]
    check('A08', 'W10', 'webhook ลายเซ็นปลอมถูกปฏิเสธ', st in (400, 503), f'HTTP {st}')

    # A10 Mishandling of Exceptional Conditions: input limits fail safely (no model call for these)
    data, ctype = multipart({'text': 'ก' * 3001}, [])
    check('A10', 'W12', 'ข้อความยาวเกินถูกปฏิเสธ', guest.call('POST', '/api/chat', raw=data, ctype=ctype)[0] == 422)
    data, ctype = multipart({'text': 'ดูภาพ'}, [('images', 'x.png', b'not an image', 'image/png')])
    check('A10', 'W12', 'ไฟล์ที่ไม่ใช่ภาพถูกปฏิเสธ', guest.call('POST', '/api/chat', raw=data, ctype=ctype)[0] == 415)
    data, ctype = multipart({'text': 'ดูภาพ'}, [('images', 'big.png', b'\x89PNG' + b'0' * (10 * 1024 * 1024 + 10), 'image/png')])
    check('A10', 'W12', 'ภาพใหญ่เกิน 10 MB ถูกปฏิเสธ', guest.call('POST', '/api/chat', raw=data, ctype=ctype)[0] == 413)
    st = guest.call('POST', '/api/auth/login', raw=b'{not json', ctype='application/json')[0]
    check('A10', 'W12', 'JSON เสียไม่ทำให้ 500', st == 422, f'HTTP {st}')

    # A09 Security Logging and Alerting Failures
    if args.docker:
        logs = subprocess.run(['docker', 'compose', 'logs', '--no-color', '--since', '24h', 'api'], cwd=PROJECT, capture_output=True, text=True).stdout
        leaks = [p for p in [r'sk-[A-Za-z0-9]{20,}', r'sk_(test|live)_[A-Za-z0-9]{10,}', r'whsec_[A-Za-z0-9]{10,}', r'4242\s?4242\s?4242\s?4242', r'1101700203450'] if re.search(p, logs)]
        check('A09', 'W11', 'log ไม่มี key/เลขบัตร/เลขประจำตัว', not leaks, ', '.join(leaks))
        check('A09', 'W11', 'มี log เหตุการณ์ (chat_complete / router / guard)', 'chat_complete' in logs, '')
    if admin_ok:
        st, _, body = admin.call('GET', '/api/admin/metrics')
        day = json.loads(body)['days'].get(datetime.now(TH).strftime('%Y%m%d'), {}) if st == 200 else {}
        check('A09', 'W11', 'ตัวนับ guard/rate/budget ใน admin metrics', st == 200 and 'tokens_total' in day, ', '.join(sorted(day))[:120])

    # Rate limit last: it uses up this IP's chat budget for a minute.
    codes = []
    for _ in range(26):
        data, ctype = multipart({'text': 'ร้านเปิดกี่โมง'}, [])
        codes.append(Client(base).call('POST', '/api/chat', raw=data, ctype=ctype)[0])
    check('LLM06', 'K04', 'nginx จำกัดคำขอแชทถี่ต่อ IP', 429 in codes and 200 in codes, f'{codes.count(200)}x200 {codes.count(429)}x429')
    write(base)

def write(base):
    out = ROOT / 'results'; out.mkdir(exist_ok=True)
    stamp = datetime.now(TH)
    (out / f'security-{stamp:%Y%m%d-%H%M}.json').write_text(json.dumps(RESULTS, ensure_ascii=False, indent=1))
    passed = sum(r['pass'] for r in RESULTS)
    lines = [f'# ผลตรวจความปลอดภัย (OWASP Top 10:2025) — {stamp:%Y-%m-%d %H:%M}', '', f'เป้าหมาย: `{base}` · **ผ่าน {passed}/{len(RESULTS)}**', '',
             '| OWASP | Test | รายการ | ผล | รายละเอียด |', '|---|---|---|---|---|']
    lines += [f"| {r['owasp']} | {r['id']} | {r['title']} | {'ผ่าน' if r['pass'] else '**ไม่ผ่าน**'} | {r['detail'][:80]} |" for r in RESULTS]
    (out / 'security-latest.md').write_text('\n'.join(lines) + '\n')
    print(f'\n{passed}/{len(RESULTS)} passed')

if __name__ == '__main__':
    main()
