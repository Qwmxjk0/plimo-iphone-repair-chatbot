"""Local MVP: persistent users, owned conversations and repair case workflow."""
import hashlib, hmac, json, os, re, secrets, sqlite3, time, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
import nlu

router=APIRouter(prefix='/api')
DB_PATH=os.getenv('MEMBER_DB','/app/data/members.sqlite3')
STATUSES=['submitted','received','checking','awaiting_approval','repairing','ready','closed','cancelled']
TRANSITIONS={'submitted':['received','cancelled'],'received':['checking','cancelled'],'checking':['awaiting_approval','cancelled'],'awaiting_approval':['repairing','cancelled'],'repairing':['ready'],'ready':['closed'],'closed':[],'cancelled':[]}

def db():
    c=sqlite3.connect(DB_PATH,timeout=10);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def password_hash(password,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()
def init_db():
    Path(DB_PATH).parent.mkdir(parents=True,exist_ok=True)
    with db() as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('user','admin')),created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts(ip TEXT NOT NULL,created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),title TEXT NOT NULL,created REAL NOT NULL,updated REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,conversation_id TEXT NOT NULL REFERENCES conversations(id),role TEXT NOT NULL,content TEXT NOT NULL,image_count INTEGER NOT NULL DEFAULT 0,created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS cases(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT NOT NULL REFERENCES users(id),conversation_id TEXT REFERENCES conversations(id),model TEXT NOT NULL,issue TEXT NOT NULL,status TEXT NOT NULL,quoted_price REAL,created REAL NOT NULL,updated REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS case_events(id INTEGER PRIMARY KEY,case_id INTEGER NOT NULL REFERENCES cases(id),actor TEXT NOT NULL REFERENCES users(id),status TEXT NOT NULL,note TEXT NOT NULL,created REAL NOT NULL);
        ''')
        c.executescript("""
        CREATE TABLE IF NOT EXISTS case_quotes(id INTEGER PRIMARY KEY AUTOINCREMENT,case_id INTEGER NOT NULL REFERENCES cases(id),amount REAL NOT NULL,status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','superseded')),created REAL NOT NULL,decided REAL,decided_by TEXT REFERENCES users(id),member_note TEXT NOT NULL DEFAULT '');
        CREATE INDEX IF NOT EXISTS quotes_case ON case_quotes(case_id,id);
        CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT,case_id INTEGER NOT NULL REFERENCES cases(id),quote_id INTEGER NOT NULL REFERENCES case_quotes(id),user_id TEXT NOT NULL REFERENCES users(id),amount_satang INTEGER NOT NULL,currency TEXT NOT NULL DEFAULT 'thb',session_id TEXT UNIQUE,checkout_url TEXT,status TEXT NOT NULL CHECK(status IN ('pending','paid','expired','failed')),created REAL NOT NULL,updated REAL NOT NULL,paid_at REAL);
        CREATE UNIQUE INDEX IF NOT EXISTS payments_one_paid_per_quote ON payments(quote_id) WHERE status='paid';
        CREATE TABLE IF NOT EXISTS stripe_events(id TEXT PRIMARY KEY,type TEXT NOT NULL,received REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS chat_images(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),conversation_id TEXT REFERENCES conversations(id),kind TEXT NOT NULL,observation TEXT NOT NULL DEFAULT '',storage TEXT NOT NULL,key TEXT NOT NULL,size INTEGER NOT NULL,sha256 TEXT NOT NULL,created REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS chat_images_conversation ON chat_images(conversation_id);
        """)
        if 'image_ids' not in [r[1] for r in c.execute('PRAGMA table_info(messages)')]:
            c.execute("ALTER TABLE messages ADD COLUMN image_ids TEXT NOT NULL DEFAULT ''")
        # status = status change, note = shop message without a status change, reply = member message to the shop.
        if 'kind' not in [r[1] for r in c.execute('PRAGMA table_info(case_events)')]:
            c.execute("ALTER TABLE case_events ADD COLUMN kind TEXT NOT NULL DEFAULT 'status'")
        # Preserve existing waiting cases, adding a versioned quote once.
        c.execute("INSERT INTO case_quotes(case_id,amount,status,created) SELECT id,quoted_price,'pending',updated FROM cases WHERE status='awaiting_approval' AND quoted_price IS NOT NULL AND NOT EXISTS(SELECT 1 FROM case_quotes WHERE case_id=cases.id)")
        password=os.getenv('ADMIN_PASSWORD','')
        username=os.getenv('ADMIN_USERNAME','admin').lower()
        if password and not c.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone():
            if len(password)<10: raise RuntimeError('ADMIN_PASSWORD must be at least 10 characters')
            c.execute('INSERT INTO users VALUES(?,?,?,?,?,?)',(uuid.uuid4().hex,username,'ผู้ดูแล Plimo',password_hash(password),'admin',time.time()))

def public_user(row):return {k:row[k] for k in ['id','username','name','role']}
def optional_user(request):
    token=request.cookies.get('plimo_member','')
    if not token:return None
    with db() as c:
        row=c.execute('SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token=? AND s.expires>?',(hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
        return public_user(row) if row else None
def user(request):
    u=optional_user(request)
    if not u:raise HTTPException(401,'กรุณาเข้าสู่ระบบ')
    return u
def admin(request):
    u=user(request)
    if u['role']!='admin':raise HTTPException(403,'สำหรับผู้ดูแลเท่านั้น')
    return u
def new_session(response,u):
    token=secrets.token_urlsafe(32)
    with db() as c:
        c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
        c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),u['id'],time.time()+604800))
    response.set_cookie('plimo_member',token,httponly=True,samesite='strict',secure=os.getenv('COOKIE_SECURE','false')=='true',max_age=604800)
    response.delete_cookie('plimo_session')

class Credentials(BaseModel):
    model_config=ConfigDict(extra='forbid')
    username:str=Field(min_length=3,max_length=32)
    password:str=Field(min_length=10,max_length=128)
    name:str=Field(default='',max_length=64)

def clean_username(value):
    value=value.strip().lower()
    if not re.fullmatch(r'[a-z0-9_.-]{3,32}',value):raise HTTPException(422,'ชื่อบัญชีใช้ a-z, 0-9, จุด ขีด และขีดล่าง 3–32 ตัว')
    return value
AUTH_IP_LIMIT=int(os.getenv('AUTH_IP_LIMIT','100'))
def client_ip(request):
    """nginx sets X-Forwarded-For to the real client (real_ip trusts only the proxy network)."""
    forwarded=request.headers.get('x-forwarded-for','').split(',')[0].strip()
    return forwarded or (request.client.host if request.client else 'unknown')
def auth_limit(request,username=''):
    # Per account+IP stops guessing one password; the wide per-IP cap keeps a
    # classroom behind one NAT from locking everyone out at once.
    ip=client_ip(request);now=time.time();keys=[ip,ip+'|'+username[:64]]
    with db() as c:
        c.execute('DELETE FROM attempts WHERE created<?',(now-900,))
        per_ip,per_account=(c.execute('SELECT COUNT(*) FROM attempts WHERE ip=?',(k,)).fetchone()[0] for k in keys)
        if per_account>=10 or per_ip>=AUTH_IP_LIMIT:raise HTTPException(429,'ลองเข้าสู่ระบบบ่อยเกินไป กรุณารอ 15 นาที')
        c.executemany('INSERT INTO attempts VALUES(?,?)',[(k,now) for k in keys])

@router.post('/auth/register')
def register(body:Credentials,request:Request,response:Response):
    auth_limit(request,body.username.strip().lower());name=clean_username(body.username)
    u={'id':uuid.uuid4().hex,'username':name,'name':body.name.strip() or name,'role':'user'}
    try:
        with db() as c:c.execute('INSERT INTO users VALUES(?,?,?,?,?,?)',(u['id'],name,u['name'],password_hash(body.password),'user',time.time()))
    except sqlite3.IntegrityError:raise HTTPException(409,'ชื่อบัญชีนี้มีผู้ใช้แล้ว')
    new_session(response,u);return {'user':u}
@router.post('/auth/login')
def login(body:Credentials,request:Request,response:Response):
    auth_limit(request,body.username.strip().lower());name=clean_username(body.username)
    with db() as c:row=c.execute('SELECT * FROM users WHERE username=?',(name,)).fetchone()
    stored=row['password'] if row else password_hash('dummy-password')
    if not row or not hmac.compare_digest(stored,password_hash(body.password,stored.split(':')[0])):raise HTTPException(401,'ชื่อบัญชีหรือรหัสผ่านไม่ถูกต้อง')
    u=public_user(row);new_session(response,u);return {'user':u}
@router.get('/auth/me')
def me(request:Request):return {'user':optional_user(request)}
@router.post('/auth/logout')
def logout(request:Request,response:Response):
    with db() as c:c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(request.cookies.get('plimo_member','').encode()).hexdigest(),))
    response.delete_cookie('plimo_member');response.delete_cookie('plimo_session');return {'ok':True}

def conversation(u,cid=None,title='บทสนทนาใหม่'):
    with db() as c:
        if cid:
            row=c.execute('SELECT * FROM conversations WHERE id=? AND user_id=?',(cid,u['id'])).fetchone()
            if not row:raise HTTPException(404,'ไม่พบบทสนทนา')
            return cid
        cid=uuid.uuid4().hex;now=time.time()
        c.execute('INSERT INTO conversations VALUES(?,?,?,?,?)',(cid,u['id'],title[:80],now,now));return cid
def history(cid):
    with db() as c:rows=c.execute('SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 8',(cid,)).fetchall()
    return [dict(r) for r in reversed(rows)]
def save_turn(cid,text,answer,image_count,image_ids=()):
    with db() as c:
        now=time.time()
        c.executemany('INSERT INTO messages(conversation_id,role,content,image_count,created,image_ids) VALUES(?,?,?,?,?,?)',[(cid,'user',text,image_count,now,','.join(image_ids)),(cid,'assistant',answer,0,now,'')])
        c.execute('UPDATE conversations SET updated=? WHERE id=?',(now,cid))
@router.get('/member/conversations')
def list_conversations(request:Request):
    u=user(request)
    with db() as c:rows=c.execute('SELECT id,title,created,updated FROM conversations WHERE user_id=? ORDER BY updated DESC LIMIT 50',(u['id'],)).fetchall()
    return {'conversations':[dict(r) for r in rows]}
@router.get('/member/conversations/{cid}')
def get_conversation(cid:str,request:Request):
    u=user(request);conversation(u,cid)
    with db() as c:rows=c.execute('SELECT role,content,image_count,created,image_ids FROM messages WHERE conversation_id=? ORDER BY id LIMIT 500',(cid,)).fetchall()
    return {'id':cid,'messages':[message_data(r) for r in rows]}
def message_data(row):
    d=dict(row);d['image_ids']=[x for x in (d.get('image_ids') or '').split(',') if x];return d
def save_image(u,cid,image_id,kind,observation,storage,key,size,sha):
    with db() as c:c.execute('INSERT INTO chat_images VALUES(?,?,?,?,?,?,?,?,?,?)',(image_id,u['id'],cid,kind,observation[:1000],storage,key,size,sha,time.time()))
def image_for(u,image_id):
    """The owner sees their images; an admin sees images of conversations attached to a repair case."""
    with db() as c:
        row=c.execute('SELECT * FROM chat_images WHERE id=?',(image_id,)).fetchone()
        if not row:return None
        if row['user_id']==u['id']:return row
        if u['role']=='admin' and c.execute('SELECT 1 FROM cases WHERE conversation_id=?',(row['conversation_id'],)).fetchone():return row
    return None

class CaseBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    model:str=Field(min_length=3,max_length=80)
    issue:str=Field(min_length=5,max_length=2000)
    conversation_id:str|None=None
def payments_enabled():
    # Demo deployment: only Stripe test-mode keys are ever accepted.
    return os.getenv('STRIPE_SECRET_KEY','').startswith('sk_test_')
def payment_for(c,quote_id):
    row=c.execute("SELECT status,amount_satang,paid_at FROM payments WHERE quote_id=? ORDER BY (status='paid') DESC,id DESC LIMIT 1",(quote_id,)).fetchone()
    return {'status':row['status'],'amount':row['amount_satang']/100,'paid_at':row['paid_at']} if row else None
def case_data(row):
    d=dict(row);d['reference']=f"PLM-{d['id']:05d}"
    with db() as c:
        quote=c.execute('SELECT * FROM case_quotes WHERE case_id=? ORDER BY id DESC LIMIT 1',(d['id'],)).fetchone()
        d['payment']=payment_for(c,quote['id']) if quote else None
        last=c.execute('SELECT kind,note FROM case_events WHERE case_id=? ORDER BY id DESC LIMIT 1',(d['id'],)).fetchone()
    # The member's message is the newest event: the shop still owes an answer.
    d['member_reply']=last['note'] if last and last['kind']=='reply' else None
    d['quote']=dict(quote) if quote else None
    d['can_pay']=bool(quote and quote['status']=='approved' and d['status'] not in ('cancelled','closed') and not (d['payment'] and d['payment']['status']=='paid'))
    d['allowed_transitions']=next_statuses(d['status'],quote)
    return d
def next_statuses(status,quote):
    """Statuses the shop may pick now. The current status first means "message only, keep the status";
    for awaiting_approval it means "send a revised quote"."""
    steps=list(TRANSITIONS[status])
    approved=bool(quote and quote['status']=='approved')
    if status=='awaiting_approval' and not approved:steps.remove('repairing')
    # Cases moved to repairing before a quote was required can still get one.
    if status=='repairing' and not approved:steps.append('awaiting_approval')
    if steps:steps.insert(0,status)
    return steps
CASE_MODEL=re.compile(r'^iPhone (11|12|13|14|15|16|17)(?: (?:Pro Max|Pro|Plus|mini))?$')
def open_case(u,model,issue,conversation_id=None,note='สมาชิกส่งคำขอซ่อม'):
    """Shared by the portal form and confirmed chat requests: same validation either way."""
    if len(issue.strip())<5:raise HTTPException(422,'กรุณาระบุอาการอย่างน้อย 5 ตัวอักษร')
    if conversation_id:conversation(u,conversation_id)
    if not CASE_MODEL.match(model):raise HTTPException(422,'กรุณาเลือกรุ่น iPhone 11–17')
    with db() as c:
        now=time.time();r=c.execute('INSERT INTO cases(user_id,conversation_id,model,issue,status,created,updated) VALUES(?,?,?,?,?,?,?)',(u['id'],conversation_id,model,issue.strip()[:2000],'submitted',now,now));cid=r.lastrowid
        c.execute('INSERT INTO case_events(case_id,actor,status,note,created) VALUES(?,?,?,?,?)',(cid,u['id'],'submitted',note,now))
        row=c.execute('SELECT * FROM cases WHERE id=?',(cid,)).fetchone()
    return case_data(row)
@router.post('/member/cases')
def create_case(body:CaseBody,request:Request):
    return {'case':open_case(user(request),body.model,body.issue,body.conversation_id)}
@router.get('/member/cases')
def list_cases(request:Request):
    u=user(request)
    with db() as c:rows=c.execute('SELECT * FROM cases WHERE user_id=? ORDER BY id DESC LIMIT 100',(u['id'],)).fetchall()
    return {'cases':[case_data(r) for r in rows],'payments_enabled':payments_enabled()}
@router.get('/member/cases/{cid}')
def get_case(cid:int,request:Request):
    u=user(request)
    with db() as c:
        row=c.execute('SELECT * FROM cases WHERE id=? AND user_id=?',(cid,u['id'])).fetchone()
        if not row:raise HTTPException(404,'ไม่พบเคส')
        events=c.execute('SELECT status,note,created,kind FROM case_events WHERE case_id=? ORDER BY id',(cid,)).fetchall()
    return {'case':case_data(row),'events':[dict(r) for r in events]}
@router.get('/admin/cases')
def admin_cases(request:Request):
    admin(request)
    with db() as c:
        rows=c.execute('SELECT cases.*,users.name AS member_name FROM cases JOIN users ON users.id=cases.user_id ORDER BY cases.id DESC LIMIT 200').fetchall()
        counts=dict(c.execute('SELECT status,COUNT(*) FROM cases GROUP BY status').fetchall())
    return {'cases':[case_data(r) for r in rows],'counts':{s:counts.get(s,0) for s in STATUSES},'transitions':TRANSITIONS}
@router.get('/admin/cases/{cid}')
def admin_case(cid:int,request:Request):
    admin(request)
    with db() as c:
        row=c.execute('SELECT * FROM cases WHERE id=?',(cid,)).fetchone()
        if not row:raise HTTPException(404,'ไม่พบเคส')
        messages=c.execute('SELECT role,content,image_count,created,image_ids FROM messages WHERE conversation_id=? ORDER BY id LIMIT 500',(row['conversation_id'],)).fetchall() if row['conversation_id'] else []
        events=c.execute('SELECT status,note,created,kind FROM case_events WHERE case_id=? ORDER BY id',(cid,)).fetchall()
        images=c.execute('SELECT id,kind,observation,created FROM chat_images WHERE conversation_id=? ORDER BY created',(row['conversation_id'],)).fetchall() if row['conversation_id'] else []
    return {'case':case_data(row),'messages':[message_data(r) for r in messages],'events':[dict(r) for r in events],'images':[dict(r) for r in images]}
class CaseUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    status:str
    note:str=Field(min_length=3,max_length=1000)
    quoted_price:float|None=Field(default=None,ge=0,le=1000000)
@router.patch('/admin/cases/{cid}')
def update_case(cid:int,body:CaseUpdate,request:Request):
    u=admin(request)
    if len(body.note.strip())<3:raise HTTPException(422,'กรุณาระบุหมายเหตุอย่างน้อย 3 ตัวอักษร')
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM cases WHERE id=?',(cid,)).fetchone()
        if not row:raise HTTPException(404,'ไม่พบเคส')
        quote=c.execute('SELECT * FROM case_quotes WHERE case_id=? ORDER BY id DESC LIMIT 1',(cid,)).fetchone()
        if body.status not in next_statuses(row['status'],quote):raise HTTPException(409,'สถานะเปลี่ยนไม่ได้ตามขั้นตอน กรุณาโหลดข้อมูลใหม่')
        now=time.time()
        if body.status==row['status']!='awaiting_approval':
            # Message only: the status and the quoted price stay as they are.
            if body.quoted_price is not None and body.quoted_price!=row['quoted_price']:raise HTTPException(409,'เปลี่ยนราคาได้เฉพาะตอนส่งใบเสนอราคา (รออนุมัติราคา)')
            c.execute('UPDATE cases SET updated=? WHERE id=?',(now,cid))
            c.execute("INSERT INTO case_events(case_id,actor,status,note,created,kind) VALUES(?,?,?,?,?,'note')",(cid,u['id'],row['status'],body.note.strip(),now))
            return {'ok':True}
        if quote and body.status in ('awaiting_approval','cancelled') and c.execute("SELECT 1 FROM payments WHERE quote_id=? AND status='paid'",(quote['id'],)).fetchone():
            # Refunds are out of scope: a paid quote cannot be replaced or cancelled here.
            raise HTTPException(409,'เคสนี้ชำระเงินแล้ว ต้องคืนเงินผ่าน Stripe ก่อนจึงจะเปลี่ยนราคาหรือยกเลิกได้')
        price=body.quoted_price if body.quoted_price is not None else row['quoted_price']
        if body.status=='awaiting_approval':
            if price is None:raise HTTPException(422,'กรุณาระบุราคาเสนอให้ลูกค้าอนุมัติ')
            c.execute("UPDATE case_quotes SET status='superseded' WHERE case_id=? AND status IN ('pending','approved')",(cid,))
            c.execute("INSERT INTO case_quotes(case_id,amount,status,created) VALUES(?,?,'pending',?)",(cid,price,now))
        elif body.status=='repairing' and (row['status']=='awaiting_approval' or price is not None):
            if not quote or quote['status']!='approved' or quote['amount']!=price:raise HTTPException(409,'ลูกค้าต้องอนุมัติราคาเสนอปัจจุบันก่อนเริ่มซ่อม')
        elif body.quoted_price is not None and row['status'] in {'repairing','ready'} and price!=row['quoted_price']:
            raise HTTPException(409,'ไม่สามารถเปลี่ยนราคาที่อนุมัติหลังเริ่มซ่อม')
        if body.status=='cancelled':
            c.execute("UPDATE case_quotes SET status='superseded' WHERE case_id=? AND status='pending'",(cid,))
        c.execute('UPDATE cases SET status=?,quoted_price=?,updated=? WHERE id=?',(body.status,price,now,cid))
        c.execute('INSERT INTO case_events(case_id,actor,status,note,created) VALUES(?,?,?,?,?)',(cid,u['id'],body.status,body.note.strip(),now))
    return {'ok':True}

class CaseReply(BaseModel):
    model_config=ConfigDict(extra='forbid')
    note:str=Field(min_length=1,max_length=1000)
@router.post('/member/cases/{cid}/reply')
def reply_case(cid:int,body:CaseReply,request:Request):
    """Member answers the shop (e.g. confirms the model) on the case itself; the status does not change."""
    u=user(request);note=body.note.strip()
    if not note:raise HTTPException(422,'กรุณาพิมพ์ข้อความ')
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM cases WHERE id=? AND user_id=?',(cid,u['id'])).fetchone()
        if not row:raise HTTPException(404,'ไม่พบเคส')
        if row['status'] in ('closed','cancelled'):raise HTTPException(409,'เคสนี้ปิดแล้ว กรุณาส่งเคสใหม่หรือติดต่อร้าน')
        now=time.time()
        c.execute('UPDATE cases SET updated=? WHERE id=?',(now,cid))
        c.execute("INSERT INTO case_events(case_id,actor,status,note,created,kind) VALUES(?,?,?,?,?,'reply')",(cid,u['id'],row['status'],note,now))
    return {'ok':True}

class QuoteDecision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    quote_id:int=Field(gt=0)
    decision:str=Field(pattern='^(approve|reject)$')
    note:str=Field(default='',max_length=1000)

@router.post('/member/cases/{cid}/quote-decision')
def decide_quote(cid:int,body:QuoteDecision,request:Request):
    return quote_decision(user(request),cid,body.quote_id,body.decision,body.note)
def quote_decision(u,cid,quote_id,decision,member_note=''):
    """Approve/reject the current pending quote; stale or foreign quotes are refused (also for chat)."""
    body=QuoteDecision(quote_id=quote_id,decision=decision,note=member_note)
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        case=c.execute('SELECT * FROM cases WHERE id=? AND user_id=?',(cid,u['id'])).fetchone()
        if not case:raise HTTPException(404,'ไม่พบเคส')
        q=c.execute('SELECT * FROM case_quotes WHERE case_id=? ORDER BY id DESC LIMIT 1',(cid,)).fetchone()
        if case['status']!='awaiting_approval' or not q or q['id']!=body.quote_id or q['status']!='pending':raise HTTPException(409,'ราคาเสนอเปลี่ยนแล้วหรือบันทึกคำตอบแล้ว กรุณาโหลดเคสใหม่')
        approved=body.decision=='approve';now=time.time();status='awaiting_approval' if approved else 'checking'
        c.execute('UPDATE case_quotes SET status=?,decided=?,decided_by=?,member_note=? WHERE id=?',('approved' if approved else 'rejected',now,u['id'],body.note.strip(),q['id']))
        c.execute('UPDATE cases SET status=?,updated=? WHERE id=?',(status,now,cid))
        note=('สมาชิกอนุมัติราคา' if approved else 'สมาชิกปฏิเสธราคา รอร้านประเมินใหม่')+f" {q['amount']:,.2f} บาท (ใบเสนอ #{q['id']})"
        if body.note.strip():note+=' · '+body.note.strip()
        c.execute('INSERT INTO case_events(case_id,actor,status,note,created) VALUES(?,?,?,?,?)',(cid,u['id'],status,note,now))
    return {'ok':True,'decision':'approved' if approved else 'rejected'}

STATUS_NAMES=dict(zip(STATUSES,['ส่งเคสแล้ว','ร้านรับเรื่อง','กำลังตรวจเช็ค','รออนุมัติราคา','กำลังซ่อม','พร้อมรับเครื่อง','ปิดเคส','ยกเลิก']))
is_case_question=nlu.is_case_question
TH=timezone(timedelta(hours=7))
THAI_MONTHS=['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.']
QUOTE_NAMES={'pending':'รอคุณอนุมัติ','approved':'อนุมัติแล้ว','rejected':'ปฏิเสธแล้ว','superseded':'มีใบเสนอใหม่แทน'}
def thai_time(ts):
    t=datetime.fromtimestamp(ts,TH);return f"{t.day} {THAI_MONTHS[t.month-1]} {t.year+543} {t:%H:%M} น."
def status_label(item):
    q=item['quote']
    if item['status']=='awaiting_approval' and q and q['status']=='approved':return 'อนุมัติราคาแล้ว รอร้านเริ่มซ่อม'
    return STATUS_NAMES[item['status']]
def case_lead(item,topic):
    """First sentence: answers the question for this status instead of repeating the same block."""
    ref,st,q,p=item['reference'],item['status'],item['quote'],item.get('payment')
    paid=bool(p and p['status']=='paid')
    if st=='closed':
        if topic=='pickup':return f'เคส {ref} ปิดเรียบร้อยแล้วครับ ร้านปิดเคสหลังส่งมอบงานแล้ว ไม่ต้องทำอะไรเพิ่ม ถ้าคุณยังไม่ได้รับเครื่อง หรือเครื่องมีปัญหาหลังซ่อม กรุณาติดต่อร้านครับ'
        return f'เคส {ref} ปิดเรียบร้อยแล้วครับ งานซ่อมเสร็จ'+('และชำระเงินครบแล้ว' if paid else '')+' ไม่ต้องดำเนินการอะไรเพิ่มครับ'
    if st=='cancelled':return f'เคส {ref} ยกเลิกแล้วครับ ถ้าต้องการซ่อมใหม่ ส่งเคสใหม่ได้ที่ บัญชี → ส่งเคสใหม่'
    if st=='ready':
        if topic=='pickup':return f'เคส {ref} ซ่อมเสร็จแล้วครับ ถ้ารับเครื่องแล้ว ร้านจะปิดเคสให้หลังตรวจการรับเครื่อง'
        return f'เคส {ref} ซ่อมเสร็จแล้ว รับเครื่องที่ร้านได้เลยครับ'+('' if paid or not item.get('can_pay') else ' ชำระค่าซ่อมก่อนหรือตอนรับเครื่องได้')
    if st=='repairing':return f'เคส {ref} ร้านกำลังซ่อมอยู่ครับ ยังรับเครื่องไม่ได้ เมื่อเสร็จสถานะจะเปลี่ยนเป็น "พร้อมรับเครื่อง"'
    if st=='awaiting_approval':
        if q and q['status']=='approved':return f'คุณอนุมัติราคาเคส {ref} แล้วครับ รอร้านเริ่มซ่อม'
        return f'เคส {ref} รอคุณอนุมัติราคาอยู่ครับ ร้านจะเริ่มซ่อมหลังคุณอนุมัติ'
    if st=='checking':return f'ร้านกำลังตรวจเช็คเครื่องเคส {ref} ครับ จะส่งใบเสนอราคาให้คุณอนุมัติก่อนเริ่มซ่อม'
    if st=='received':return f'ร้านรับเรื่องเคส {ref} แล้วครับ ขั้นต่อไปคือตรวจเช็คเครื่อง'
    return f'ส่งเคส {ref} แล้วครับ รอร้านรับเรื่อง'
def case_lines(item,events,topic):
    q=item['quote'];lines=[f"{item['reference']} · {item['model']} · สถานะ: {status_label(item)}",'อัปเดตล่าสุด: '+thai_time(item['updated'])]
    note=next((e['note'] for e in reversed(events) if e['note'] and e['kind']!='reply'),'')
    # A closed or cancelled case needs no "what to do next" from the shop.
    if note and (item['status'] not in ('closed','cancelled') or topic=='note'):lines.append('ข้อความล่าสุดจากร้าน: '+note[:300])
    if q:
        lines.append(f"ใบเสนอราคา #{q['id']}: {q['amount']:,.2f} บาท · {QUOTE_NAMES[q['status']]}")
        if q['status']=='pending' and item['status']=='awaiting_approval':lines.append('อนุมัติหรือปฏิเสธราคาได้ที่ บัญชี → งานซ่อมของฉัน')
    elif topic in ('price','payment'):lines.append('เคสนี้ยังไม่มีใบเสนอราคา ทางร้านจะเสนอราคาหลังตรวจเช็ค')
    lines.extend(case_extra_lines(item,topic))
    if topic=='action':lines.append('แชทไม่สามารถยกเลิก อนุมัติ หรือแก้ไขเคสแทนคุณได้ กรุณาทำที่ บัญชี → งานซ่อมของฉัน หรือแจ้งทางร้านครับ')
    if topic=='pickup' and item['status'] in ('submitted','received','checking','awaiting_approval'):lines.append('เมื่อซ่อมเสร็จ สถานะจะเปลี่ยนเป็น "พร้อมรับเครื่อง" ตรวจได้ในบัญชีหรือถามในแชทนี้ครับ')
    return lines
def case_extra_lines(item,topic):
    """Payment state from SQLite only; the chat never confirms a payment itself."""
    p=item.get('payment')
    if p and p['status']=='paid':return [f"การชำระเงิน: ชำระแล้ว {p['amount']:,.2f} บาท เมื่อ {thai_time(p['paid_at'])} (Stripe โหมดทดสอบ)"]
    if item.get('can_pay'):
        return ['การชำระเงิน: ยังไม่ชำระ — กดปุ่ม "ชำระเงิน" ใน บัญชี → งานซ่อมของฉัน (Stripe โหมดทดสอบ)' if payments_enabled() else 'การชำระเงิน: ยังไม่ชำระ ร้านยังไม่เปิดชำระเงินออนไลน์']
    if topic=='payment':return ['การชำระเงิน: ชำระได้หลังอนุมัติใบเสนอราคาแล้วเท่านั้น']
    return []
def case_answer(u,text,ref=None,topic='status'):
    """Case status straight from SQLite. Returns (answer, case id answered or None)."""
    if not u:return 'กรุณาเข้าสู่ระบบก่อนถามสถานะเคสของคุณครับ หลังเข้าสู่ระบบพิมพ์เลขเคส เช่น PLM-00012 ได้เลยครับ',None
    ref=ref or nlu.parse_case_ref(text)
    with db() as c:
        if ref:rows=c.execute('SELECT * FROM cases WHERE id=? AND user_id=?',(ref,u['id'])).fetchall()
        else:rows=c.execute('SELECT * FROM cases WHERE user_id=? ORDER BY updated DESC,id DESC LIMIT 5',(u['id'],)).fetchall()
        events={r['id']:c.execute('SELECT status,note,created,kind FROM case_events WHERE case_id=? ORDER BY id',(r['id'],)).fetchall() for r in rows}
    # Someone else's case and a missing case get the same reply: no existence leak.
    if not rows:return ('ไม่พบเคสนี้ในบัญชีของคุณครับ กรุณาตรวจเลข PLM อีกครั้ง' if ref else 'บัญชีของคุณยังไม่มีเคสซ่อมครับ'),None
    if len(rows)==1:
        item=case_data(rows[0])
        return case_lead(item,topic)+'\n\nรายละเอียดจากระบบ\n'+'\n'.join(case_lines(item,events[item['id']],topic)),item['id']
    lines=['สถานะล่าสุดจากระบบเคสของคุณครับ']
    for row in rows:
        item=case_data(row);q=item['quote']
        lines.append(item['reference']+' · '+item['model']+' · '+status_label(item))
        if q and q['status']=='pending' and item['status']=='awaiting_approval':lines.append(f"ราคาเสนอ {q['amount']:,.2f} บาท — เปิดบัญชี → งานซ่อมของฉัน เพื่ออนุมัติหรือปฏิเสธราคา")
    lines.append('แสดงสูงสุด 5 เคสล่าสุด ระบุเลข PLM-xxxxx เพื่อดูรายละเอียดเคสที่ต้องการ')
    return '\n\n'.join(lines),None
