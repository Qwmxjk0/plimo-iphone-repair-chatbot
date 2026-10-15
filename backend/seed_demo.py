"""Explicit user-requested demo accounts/data. Idempotent; no provider calls."""
import time,uuid
import membership as m

def seed():
    m.init_db()
    with m.db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS demo_seed(version TEXT PRIMARY KEY)')
        if c.execute('SELECT 1 FROM demo_seed WHERE version=?',('members-v1',)).fetchone():
            print('Demo records already exist; preserved.');return
        now=time.time();ids={}
        for username,password,name,role in [('demo_user','PlimoMemberDemo2026!','สมาชิกตัวอย่าง','user'),('demo_admin','PlimoAdminDemo2026!','ผู้ดูแลตัวอย่าง','admin')]:
            row=c.execute('SELECT id FROM users WHERE username=?',(username,)).fetchone()
            uid=row['id'] if row else uuid.uuid4().hex;ids[role]=uid
            if not row:c.execute('INSERT INTO users VALUES(?,?,?,?,?,?)',(uid,username,name,m.password_hash(password),role,now))
        conversations=[]
        examples=[('ตัวอย่าง · ราคาเปลี่ยนหน้าจอ iPhone 13','เปลี่ยนหน้าจอ iPhone 13 ราคาเท่าไร','[ประวัติตัวอย่างสำหรับเดโม] ราคาเริ่มต้นสาธิต 3,200 บาทสำหรับ iPhone 13 รุ่นปกติ ไม่ใช่ราคาเสนอจริงของร้าน ต้องตรวจเครื่องก่อนยืนยันราคา'),('ตัวอย่าง · แบตเตอรี่ iPhone 12','แบตเตอรี่หมดเร็ว มีราคาตัวอย่างไหม','[ประวัติตัวอย่างสำหรับเดโม] เปลี่ยนแบตเตอรี่ iPhone 11–13 มีราคาสาธิตเริ่มต้น 990 บาท เงื่อนไขและราคาจริงต้องยืนยันกับร้าน'),('ตัวอย่าง · รุ่น Pro Max','iPhone 13 Pro Max ใช้ราคาเดียวกับ iPhone 13 ได้ไหม','[ประวัติตัวอย่างสำหรับเดโม] ยังไม่มีราคาสาธิตเฉพาะ iPhone 13 Pro Max ห้ามนำราคาของรุ่นปกติมาใช้โดยอัตโนมัติ')]
        for i,(title,q,a) in enumerate(examples):
            cid=uuid.uuid4().hex;created=now-(3-i)*86400;conversations.append(cid)
            c.execute('INSERT INTO conversations VALUES(?,?,?,?,?)',(cid,ids['user'],title,created,created))
            c.executemany('INSERT INTO messages(conversation_id,role,content,image_count,created) VALUES(?,?,?,?,?)',[(cid,'user',q,0,created),(cid,'assistant',a,0,created+5)])
        sequences=[['submitted'],['submitted'],['submitted','received'],['submitted','received','checking'],['submitted','received','checking','awaiting_approval'],['submitted','received','checking','awaiting_approval','repairing'],['submitted','received','checking','repairing','ready'],['submitted','received','checking','repairing','ready','closed']]
        for i,statuses in enumerate(sequences):
            created=now-(8-i)*3600;model=['iPhone 13','iPhone 12','iPhone 13 Pro Max'][i%3]
            issue='[เคสตัวอย่างสำหรับเดโม] '+['หน้าจอแตก ต้องการให้ร้านตรวจเช็ค','แบตเตอรี่หมดเร็ว ขอประเมินอาการ','เครื่องเปิดไม่ติด ขอให้ตรวจเบื้องต้น'][i%3]
            row=c.execute('INSERT INTO cases(user_id,conversation_id,model,issue,status,quoted_price,created,updated) VALUES(?,?,?,?,?,?,?,?)',(ids['user'],conversations[i%3],model,issue,statuses[-1],(3200 if model=='iPhone 13' else 990 if model=='iPhone 12' else None) if i>=4 else None,created,created+len(statuses)*60));case_id=row.lastrowid
            if statuses[-1]=='awaiting_approval':
                amount=3200 if model=='iPhone 13' else 990 if model=='iPhone 12' else None
                if amount is not None:c.execute("INSERT INTO case_quotes(case_id,amount,status,created) VALUES(?,?,'pending',?)",(case_id,amount,created+len(statuses)*60))
            for j,status in enumerate(statuses):c.execute('INSERT INTO case_events(case_id,actor,status,note,created) VALUES(?,?,?,?,?)',(case_id,ids['user'] if j==0 else ids['admin'],status,'ข้อมูลตัวอย่างสำหรับสาธิตสถานะ ไม่ใช่งานซ่อมจริง',created+j*60))
        c.execute('INSERT INTO demo_seed VALUES(?)',('members-v1',))
    print('Created 2 demo accounts, 3 example conversations, 8 example cases. No AI calls.')

def lock_demo_admin():
    """Public servers: the demo admin password is in the repo, so replace it with a random one."""
    import secrets
    with m.db() as c:c.execute("UPDATE users SET password=? WHERE username='demo_admin'",(m.password_hash(secrets.token_urlsafe(32)),))
    print('demo_admin locked; use ADMIN_USERNAME / ADMIN_PASSWORD from .env for admin access.')

if __name__=='__main__':
    import sys
    seed()
    if '--lock-admin' in sys.argv:lock_demo_admin()
