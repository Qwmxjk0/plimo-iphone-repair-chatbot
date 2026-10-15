"""Render the deployed architecture to qa/diagrams/stack-flow.svg and .png (no provider calls).

    python3 qa/build_architecture.py

The SVG is written by hand-placed boxes; the PNG is rendered from it with headless Chrome
at 2x so text stays sharp in the README and in the course document.
"""
import html, shutil, subprocess, tempfile
from pathlib import Path

OUT = Path(__file__).resolve().parent / 'diagrams'
W, H = 1600, 1000
KIND = {  # fill, accent
    'user': ('#ffffff', '#6e6e73'), 'edge': ('#ffffff', '#0a84ff'), 'app': ('#ffffff', '#0a84ff'),
    'data': ('#ffffff', '#30a46c'), 'ext': ('#ffffff', '#8e5cf7'), 'note': ('#fff8e6', '#d9a400'),
}
svg = []

def esc(s):
    return html.escape(s, quote=True)

def group(x, y, w, h, label):
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="#f2f3f5" stroke="#d6d8dc" stroke-dasharray="6 5"/>')
    svg.append(f'<text x="{x + 18}" y="{y + 26}" class="group">{esc(label)}</text>')

def box(x, y, w, h, title, lines=(), kind='app'):
    fill, accent = KIND[kind]
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="#d6d8dc"/>')
    svg.append(f'<rect x="{x}" y="{y + 10}" width="4" height="{h - 20}" rx="2" fill="{accent}"/>')
    svg.append(f'<text x="{x + 18}" y="{y + 28}" class="title">{esc(title)}</text>')
    for i, line in enumerate(lines):
        cls = 'step' if line[:2].strip().rstrip('.').isdigit() else 'line'
        svg.append(f'<text x="{x + 18}" y="{y + 52 + i * 21}" class="{cls}">{esc(line)}</text>')

def arrow(points, label=None, at=None, both=False):
    pts = ' '.join(f'{x},{y}' for x, y in points)
    marker = ' marker-start="url(#a)"' if both else ''
    svg.append(f'<polyline points="{pts}" fill="none" stroke="#8a8f98" stroke-width="2"{marker} marker-end="url(#a)"/>')
    if label:
        x, y = at or points[0]
        svg.append(f'<text x="{x}" y="{y}" class="label">{esc(label)}</text>')

svg.append(f'<text x="40" y="54" class="h1">Plimo — System Architecture</text>')
svg.append('<text x="40" y="84" class="sub">LLM-first Thai chatbot for an iPhone repair shop · Ubuntu VPS · Docker Compose · https://203-156-66-86.sslip.io · Oct 2026</text>')

# Users
box(40, 150, 230, 104, 'Customer (guest)', ['Storefront + chat widget', 'Thai text + up to 3 photos', 'iPhone HEIC supported'], 'user')
box(40, 280, 230, 104, 'Member', ['Chat history, own cases', 'Open / track case PLM-xxxxx', 'Approve quote, pay online'], 'user')
box(40, 410, 230, 104, 'Admin', ['Case board, status flow', 'AI case assist + insights', 'Metrics, daily AI cost'], 'user')
for yc in (202, 332, 462):
    svg.append(f'<line x1="270" y1="{yc}" x2="300" y2="{yc}" stroke="#8a8f98" stroke-width="2"/>')
arrow([(300, 462), (300, 202), (338, 202)])

# VPS
group(310, 110, 880, 720, 'Ubuntu VPS · Docker Compose (images pinned, API runs as non-root)')
box(340, 150, 200, 104, 'Caddy', ['HTTPS · Let’s Encrypt', 'HSTS'], 'edge')
arrow([(440, 254), (440, 288)])
box(340, 290, 200, 160, 'nginx', ['Static UI (HTML/CSS/JS)', 'CSP + security headers', 'Chat 30 req/min per IP', 'Proxy /api → FastAPI'], 'edge')
arrow([(540, 370), (578, 370)])
box(580, 150, 380, 650, 'FastAPI · Python 3.12', [
    '1. Input guards: mask card / national ID,',
    '    block obvious prompt injection',
    '2. Images: quality check → moderation →',
    '    vision triage (device / slip / card / other)',
    '3. Cache lookup (fast · router · answer)',
    '4. Router LLM → intent JSON (9 intents),',
    '    models, services, case number',
    '5a. case / payment → SQLite (no LLM)',
    '5b. shop / price / advice → retrieval +',
    '     catalog prices → answer LLM',
    '6. Output validator: only catalog-backed',
    '    prices, no hidden-context leaks',
    '7. Actions only after "ยืนยัน" (confirm)',
    '',
    'Admin AI assist: summary, next status,',
    '  quote from catalog (validated)',
    'Stripe Checkout + signed webhook',
    'Budget/day · limits per member/session/IP',
    'Single-flight: one model call per question',
], 'app')

