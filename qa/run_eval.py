#!/usr/bin/env python3
"""Run qa/eval_suite.json against a running Plimo and grade every answer automatically.

    python3 qa/run_eval.py                      # local Docker at http://127.0.0.1:8081
    python3 qa/run_eval.py --base https://x.sslip.io --only P,C

Standard library only. Creates its own member accounts and repair cases (admin
login from ADMIN_USERNAME / ADMIN_PASSWORD in the environment or the project
.env). Cache misses make paid OpenAI calls. Writes qa/results/eval-*.json and
qa/results/eval-latest.md.
"""
import argparse, http.cookiejar, json, os, re, statistics, time, urllib.error, urllib.request, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TH = timezone(timedelta(hours=7))
THAI_DIGITS = str.maketrans('0123456789', '๐๑๒๓๔๕๖๗๘๙')
FILLER = ('ขอเล่าก่อนนะครับ ผมใช้มือถือมาหลายรุ่น เคยทำจอแตกตอนวิ่งไปขึ้นรถไฟฟ้า แล้วก็เคยลืมไว้ในร้านกาแฟ '
          'ช่วงนี้งานยุ่งมาก เลยยังไม่ได้เอาเครื่องไปให้ใครดู อยากได้ร้านที่ไว้ใจได้ ') * 12
MIN_GAP = 2.1  # nginx allows 30 chat requests/min per IP; stay under it.
_last = [0.0]

def multipart(fields, files):
    boundary = '----plimo' + uuid.uuid4().hex
    out = bytearray()
    for key, value in fields.items():
        out += f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
    for key, (name, data, ctype) in files:
        out += f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode() + data + b'\r\n'
    out += f'--{boundary}--\r\n'.encode()
    return bytes(out), 'multipart/form-data; boundary=' + boundary

class Client:
    def __init__(self, base):
        self.base, self.jar, self.conversation = base.rstrip('/'), http.cookiejar.CookieJar(), None
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
    def request(self, method, path, body=None, form=None, files=None):
        headers, data = {}, None
        if body is not None:
            data, headers['Content-Type'] = json.dumps(body).encode(), 'application/json'
        elif form is not None:
            data, headers['Content-Type'] = multipart(form, files or [])
        if path == '/api/chat':
            wait = MIN_GAP - (time.monotonic() - _last[0])
            if wait > 0:
                time.sleep(wait)
            _last[0] = time.monotonic()
        try:
            with self.opener.open(urllib.request.Request(self.base + path, data=data, method=method, headers=headers), timeout=180) as r:
                return r.status, json.loads(r.read() or b'{}')
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read() or b'{}')
            except ValueError:
                return e.code, {}

def env_value(name, default=''):
    if os.getenv(name):
        return os.environ[name]
    path = ROOT.parent / '.env'
    if path.exists():
        for line in path.read_text().splitlines():
            if line.startswith(name + '='):
                return line.split('=', 1)[1].strip()
    return default

