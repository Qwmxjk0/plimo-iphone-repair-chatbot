import os,tempfile,unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
import membership,main
from test_chat import MemoryRedis

class MemberTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=patch.object(membership,'DB_PATH',self.tmp.name+'/test.sqlite3');self.p.start()
        with patch.dict(os.environ,{'ADMIN_USERNAME':'admin','ADMIN_PASSWORD':'test-admin-password'}):membership.init_db()
        self.a=TestClient(main.app);self.b=TestClient(main.app);self.ad=TestClient(main.app)
        self.a.post('/api/auth/register',json={'username':'alice','password':'alice-test-password','name':'อลิซ'})
        self.b.post('/api/auth/register',json={'username':'bob','password':'bob-test-password','name':'บ๊อบ'})
        self.ad.post('/api/auth/login',json={'username':'admin','password':'test-admin-password'})
    def tearDown(self):self.p.stop();self.tmp.cleanup()
    def test_ownership_and_admin_permissions(self):
        u=self.a.get('/api/auth/me').json()['user'];cid=membership.conversation(u,title='ทดสอบส่วนตัว');membership.save_turn(cid,'ข้อความส่วนตัว','คำตอบ',1)
        self.assertEqual(self.a.get('/api/member/conversations/'+cid).status_code,200)
        self.assertEqual(self.b.get('/api/member/conversations/'+cid).status_code,404)
        self.assertEqual(self.b.post('/api/member/cases',json={'model':'iPhone 13','issue':'หน้าจอเสีย','conversation_id':cid}).status_code,404)
        self.assertEqual(self.a.get('/api/admin/cases').status_code,403)
        self.assertEqual(TestClient(main.app).get('/api/member/cases').status_code,401)
    def test_case_lifecycle_counts_and_audit(self):
        c=self.a.post('/api/member/cases',json={'model':'iPhone 13 Pro Max','issue':'หน้าจอไม่ติด'}).json()['case'];cid=c['id']
        self.assertEqual(self.b.get('/api/member/cases/'+str(cid)).status_code,404)
        self.assertEqual(self.a.patch('/api/admin/cases/'+str(cid),json={'status':'received','note':'รับเรื่อง'}).status_code,403)
        self.assertEqual(self.ad.patch('/api/admin/cases/'+str(cid),json={'status':'closed','note':'ข้ามขั้น'}).status_code,409)
        self.assertEqual(self.ad.patch('/api/admin/cases/'+str(cid),json={'status':'received','note':'รับเคสแล้ว'}).status_code,200)
        self.assertEqual(self.ad.get('/api/admin/cases').json()['counts']['received'],1)
        detail=self.a.get('/api/member/cases/'+str(cid)).json();self.assertEqual(detail['case']['status'],'received');self.assertEqual(len(detail['events']),2)
    def test_roles_logout_and_csrf(self):
        r=TestClient(main.app).post('/api/auth/register',json={'username':'hacker','password':'test-password-123','role':'admin'})
        self.assertEqual(r.status_code,422)
        self.assertEqual(self.a.post('/api/auth/logout',headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.a.post('/api/auth/logout').status_code,200)
        self.assertEqual(self.a.get('/api/member/cases').status_code,401)
        with membership.db() as c:
            stored=c.execute('SELECT password FROM users WHERE username=?',('alice',)).fetchone()[0]
        self.assertNotIn('alice-test-password',stored)
    def test_chat_persists_and_isolated_across_members(self):
        async def retrieve(query,session):return {'chunks':[{'content':'ข้อมูลทดสอบ'}],'sources':[]},False
        async def generate(*args):return 'คำตอบทดสอบส่วนตัว'
        with patch.object(main,'OPENAI_KEY','test'),patch.object(main,'RAG_KEY','test'),patch.object(main,'cache',MemoryRedis()),patch.object(main,'retrieve',retrieve),patch.object(main,'generate',generate):
            result=self.a.post('/api/chat',data={'text':'ข้อความส่วนตัวของอลิซ'})
            self.assertEqual(result.status_code,200);cid=result.json()['conversation_id']
            self.assertEqual(len(self.a.get('/api/member/conversations/'+cid).json()['messages']),2)
            self.assertEqual(self.b.post('/api/chat',data={'text':'อ่านข้อมูลคนอื่น','conversation_id':cid}).status_code,404)
            # Redis disappears; owned text history remains in the SQLite volume.
            main.cache.values.clear()
            self.assertEqual(len(membership.history(cid)),2)
            self.assertEqual(self.b.get('/api/member/conversations').json()['conversations'],[])

if __name__=='__main__':unittest.main()
