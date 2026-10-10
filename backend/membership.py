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
    d=dict(row);d['reference']=f"PLM-{d['id']:05d}";return d
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
        if body.status not in TRANSITIONS[row['status']]:raise HTTPException(409,'สถานะเปลี่ยนไม่ได้ตามขั้นตอน กรุณาโหลดข้อมูลใหม่')
        now=time.time();price=body.quoted_price if body.quoted_price is not None else row['quoted_price']
        c.execute('UPDATE cases SET status=?,quoted_price=?,updated=? WHERE id=?',(body.status,price,now,cid))
        c.execute('INSERT INTO case_events(case_id,actor,status,note,created) VALUES(?,?,?,?,?)',(cid,u['id'],body.status,body.note.strip(),now))
    return {'ok':True}