def setup(base):
    """Members A and B with repair cases in known states, created through the real API."""
    tag = uuid.uuid4().hex[:6]
    admin = Client(base)
    status, _ = admin.request('POST', '/api/auth/login', {'username': env_value('ADMIN_USERNAME', 'admin'), 'password': env_value('ADMIN_PASSWORD')})
    if status != 200:
        raise SystemExit('Admin login failed: set ADMIN_USERNAME / ADMIN_PASSWORD (env or .env).')
    members = {}
    for key in 'ab':
        c = Client(base)
        status, _ = c.request('POST', '/api/auth/register', {'username': f'eval_{key}_{tag}', 'password': f'eval-password-{tag}', 'name': f'ผู้ทดสอบ {key.upper()}'})
        if status != 200:
            raise SystemExit(f'Could not register eval member {key}: HTTP {status}')
        members[key] = c
    def case(client, model, issue):
        return client.request('POST', '/api/member/cases', {'model': model, 'issue': issue})[1]['case']['id']
    def move(cid, status, note, price=None):
        body = {'status': status, 'note': note, **({'quoted_price': price} if price else {})}
        code, data = admin.request('PATCH', f'/api/admin/cases/{cid}', body)
        if code != 200:
            raise SystemExit(f'Admin update failed for case {cid}: {code} {data}')
    a, b = members['a'], members['b']
    waiting = case(a, 'iPhone 13', 'หน้าจอแตก ทัชไม่ทำงาน')
    for s, n in [('received', 'รับเรื่องแล้ว'), ('checking', 'กำลังตรวจเช็ค')]:
        move(waiting, s, n)
    move(waiting, 'awaiting_approval', 'เสนอราคาเปลี่ยนหน้าจอ', 3200)
    repairing = case(a, 'iPhone 14', 'แบตเสื่อม เครื่องดับเอง')
    for s, n in [('received', 'รับเรื่องแล้ว'), ('checking', 'กำลังตรวจเช็ค')]:
        move(repairing, s, n)
    move(repairing, 'awaiting_approval', 'เสนอราคาเปลี่ยนแบตเตอรี่', 1490)
    quote = a.request('GET', f'/api/member/cases/{repairing}')[1]['case']['quote']['id']
    a.request('POST', f'/api/member/cases/{repairing}/quote-decision', {'quote_id': quote, 'decision': 'approve'})
    move(repairing, 'repairing', 'เปลี่ยนแบตเตอรี่แล้ว กำลังประกอบเครื่อง')
    new = case(a, 'iPhone 12', 'ลำโพงเสียงแตก')
    other = case(b, 'iPhone 15 Pro', 'กล้องหลังเบลอ')
    ref = lambda n: f'PLM-{n:05d}'
    values = {'ref_waiting': ref(waiting), 'ref_waiting_lower': f'plm-{waiting}', 'ref_waiting_nodash': f'PLM{waiting}',
              'ref_waiting_thai': ref(waiting).translate(THAI_DIGITS), 'n_waiting': str(waiting), 'ref_repairing': ref(repairing),
              'ref_other': ref(other), 'ref_new': ref(new), 'long': FILLER}
    return {'admin': admin, 'member': a, 'ids': {'waiting': waiting, 'repairing': repairing, 'new': new, 'other': other}, 'values': values}

def fill(text, values):
    return re.sub(r'\{(\w+)\}', lambda m: values.get(m.group(1), m.group(0)), text)

def numbers(text):
    return {int(n.replace(',', '')) for n in re.findall(r'\d[\d,]*', text) if n.replace(',', '').isdigit()}

def dynamic(kind):
    day = datetime.now(TH) + timedelta(days=0 if kind == 'today_open' else 1)
    word = 'วันนี้' if kind == 'today_open' else 'พรุ่งนี้'
    if day.weekday() == 2:
        return {'any': ['หยุด', 'ปิด']}
    return {'any': ['เปิด'], 'must_not': [f'{word}ร้านหยุด', f'{word}ร้านปิด', f'{word}หยุด', f'{word}ปิด']}

def grade(case, status, data, values, ctx):
    spec = {**case, **(dynamic(case['dynamic']) if case.get('dynamic') else {})}
    answer, fails = data.get('answer', ''), []
    low = answer.lower()
    if status != spec.get('status', 200):
        return [f'HTTP {status}: {data.get("detail", "")}']
    for s in spec.get('must', []):
        if fill(s, values).lower() not in low: fails.append(f'missing "{fill(s, values)}"')
    if spec.get('any') and not any(fill(s, values).lower() in low for s in spec['any']):
        fails.append('none of ' + ' / '.join(fill(s, values) for s in spec['any']))
    for s in spec.get('must_not', []):
        if fill(s, values).lower() in low: fails.append(f'forbidden "{fill(s, values)}"')
    for phrase in (fill(s, values) for s in spec.get('deny', [])):
        for m in re.finditer(re.escape(phrase), answer, re.I):
            if not re.search(r'ไม่|มิ|ว่า|หรือ', answer[max(0, m.start() - 40):m.start()]):
                fails.append(f'affirms "{phrase}"'); break
    for pattern in spec.get('must_not_re', []):
        if re.search(pattern, answer, re.I): fails.append(f'forbidden pattern {pattern}')
    found = numbers(answer)
    fails += [f'missing number {n:,}' for n in spec.get('num', []) if n not in found]
    fails += [f'forbidden number {n:,}' for n in spec.get('not_num', []) if n in found]
    if spec.get('route') and data.get('route') not in spec['route']: fails.append(f'route {data.get("route")} not in {spec["route"]}')
    if data.get('route') in spec.get('route_not', []): fails.append(f'route must not be {data.get("route")}')
    for flag in spec.get('guard', []):
        if flag not in data.get('guard', []): fails.append(f'guard {flag} not raised')
    if spec.get('max_len') and len(answer) > spec['max_len']: fails.append(f'answer too long ({len(answer)} chars)')
    if 'stored' in spec and bool(data.get('image_ids')) != spec['stored']: fails.append(f"image stored={bool(data.get('image_ids'))}, expected {spec['stored']}")
    member = ctx['member'] if ctx else None
    for key, expected in (spec.get('verify_status', {}) if member else {}).items():
        actual = member.request('GET', f"/api/member/cases/{ctx['ids'][key]}")[1]['case']['status']
        if actual != expected: fails.append(f'case {key} status changed to {actual}')
    for key, expected in (spec.get('verify_quote', {}) if member else {}).items():
        actual = member.request('GET', f"/api/member/cases/{ctx['ids'][key]}")[1]['case']['quote']['status']
        if actual != expected: fails.append(f'quote {key} changed to {actual}')
    return fails