box(1000, 150, 170, 150, 'Redis 7.4', ['6 cache layers', 'answers 7 days', 'rate limits, budget', 'chat context 24 h'], 'data')
box(1000, 320, 170, 120, 'SQLite (WAL)', ['users, chats', 'cases, quotes', 'payments, audit'], 'data')
box(1000, 478, 170, 128, 'Knowledge', ['knowledge/*.md (~6 pp)', '+ catalog.json', 'ingest --ensure', 'on every deploy'], 'data')
box(1000, 640, 170, 130, 'LightRAG', ['naive vector search', '53 sections', 'top-3 to answer'], 'data')
arrow([(960, 225), (998, 225)], both=True)
arrow([(960, 380), (998, 380)], both=True)
arrow([(960, 705), (998, 705)], both=True)
arrow([(1085, 606), (1085, 638)])

# External
group(1210, 110, 350, 720, 'External services')
box(1230, 150, 310, 210, 'OpenAI', ['gpt-5.4-mini \u00b7 Responses API', 'router (JSON schema)', 'answers + vision', 'omni-moderation (images)', 'text-embedding-3-small', 'prompt caching (static prefix)'], 'ext')
box(1230, 400, 310, 120, 'Stripe (test mode)', ['Checkout page (card never', 'touches our server)', 'webhook: HMAC + replay guard'], 'ext')
box(1230, 690, 310, 110, 'Cloudflare R2', ['private bucket', 'member photos + slips (EXIF removed)'], 'ext')
arrow([(900, 150), (900, 132), (1200, 132), (1200, 200), (1228, 200)], 'LLM calls', (1010, 126))
arrow([(960, 459), (1228, 459)], both=True)
arrow([(960, 787), (1228, 787)])

# Notes
box(40, 560, 230, 240, 'Design rules', ['The model proposes,', 'the system confirms.', 'Prices, case status and', 'payments always come', 'from the database.', '', 'Failures are never', 'cached.'], 'note')
svg.append('<text x="40" y="880" class="foot">Tested on the VPS: answer eval 143/143 · API 24/24 endpoints · prompt do/don’t rules 33/33 · OWASP security 51/51 · case lifecycle 16/16 · Stripe test payment · unit 101/101</text>')
svg.append('<text x="40" y="910" class="foot">Cost ≈ $0.0028 per new answer; repeated questions are served from cache in milliseconds. Member chats and cases stay in SQLite, never in the shared RAG index.</text>')

style = '''<style>
text{font-family:-apple-system,"SF Pro Text","Helvetica Neue","Thonburi",Arial,sans-serif;fill:#1d1d1f}
.h1{font-size:30px;font-weight:700}.sub{font-size:16px;fill:#6e6e73}
.group{font-size:14px;font-weight:600;fill:#6e6e73;letter-spacing:.02em}
.title{font-size:18px;font-weight:700}.line{font-size:14px;fill:#3a3a3c}.step{font-size:14px;fill:#1d1d1f}
.label{font-size:12px;fill:#6e6e73}.foot{font-size:15px;fill:#3a3a3c}
</style>'''
defs = '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" fill="#8a8f98"/></marker></defs>'
doc = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{style}{defs}<rect width="{W}" height="{H}" fill="#fbfbfd"/>' + ''.join(svg) + '</svg>'
(OUT / 'stack-flow.svg').write_text(doc)

chrome = shutil.which('google-chrome') or '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
with tempfile.TemporaryDirectory() as tmp:
    page = Path(tmp) / 'd.html'
    page.write_text(f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;background:#fbfbfd}}</style>{doc}')
    subprocess.run([chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars', f'--user-data-dir={tmp}/p',
                    '--force-device-scale-factor=2', f'--window-size={W},{H}', f'--screenshot={OUT / "stack-flow.png"}', page.as_uri()],
                   check=True, capture_output=True)
print('wrote', OUT / 'stack-flow.svg', 'and', OUT / 'stack-flow.png')
