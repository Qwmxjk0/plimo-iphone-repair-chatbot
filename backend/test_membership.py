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
        async def retrieve(query,session=None):return {'chunks':[{'content':'ข้อมูลทดสอบ'}],'sources':[]},False
        async def generate(*args):return 'คำตอบทดสอบส่วนตัว'
        async def route(text,history,active,images):return main.router.fallback(text),False
        with patch.object(main,'OPENAI_KEY','test'),patch.object(main,'RAG_KEY','test'),patch.object(main,'cache',MemoryRedis()),patch.object(main,'retrieve',retrieve),patch.object(main,'generate',generate),patch.object(main,'route_message',route):
            result=self.a.post('/api/chat',data={'text':'ข้อความส่วนตัวของอลิซ'})
            self.assertEqual(result.status_code,200);cid=result.json()['conversation_id']
            self.assertEqual(len(self.a.get('/api/member/conversations/'+cid).json()['messages']),2)
            self.assertEqual(self.b.post('/api/chat',data={'text':'อ่านข้อมูลคนอื่น','conversation_id':cid}).status_code,404)
            # Redis disappears; owned text history remains in the SQLite volume.
            main.cache.values.clear()
            self.assertEqual(len(membership.history(cid)),2)
            self.assertEqual(self.b.get('/api/member/conversations').json()['conversations'],[])

    def quote_case(self):
        cid=self.a.post('/api/member/cases',json={'model':'iPhone 13','issue':'หน้าจอแตกทดสอบ'}).json()['case']['id']
        for status in ['received','checking']:
            self.assertEqual(self.ad.patch('/api/admin/cases/'+str(cid),json={'status':status,'note':'ทดสอบขั้นตอน'}).status_code,200)
        self.assertEqual(self.ad.patch('/api/admin/cases/'+str(cid),json={'status':'awaiting_approval','note':'เสนอราคาสาธิต','quoted_price':3200}).status_code,200)
        return cid,self.a.get('/api/member/cases/'+str(cid)).json()['case']['quote']['id']

    def test_case_answer_leads_with_what_the_status_means(self):
        cid=self.a.post('/api/member/cases',json={'model':'iPhone 14','issue':'แบตเสื่อมทดสอบ'}).json()['case']['id']
        u=self.a.get('/api/auth/me').json()['user']
        def ask(topic):return membership.case_answer(u,'',cid,topic)[0]
        self.assertTrue(ask('status').startswith('ส่งเคส PLM-'))
        with membership.db() as c:c.execute("UPDATE cases SET status='closed' WHERE id=?",(cid,))
        closed,pickup=ask('status'),ask('pickup')
        self.assertIn('ปิดเรียบร้อยแล้ว',closed.split('\n')[0])
        self.assertIn('ยังไม่ได้รับเครื่อง',pickup.split('\n')[0])
        self.assertNotEqual(closed.split('\n')[0],pickup.split('\n')[0])
        # A closed case never tells the customer to wait for "พร้อมรับเครื่อง".
        self.assertNotIn('เมื่อซ่อมเสร็จ',pickup)

    def test_no_repair_without_quote_and_message_only(self):
        cid=self.a.post('/api/member/cases',json={'model':'iPhone 11','issue':'แบตเสื่อมทดสอบ'}).json()['case']['id'];url='/api/admin/cases/'+str(cid)
        for status in ['received','checking']:
            self.assertEqual(self.ad.patch(url,json={'status':status,'note':'ทดสอบขั้นตอน'}).status_code,200)
        # Repair cannot start before a quote.
        self.assertEqual(self.ad.patch(url,json={'status':'repairing','note':'เริ่มซ่อม'}).status_code,409)
        # The shop asks a question without moving the case; a price change is not allowed here.
        self.assertEqual(self.ad.patch(url,json={'status':'checking','note':'ยืนยันรุ่นอีกครั้ง','quoted_price':990}).status_code,409)
        self.assertEqual(self.ad.patch(url,json={'status':'checking','note':'ยืนยันรุ่นอีกครั้ง'}).status_code,200)
        reply='/api/member/cases/'+str(cid)+'/reply'
        self.assertEqual(self.b.post(reply,json={'note':'ไม่ใช่เคสฉัน'}).status_code,404)
        self.assertEqual(self.a.post(reply,json={'note':'iPhone 11 ครับ'}).status_code,200)
        case=self.ad.get('/api/admin/cases').json()['cases'][0]
        self.assertEqual((case['id'],case['status'],case['member_reply']),(cid,'checking','iPhone 11 ครับ'))
        events=self.a.get('/api/member/cases/'+str(cid)).json()['events']
        self.assertEqual([e['kind'] for e in events[-2:]],['note','reply'])
        self.assertEqual(self.ad.patch(url,json={'status':'awaiting_approval','note':'ราคาแบต','quoted_price':990}).status_code,200)
        self.assertIsNone(self.ad.get('/api/admin/cases').json()['cases'][0]['member_reply'])

    def test_legacy_repairing_case_can_still_get_quote(self):
        cid=self.a.post('/api/member/cases',json={'model':'iPhone 11','issue':'แบตเสื่อมทดสอบ'}).json()['case']['id']
        with membership.db() as c:c.execute("UPDATE cases SET status='repairing' WHERE id=?",(cid,))
        case=self.a.get('/api/member/cases/'+str(cid)).json()['case']
        self.assertEqual(case['allowed_transitions'],['repairing','ready','awaiting_approval'])
        self.assertEqual(self.ad.patch('/api/admin/cases/'+str(cid),json={'status':'awaiting_approval','note':'ราคาแบต','quoted_price':990}).status_code,200)
        self.assertEqual(self.a.get('/api/member/cases/'+str(cid)).json()['case']['quote']['status'],'pending')

    def test_quote_approval_ownership_and_price_guard(self):
        cid,qid=self.quote_case();url='/api/member/cases/'+str(cid)+'/quote-decision'
        body={'quote_id':qid,'decision':'approve'}
        self.assertEqual(self.b.post(url,json=body).status_code,404)
        self.assertEqual(self.ad.patch('/api/admin/cases/'+str(cid),json={'status':'repairing','note':'เริ่มงาน'}).status_code,409)
        self.assertEqual(self.a.post(url,json=body).status_code,200)
        self.assertEqual(self.a.post(url,json=body).status_code,409)
        self.assertEqual(self.ad.patch('/api/admin/cases/'+str(cid),json={'status':'repairing','note':'เริ่มงาน','quoted_price':3300}).status_code,409)
        self.assertEqual(self.ad.patch('/api/admin/cases/'+str(cid),json={'status':'repairing','note':'เริ่มงาน'}).status_code,200)
        detail=self.a.get('/api/member/cases/'+str(cid)).json()
        self.assertEqual(detail['case']['quote']['status'],'approved')
        self.assertTrue(any('สมาชิกอนุมัติราคา' in ev['note'] for ev in detail['events']))

    def test_quote_revision_reject_and_stale_decision(self):
        cid,old=self.quote_case();url='/api/member/cases/'+str(cid)+'/quote-decision'
        self.assertEqual(self.ad.patch('/api/admin/cases/'+str(cid),json={'status':'awaiting_approval','quoted_price':3500,'note':'ประเมินราคาใหม่'}).status_code,200)
        self.assertEqual(self.a.post(url,json={'quote_id':old,'decision':'approve'}).status_code,409)
        q=self.a.get('/api/member/cases/'+str(cid)).json()['case']['quote']
        self.assertEqual(q['amount'],3500)
        self.assertEqual(self.a.post(url,json={'quote_id':q['id'],'decision':'reject','note':'ขอประเมินใหม่'}).status_code,200)
        c=self.a.get('/api/member/cases/'+str(cid)).json()['case']
        self.assertEqual(c['status'],'checking');self.assertEqual(c['quote']['status'],'rejected')
        self.assertEqual(self.ad.patch('/api/admin/cases/'+str(cid),json={'status':'repairing','note':'ข้ามอนุมัติ'}).status_code,409)

    def test_case_chat_reads_fresh_owned_status_without_openai(self):
        cid,_=self.quote_case();text=f'สถานะเคส PLM-{cid:05d}'
        with patch.object(main,'cache',MemoryRedis()),patch.object(main,'OPENAI_KEY',''),patch.object(main,'generate') as gen,patch.object(main,'retrieve') as rag:
            r=self.a.post('/api/chat',data={'text':text});self.assertEqual(r.status_code,200)
            self.assertIn('รออนุมัติราคา',r.json()['answer']);conv=r.json()['conversation_id']
            self.ad.patch('/api/admin/cases/'+str(cid),json={'status':'cancelled','note':'ยกเลิกตามคำขอ'})
            r=self.a.post('/api/chat',data={'text':text,'conversation_id':conv});self.assertIn('ยกเลิก',r.json()['answer'])
            self.assertFalse(r.json()['cache']['answer']);self.assertFalse(r.json()['rag_used'])
            private=self.b.post('/api/chat',data={'text':text}).json()['answer'];self.assertIn('ไม่พบเคส',private);self.assertNotIn('iPhone 13',private)
            guest=TestClient(main.app).post('/api/chat',data={'text':text});self.assertIn('เข้าสู่ระบบ',guest.json()['answer'])
            self.assertEqual(len(self.a.get('/api/member/conversations/'+conv).json()['messages']),4)
            gen.assert_not_called();rag.assert_not_called()

    def test_fresh_demo_seed_has_pending_quote_and_is_idempotent(self):
        import seed_demo
        seed_demo.seed()
        with membership.db() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM cases').fetchone()[0],8)
            q=c.execute("SELECT case_quotes.* FROM case_quotes JOIN cases ON cases.id=case_quotes.case_id WHERE cases.status='awaiting_approval'").fetchone()
            self.assertIsNotNone(q);self.assertEqual(q['status'],'pending');self.assertEqual(q['amount'],990)
        seed_demo.seed()
        with membership.db() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM cases').fetchone()[0],8)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM case_quotes').fetchone()[0],1)

if __name__=='__main__':unittest.main()