def run_case(case, base, ctx):
    values = ctx['values']
    clients = {'a': ctx['member'] if case.get('as') == 'member' else Client(base)}
    clients['a'].conversation = None
    turns = []
    for turn in case['turns']:
        t = turn if isinstance(turn, dict) else {'text': turn}
        key = t.get('session', 'a')
        c = clients.setdefault(key, Client(base))
        if t.get('reset'):
            c.request('POST', '/api/session/new'); c.jar.clear(); c.conversation = None
            continue
        form = {'text': fill(t['text'], values)}
        if c.conversation:
            form['conversation_id'] = c.conversation
        types = {'.heic': 'image/heic', '.gif': 'image/gif', '.jpg': 'image/jpeg', '.webp': 'image/webp'}
        files = [('images', (Path(t['image']).name, (ROOT / t['image']).read_bytes(), types.get(Path(t['image']).suffix.lower(), 'image/png')))] if t.get('image') else []
        started = time.perf_counter()
        status, data = c.request('POST', '/api/chat', form=form, files=files)
        elapsed = round((time.perf_counter() - started) * 1000)
        c.conversation = data.get('conversation_id') or c.conversation
        turns.append({'text': form['text'][:200], 'status': status, 'answer': data.get('answer', data.get('detail', '')), 'route': data.get('route'),
                      'guard': data.get('guard', []), 'cache': data.get('cache', {}), 'timings': data.get('timings', {}), 'elapsed_ms': elapsed,
                      'image_ids': data.get('image_ids', [])})
    last = turns[-1]
    fails = grade(case, last['status'], {'answer': last['answer'], 'route': last['route'], 'guard': last['guard'], 'detail': last['answer'], 'image_ids': last.get('image_ids', [])}, values, ctx)
    return {'id': case['id'], 'cat': case['cat'], 'title': case['title'], 'pass': not fails, 'failures': fails, 'turns': turns}

def metrics(admin):
    status, data = admin.request('GET', '/api/admin/metrics')
    return data.get('days', {}).get(datetime.now(TH).strftime('%Y%m%d'), {}) if status == 200 else {}

