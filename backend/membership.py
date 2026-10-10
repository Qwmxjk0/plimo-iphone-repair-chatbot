"""Local MVP: persistent users, owned conversations and repair case workflow."""
import hashlib, hmac, json, os, re, secrets, sqlite3, time, uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

router=APIRouter(prefix='/api')
DB_PATH=os.getenv('MEMBER_DB','/app/data/members.sqlite3')
STATUSES=['submitted','received','checking','awaiting_approval','repairing','ready','closed','cancelled']
TRANSITIONS={'submitted':['received','cancelled'],'received':['checking','cancelled'],'checking':['awaiting_approval','repairing','cancelled'],'awaiting_approval':['repairing','cancelled'],'repairing':['ready'],'ready':['closed'],'closed':[],'cancelled':[]}

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
        """)
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
def auth_limit(request):
    ip=request.headers.get('x-forwarded-for',request.client.host if request.client else 'unknown')
    with db() as c:
        c.execute('DELETE FROM attempts WHERE created<?',(time.time()-900,))
        if c.execute('SELECT COUNT(*) FROM attempts WHERE ip=?',(ip,)).fetchone()[0]>=10:raise HTTPException(429,'ลองเข้าสู่ระบบบ่อยเกินไป กรุณารอ 15 นาที')
        c.execute('INSERT INTO attempts VALUES(?,?)',(ip,time.time()))

@router.post('/auth/register')
def register(body:Credentials,request:Request,response:Response):
    auth_limit(request);name=clean_username(body.username)
    u={'id':uuid.uuid4().hex,'username':name,'name':body.name.strip() or name,'role':'user'}
    try:
        with db() as c:c.execute('INSERT INTO users VALUES(?,?,?,?,?,?)',(u['id'],name,u['name'],password_hash(body.password),'user',time.time()))
    except sqlite3.IntegrityError:raise HTTPException(409,'ชื่อบัญชีนี้มีผู้ใช้แล้ว')
    new_session(response,u);return {'user':u}
@router.post('/auth/login')
def login(body:Credentials,request:Request,response:Response):
    auth_limit(request);name=clean_username(body.username)
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
def save_turn(cid,text,answer,image_count):
    with db() as c:
        now=time.time()
        c.executemany('INSERT INTO messages(conversation_id,role,content,image_count,created) VALUES(?,?,?,?,?)',[(cid,'user',text,image_count,now),(cid,'assistant',answer,0,now)])
        c.execute('UPDATE conversations SET updated=? WHERE id=?',(now,cid))
@router.get('/member/conversations')
def list_conversations(request:Request):
    u=user(request)
    with db() as c:rows=c.execute('SELECT id,title,created,updated FROM conversations WHERE user_id=? ORDER BY updated DESC LIMIT 50',(u['id'],)).fetchall()
    return {'conversations':[dict(r) for r in rows]}
@router.get('/member/conversations/{cid}')
def get_conversation(cid:str,request:Request):
    u=user(request);conversation(u,cid)
    with db() as c:rows=c.execute('SELECT role,content,image_count,created FROM messages WHERE conversation_id=? ORDER BY id LIMIT 500',(cid,)).fetchall()
    return {'id':cid,'messages':[dict(r) for r in rows]}

class CaseBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    model:str=Field(min_length=3,max_length=80)
    issue:str=Field(min_length=5,max_length=2000)
    conversation_id:str|None=None
def case_data(row):
    d=dict(row);d['reference']=f"PLM-{d['id']:05d}"
    with db() as c:quote=c.execute('SELECT * FROM case_quotes WHERE case_id=? ORDER BY id DESC LIMIT 1',(d['id'],)).fetchone()
    d['quote']=dict(quote) if quote else None
    next_steps=list(TRANSITIONS[d['status']])
    if d['status']=='awaiting_approval' and (not quote or quote['status']!='approved'):
        next_steps=[s for s in next_steps if s!='repairing']
    if d['status']=='awaiting_approval':next_steps.insert(0,'awaiting_approval')
    d['allowed_transitions']=next_steps
    return d
@router.post('/member/cases')
def create_case(body:CaseBody,request:Request):
    u=user(request)
    if len(body.issue.strip())<5:raise HTTPException(422,'กรุณาระบุอาการอย่างน้อย 5 ตัวอักษร')
    if body.conversation_id:conversation(u,body.conversation_id)
    if not re.match(r'^iPhone (11|12|13|14|15|16|17)(?: (?:Pro Max|Pro|Plus|mini))?$',body.model):raise HTTPException(422,'กรุณาเลือกรุ่น iPhone 11–17')
    with db() as c:
        now=time.time();r=c.execute('INSERT INTO cases(user_id,conversation_id,model,issue,status,created,updated) VALUES(?,?,?,?,?,?,?)',(u['id'],body.conversation_id,body.model,body.issue.strip(),'submitted',now,now));cid=r.lastrowid
        c.execute('INSERT INTO case_events(case_id,actor,status,note,created) VALUES(?,?,?,?,?)',(cid,u['id'],'submitted','สมาชิกส่งเคสสาธิต',now))
        row=c.execute('SELECT * FROM cases WHERE id=?',(cid,)).fetchone()
    return {'case':case_data(row)}
@router.get('/member/cases')
def list_cases(request:Request):
    u=user(request)
    with db() as c:rows=c.execute('SELECT * FROM cases WHERE user_id=? ORDER BY id DESC LIMIT 100',(u['id'],)).fetchall()
    return {'cases':[case_data(r) for r in rows]}
@router.get('/member/cases/{cid}')
def get_case(cid:int,request:Request):
    u=user(request)
    with db() as c:
        row=c.execute('SELECT * FROM cases WHERE id=? AND user_id=?',(cid,u['id'])).fetchone()
        if not row:raise HTTPException(404,'ไม่พบเคส')
        events=c.execute('SELECT status,note,created FROM case_events WHERE case_id=? ORDER BY id',(cid,)).fetchall()
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
        messages=c.execute('SELECT role,content,image_count,created FROM messages WHERE conversation_id=? ORDER BY id LIMIT 500',(row['conversation_id'],)).fetchall() if row['conversation_id'] else []
        events=c.execute('SELECT status,note,created FROM case_events WHERE case_id=? ORDER BY id',(cid,)).fetchall()
    return {'case':case_data(row),'messages':[dict(r) for r in messages],'events':[dict(r) for r in events]}
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
        revising=row['status']=='awaiting_approval' and body.status=='awaiting_approval'
        if not revising and body.status not in TRANSITIONS[row['status']]:raise HTTPException(409,'สถานะเปลี่ยนไม่ได้ตามขั้นตอน กรุณาโหลดข้อมูลใหม่')
        quote=c.execute('SELECT * FROM case_quotes WHERE case_id=? ORDER BY id DESC LIMIT 1',(cid,)).fetchone()
        now=time.time();price=body.quoted_price if body.quoted_price is not None else row['quoted_price']
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


class QuoteDecision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    quote_id:int=Field(gt=0)
    decision:str=Field(pattern='^(approve|reject)$')
    note:str=Field(default='',max_length=1000)

@router.post('/member/cases/{cid}/quote-decision')
def decide_quote(cid:int,body:QuoteDecision,request:Request):
    u=user(request)
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
def is_case_question(text):
    return bool(re.search(r'\bPLM-\d+\b|เคสของฉัน|สถานะ.{0,20}(เคส|ซ่อม|เครื่อง)|(เคส|งานซ่อม).{0,20}(ถึงไหน|สถานะ)|ซ่อม.{0,15}เสร็จ|รับเครื่อง.{0,10}ได้ยัง',text,re.I))

def case_answer(u,text):
    if not u:return 'กรุณาเข้าสู่ระบบก่อนถามสถานะเคสของคุณครับ'
    match=re.search(r'\bPLM-(\d+)\b',text,re.I)
    with db() as c:
        if match:
            raw=match.group(1)
            rows=[] if len(raw)>12 else c.execute('SELECT * FROM cases WHERE id=? AND user_id=?',(int(raw),u['id'])).fetchall()
        else:rows=c.execute('SELECT * FROM cases WHERE user_id=? ORDER BY updated DESC,id DESC LIMIT 5',(u['id'],)).fetchall()
    if not rows:return 'ไม่พบเคสนี้ในบัญชีของคุณครับ' if match else 'บัญชีของคุณยังไม่มีเคสซ่อมครับ'
    lines=['สถานะล่าสุดจากระบบเคสของคุณครับ (ระบบสาธิต)']
    for row in rows:
        item=case_data(row);q=item['quote'];label=STATUS_NAMES[item['status']]
        if item['status']=='awaiting_approval' and q and q['status']=='approved':label='อนุมัติราคาแล้ว รอร้านเริ่มซ่อม'
        lines.append(item['reference']+' · '+item['model']+' · '+label)
        if q and q['status']=='pending' and item['status']=='awaiting_approval':lines.append(f"ราคาเสนอสาธิต {q['amount']:,.2f} บาท — เปิดบัญชี → งานซ่อมของฉัน เพื่ออนุมัติหรือปฏิเสธราคา")
    if not match:lines.append('แสดงสูงสุด 5 เคสล่าสุด ระบุเลข PLM-xxxxx เพื่อดูเคสที่ต้องการ')
    return '\n\n'.join(lines)
