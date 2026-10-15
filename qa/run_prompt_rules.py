#!/usr/bin/env python3
"""Randomly sample the prompt's do/don't rules (qa/prompt_rules.json) and test them live.

    python3 qa/run_prompt_rules.py                    # 12 random probes, new seed
    python3 qa/run_prompt_rules.py --n 33 --seed 7    # every probe, reproducible order
    python3 qa/run_prompt_rules.py --base https://x.sslip.io

Each probe runs as a fresh guest and is graded with run_eval.grade. The seed is
printed in the report so the same sample can be rerun. Writes
qa/results/prompt-rules-latest.md (or -vps.md for a remote base).
"""
import argparse, json, random, sys
from datetime import datetime
from run_eval import ROOT, TH, run_case

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8081')
    ap.add_argument('--n', type=int, default=12)
    ap.add_argument('--seed', type=int, default=None)
    args = ap.parse_args()
    seed = args.seed if args.seed is not None else random.randrange(1, 100000)
    rules = json.loads((ROOT / 'prompt_rules.json').read_text())['rules']
    probes = [(r, i, p) for r in rules for i, p in enumerate(r['probes'], 1)]
    sample = random.Random(seed).sample(probes, min(args.n, len(probes)))
    rows = []
    for rule, i, probe in sample:
        case = {'id': f"{rule['id']}.{i}", 'cat': rule['id'], 'title': rule['rule'], **probe}
        result = run_case(case, args.base, {'values': {}, 'member': None})
        rows.append((rule, case, result))
        print(('PASS ' if result['pass'] else 'FAIL ') + case['id'], '; '.join(result['failures']), file=sys.stderr)
    passed = sum(r['pass'] for _, _, r in rows)
    kinds = {t: [r for rule, _, r in rows if rule['type'] == t] for t in ('ต้องทำ', 'ห้ามทำ')}
    lines = [f"# สุ่มทดสอบกติกา ต้องทำ/ห้ามทำ — {datetime.now(TH):%Y-%m-%d %H:%M} (เวลาไทย) · `{args.base}`", '',
             f"**{passed}/{len(rows)} ผ่าน** · สุ่ม {len(rows)} จาก {len(probes)} คำถาม ({len(rules)} กติกา) · seed `{seed}` "
             f"(รันซ้ำ: `python3 qa/run_prompt_rules.py --n {args.n} --seed {seed}`)", '',
             ' · '.join(f"{t} {sum(r['pass'] for r in v)}/{len(v)}" for t, v in kinds.items()), '',
             '| | ข้อ | ประเภท | กติกา | คำถาม | คำตอบ (ย่อ) |', '|---|---|---|---|---|---|']
    for rule, case, r in rows:
        answer = r['turns'][-1]['answer'].replace('\n', ' ').replace('|', '/')[:140]
        note = '' if r['pass'] else ' ❗' + '; '.join(r['failures'])
        lines.append(f"| {'✅' if r['pass'] else '❌'} | {case['id']} | {rule['type']} | {rule['rule']} | {case['turns'][-1]} | {answer}{note} |")
    out = ROOT / 'results'; out.mkdir(exist_ok=True)
    name = 'prompt-rules-latest.md' if '127.0.0.1' in args.base or 'localhost' in args.base else 'prompt-rules-vps.md'
    (out / name).write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    sys.exit(0 if passed == len(rows) else 1)

if __name__ == '__main__':
    main()