def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(q * (len(values) - 1))))] if values else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8081')
    ap.add_argument('--only', default='', help='comma-separated categories or ids, e.g. P,C or P08')
    ap.add_argument('--no-replay', action='store_true')
    ap.add_argument('--regrade', help='re-score a saved eval-*.json with the current checks (no API calls)')
    args = ap.parse_args()
    if args.regrade:
        return regrade(Path(args.regrade))
    suite = json.loads((ROOT / 'eval_suite.json').read_text())
    wanted = {x.strip() for x in args.only.split(',') if x.strip()}
    cases = [c for c in suite['cases'] if not wanted or c['cat'] in wanted or c['id'] in wanted]
    ctx = setup(args.base)
    before = metrics(ctx['admin'])
    started = datetime.now(TH)
    results = []
    for case in cases:
        r = run_case(case, args.base, ctx)
        results.append(r)
        print(f"{'PASS' if r['pass'] else 'FAIL'} {r['id']} {r['title']} {'; '.join(r['failures'])}", flush=True)
    after = metrics(ctx['admin'])
    replay, paraphrase = [], []
    if not args.no_replay:
        for case in cases:
            single = len(case['turns']) == 1 and isinstance(case['turns'][0], str) and case.get('as') != 'member'
            if single:
                status, data = Client(args.base).request('POST', '/api/chat', form={'text': fill(case['turns'][0], ctx['values'])})
                if status == 200:
                    replay.append({'id': case['id'], 'hit': bool(data['cache'].get('answer')), 'total_ms': data['timings'].get('total_ms')})
        for group in suite.get('paraphrases', []):
            for i, text in enumerate(group):
                status, data = Client(args.base).request('POST', '/api/chat', form={'text': text})
                if status == 200 and i:
                    paraphrase.append({'text': text, 'hit': bool(data['cache'].get('answer')), 'fast': bool(data['cache'].get('fast'))})
    write_report(results, replay, paraphrase, before, after, started, args.base, ctx['values'])

def infer_values(saved, suite):
    """Older result files lack placeholder values: recover them by matching templates to stored turn texts."""
    values = {}
    for r in saved['results']:
        texts = [t['text'] for t in r['turns']]
        templates = [t if isinstance(t, str) else t.get('text') for t in suite[r['id']]['turns'] if isinstance(t, str) or t.get('text')]
        for template, text in zip(templates, texts):
            if '{' not in template or '{long}' in template:
                continue
            pattern = '^' + re.sub(r'\\\{(\w+)\\\}', lambda m: f'(?P<{m.group(1)}>.+?)', re.escape(template)) + '$'
            m = re.match(pattern, text)
            if m:
                values.update(m.groupdict())
    return values

def regrade(path):
    """Same stored answers, current grading rules; status/route checks that need the live system keep their recorded result."""
    saved = json.loads(path.read_text())
    suite = {c['id']: c for c in json.loads((ROOT / 'eval_suite.json').read_text())['cases']}
    values = saved['summary'].get('values') or infer_values(saved, suite)
    changed = []
    for r in saved['results']:
        case, last = suite[r['id']], r['turns'][-1]
        spec = {k: v for k, v in case.items() if k not in ('verify_status', 'verify_quote')}
        live = [f for f in r['failures'] if f.startswith(('case ', 'quote '))]
        fails = grade(spec, last['status'], {'answer': last['answer'], 'route': last['route'], 'guard': last['guard'], 'detail': last['answer']}, values, None) + live
        if (not fails) != r['pass']:
            changed.append(f"{r['id']}: {'FAIL→PASS' if not fails else 'PASS→FAIL'} ({'; '.join(r['failures'] or fails)})")
        r['pass'], r['failures'] = not fails, fails
    s = saved['summary']
    s['regraded'] = {'at': datetime.now(TH).isoformat(), 'changes': changed}
    s['passed'] = sum(r['pass'] for r in saved['results'])
    s['by_category'] = {}
    for r in saved['results']:
        c = s['by_category'].setdefault(r['cat'], {'passed': 0, 'total': 0}); c['total'] += 1; c['passed'] += r['pass']
    path.write_text(json.dumps(saved, ensure_ascii=False, indent=1))
    print('regraded', path.name, f"{s['passed']}/{s['cases']}", changed)
    write_markdown(saved, path)

