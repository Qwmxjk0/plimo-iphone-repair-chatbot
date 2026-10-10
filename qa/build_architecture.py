"""Render the implemented local architecture to PNG and SVG without provider calls."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import html

OUT = Path(__file__).resolve().parent / 'diagrams'
OUT.mkdir(exist_ok=True)
W, H = 1600, 1180
im = Image.new('RGB', (W, H), '#f6f7f3')
d = ImageDraw.Draw(im)
FONT = '/System/Library/Fonts/Supplemental/Thonburi.ttc'
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', '<rect width="1600" height="1180" fill="#f6f7f3"/>']

def text(x, y, value, size=18, color='#24382d'):
    d.text((x, y), value, font=ImageFont.truetype(FONT, size), fill=color)
    svg.append(f'<text x="{x}" y="{y+size}" font-family="Thonburi,Arial,sans-serif" font-size="{size}" fill="{color}">{html.escape(value)}</text>')

def box(x, y, w, h, title, lines=(), kind='app'):
    fill, stroke = {'app':('#e8efe1','#829773'), 'cache':('#e3eff0','#70999d'), 'ai':('#eee9f6','#9888b3'), 'data':('#fff','#b1b9ac'), 'group':('#f6f7f3','#c0c8ba'), 'note':('#fff2de','#c4a063')}[kind]
    d.rounded_rectangle((x,y,x+w,y+h), radius=14, fill=fill, outline=stroke, width=2)
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    text(x+18,y+14,title,21)
    for i,line in enumerate(lines): text(x+18,y+49+i*26,line,16)

def arrow(points, label=None, labelpos=None, color='#607669'):
    d.line(points,fill=color,width=3)
    x,y=points[-1];a,b=points[-2]
    if x>a: tip=[(x,y),(x-10,y-6),(x-10,y+6)]
    elif x<a: tip=[(x,y),(x+10,y-6),(x+10,y+6)]
    elif y>b: tip=[(x,y),(x-6,y-10),(x+6,y-10)]
    else: tip=[(x,y),(x-6,y+10),(x+6,y+10)]
    d.polygon(tip,fill=color)
    svg.append('<polyline points="'+' '.join(f'{a},{b}' for a,b in points)+f'" fill="none" stroke="{color}" stroke-width="3"/>')
    svg.append('<polygon points="'+' '.join(f'{a},{b}' for a,b in tip)+f'" fill="{color}"/>')
    if label: text(*labelpos,label,14,color)

text(40,25,'PLIMO / Updated System Architecture',34)
text(40,78,'Members / Chat history / Conversation-linked cases / Admin / Thai text + image RAG',21)
text(40,115,'10 Oct 2026   |   Implemented local MVP   |   Arrows show requests / data access',16,'#6e7d68')

box(30,165,300,670,'CUSTOMER / ADMIN',kind='group')
box(50,235,260,130,'Storefront + Chat',('Single shop page','16 demo items / prices','Thai text + up to 3 images'))
box(50,410,260,155,'Member portal',('Login / register','Own chat history + continue','Create / track repair case','Link chat / approve quote'))
box(50,620,260,130,'Admin dashboard',('Role-checked access','Case counts / linked chat','Status + quote + audit'))

box(365,165,810,670,'DOCKER HOST / http://127.0.0.1:8081',kind='group')
box(390,235,330,110,'Nginx',('Serves static UI','Proxies /api to FastAPI'))
box(390,410,330,205,'FastAPI',('Auth + per-user ownership','Chat / image validation','RAG + grounded answer','Case workflow + admin routes','Saves successful member turns'))
box(790,230,360,210,'Redis 7 / temporary',('Answer cache: 30 minutes','Retrieval cache: 1 hour','Vision cache: 24 hours','Recent chat context: 24 hours','Rate limits + session lock'),'cache')
box(790,490,360,115,'LightRAG',('Shop knowledge retrieval','Graph + vector + text index'))
box(790,665,360,130,'SQLite / persistent',('Users + auth sessions','Owned conversations / messages','Cases + versioned quotes / audit'),'data')

box(1210,165,360,670,'EXTERNAL / OpenAI API',kind='group')
box(1230,250,320,155,'Responses API',('Vision: image observations','Answer: retrieved shop context','Default: gpt-5.4-mini','Model configurable in .env'),'ai')
box(1230,520,320,130,'RAG indexing APIs',('Entity / relation extraction','Embeddings:','text-embedding-3-small'),'ai')

arrow([(310,300),(390,300)])
arrow([(310,485),(350,485),(350,320),(390,320)])
arrow([(310,685),(340,685),(340,330),(390,330)])
arrow([(550,345),(550,410)],'API request',(563,366))
arrow([(720,450),(755,450),(755,335),(790,335)],'cache check',(795,446))
arrow([(720,550),(790,550)],'retrieve',(725,524))
arrow([(720,595),(755,595),(755,730),(790,730)],'read / write',(651,704))
arrow([(720,475),(770,475),(1190,475),(1190,330),(1230,330)],'vision / grounded answer',(891,448))

box(30,880,1145,145,'LOCAL DATA / Docker volumes',kind='group')
box(50,930,330,75,'Knowledge files',('Shop facts + labeled demo prices',),'data')
box(415,930,300,75,'ingest.py',('Explicit demo ingestion',),'app')
box(790,930,360,75,'Persistent volumes',('RAG index / member DB / Redis AOF',),'data')
arrow([(380,968),(415,968)])
arrow([(565,930),(565,855),(770,855),(770,585),(790,585)],'ingest knowledge',(575,835))
arrow([(1130,795),(1130,930)])
arrow([(1140,605),(1160,605),(1160,905),(1000,905),(1000,930)])
arrow([(1150,570),(1195,570),(1195,585),(1230,585)])

box(1210,880,360,145,'HOSTED SITE',('chatgpt.site = static preview','Member / RAG / cases run locally','No Docker backend deployed here'),'note')
text(40,1060,'Private member chats and cases stay in SQLite, outside the shared RAG knowledge base.',20)
text(40,1099,'Case chat reads owned SQLite records live, bypassing answer cache / GPT. Members approve quotes in the portal.',18,'#687661')
text(40,1133,'Verified: live text RAG + cache, membership and history UI. Full live image quality tests remain pending.',16,'#687661')
svg.append('</svg>')
(OUT/'stack-flow.svg').write_text('\n'.join(svg))
im.save(OUT/'stack-flow.png')