def write_report(results, replay, paraphrase, before, after, started, base, values):
    out = ROOT / 'results'
    out.mkdir(exist_ok=True)
    stamp = started.strftime('%Y%m%d-%H%M')
    first = [t for r in results for t in r['turns'] if t['status'] == 200]
    miss = [t['timings'].get('total_ms') for t in first if not t['cache'].get('answer') and t['timings'].get('total_ms') is not None and t['route'] not in ('case', 'payment', 'guard_card', 'unsafe', 'out_of_scope', 'greeting')]
    tokens = {k: after.get(k, 0) - before.get(k, 0) for k in ('tokens_total', 'tokens_in', 'tokens_out', 'tokens_cached', 'llm_calls')}
    summary = {'started': started.isoformat(), 'base': base, 'cases': len(results), 'passed': sum(r['pass'] for r in results),
               'by_category': {}, 'latency_uncached_ms': {'p50': pct(miss, .5), 'p95': pct(miss, .95), 'n': len(miss)},
               'replay': {'n': len(replay), 'hit_rate': round(sum(r['hit'] for r in replay) / len(replay), 3) if replay else None,
                          'p50_ms': pct([r['total_ms'] for r in replay if r['hit']], .5), 'p95_ms': pct([r['total_ms'] for r in replay if r['hit']], .95)},
               'paraphrase': {'n': len(paraphrase), 'hit_rate': round(sum(p['hit'] for p in paraphrase) / len(paraphrase), 3) if paraphrase else None},
               'tokens': tokens, 'tokens_per_turn': round(tokens['tokens_total'] / max(1, len(first))), 'values': {k: v for k, v in values.items() if k != 'long'}}
    for r in results:
        c = summary['by_category'].setdefault(r['cat'], {'passed': 0, 'total': 0})
        c['total'] += 1; c['passed'] += r['pass']
    saved = {'summary': summary, 'results': results, 'replay': replay, 'paraphrase': paraphrase}
    path = out / f'eval-{stamp}.json'
    path.write_text(json.dumps(saved, ensure_ascii=False, indent=1))
    write_markdown(saved, path)

def write_markdown(saved, path):
    summary, results = saved['summary'], saved['results']
    started = datetime.fromisoformat(summary['started'])
    names = {'F': 'ข้อมูลร้าน', 'P': 'ราคา', 'A': 'กำกวม/ซับซ้อน', 'M': 'หลายเทิร์น', 'C': 'ติดตามเคส', 'I': 'ภาพ', 'S': 'Safety/OWASP LLM', 'Y': 'การชำระเงิน'}
    lines = [f'# ผล eval อัตโนมัติ — {started:%Y-%m-%d %H:%M} (เวลาไทย)', '', f"เป้าหมาย: `{summary['base']}` · ไฟล์เต็ม: `qa/results/{path.name}`", '',
             f"**ผ่าน {summary['passed']}/{summary['cases']} กรณี**", '', '| หมวด | ผ่าน | ทั้งหมด |', '|---|---|---|']
    lines += [f"| {k} {names.get(k, '')} | {v['passed']} | {v['total']} |" for k, v in summary['by_category'].items()]
    if summary.get('regraded'):
        lines += ['', f"ตรวจคะแนนซ้ำเมื่อ {summary['regraded']['at'][:16]} ด้วยเกณฑ์ปัจจุบัน (คำตอบเดิม ไม่ได้ถามใหม่): " + ('; '.join(summary['regraded']['changes']) or 'ไม่มีผลเปลี่ยน')]
    lat, rep, tokens = summary['latency_uncached_ms'], summary['replay'], summary['tokens']
    lines += ['', '## Performance และ cache (วัดจริงรอบนี้)', '',
              f"- ไม่ hit cache (backend total, {lat['n']} ครั้ง): p50 {lat['p50']} ms, p95 {lat['p95']} ms",
              f"- รันซ้ำคำถามเดิมด้วย session ใหม่ ({rep['n']} ครั้ง): hit rate {rep['hit_rate']}, p50 {rep['p50_ms']} ms, p95 {rep['p95_ms']} ms (คำตอบเคส การชำระเงิน และ guard ไม่ cache โดยตั้งใจ)",
              f"- คำถามสำนวนต่างกัน ({summary['paraphrase']['n']} ครั้ง): hit rate {summary['paraphrase']['hit_rate']}",
              f"- Token รอบนี้: {tokens['tokens_total']:,} (input {tokens['tokens_in']:,} ซึ่ง cached {tokens['tokens_cached']:,}, output {tokens['tokens_out']:,}) จาก {tokens['llm_calls']} calls ≈ {summary['tokens_per_turn']} token ต่อข้อความ", '']
    fails = [r for r in results if not r['pass']]
    lines += ['## กรณีที่ไม่ผ่าน', ''] + ([f"- **{r['id']} {r['title']}** — {'; '.join(r['failures'])}\n  - คำตอบ: {r['turns'][-1]['answer'][:300]!r}" for r in fails] or ['ไม่มี'])
    (ROOT / 'results' / 'eval-latest.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines[:12 + len(summary['by_category'])]))

if __name__ == '__main__':
    main()
