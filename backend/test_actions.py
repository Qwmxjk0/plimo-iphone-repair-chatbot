"""Chat case actions (proposal -> explicit confirmation) and admin AI, with mocked models."""
import json, os, tempfile, unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
import main, membership, router
from test_chat import MemoryRedis

def route(intent='case', topic='status', models=(), services=(), ref=None, standalone='คำถาม'):
    return {'intent': intent, 'standalone': standalone, 'models': list(models), 'services': list(services), 'case_ref': ref,
            'case_topic': topic, 'extra_question': None, 'needs_clarification': False, 'time_sensitive': False, 'source': 'model'}

class ActionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.routes, self.llm_out = {}, '{}'
        async def fake_route(text, history, active, images):
            return dict(self.routes.get(text) or router.fallback(text)), False
        async def fake_llm(instructions, content, **kw):
            return self.llm_out
        async def fake_retrieve(query, session=None):
            return {'chunks': [{'content': 'ร้านเปิด 10:00–20:00'}], 'sources': []}, False
        async def fake_generate(*a):
            return 'ร้านเปิด 10:00–20:00 น. ครับ'
        self.patches = [patch.object(membership, 'DB_PATH', self.tmp.name + '/a.sqlite3'), patch.object(main, 'cache', MemoryRedis()),
                        patch.object(main, 'OPENAI_KEY', 'test'), patch.object(main, 'RAG_KEY', 'test'),
                        patch.object(main, 'route_message', fake_route), patch.object(main, 'llm', fake_llm),
                        patch.object(main, 'retrieve', fake_retrieve), patch.object(main, 'generate', fake_generate),
                        patch.dict(os.environ, {'ADMIN_USERNAME': 'admin', 'ADMIN_PASSWORD': 'test-admin-password', 'STRIPE_SECRET_KEY': ''})]
        for p in self.patches: p.start()
        membership.init_db()
        self.a, self.b, self.ad = TestClient(main.app), TestClient(main.app), TestClient(main.app)
        self.a.post('/api/auth/register', json={'username': 'alice', 'password': 'alice-test-password'})
        self.b.post('/api/auth/register', json={'username': 'bob', 'password': 'bob-test-password'})
        self.ad.post('/api/auth/login', json={'username': 'admin', 'password': 'test-admin-password'})
        self.conv = None
    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.tmp.cleanup()
    def say(self, text, client=None, conv=True):
        data = {'text': text}
        if conv and self.conv and (client is None or client is self.a):
            data['conversation_id'] = self.conv
        r = (client or self.a).post('/api/chat', data=data)
        self.assertEqual(r.status_code, 200, r.text)
        if client is None or client is self.a:
            self.conv = r.json()['conversation_id'] or self.conv
        return r.json()
    def cases(self, client=None):
        return (client or self.a).get('/api/member/cases').json()['cases']
    def quoted_case(self, price=3200):
        cid = self.a.post('/api/member/cases', json={'model': 'iPhone 13', 'issue': 'หน้าจอแตกทดสอบ'}).json()['case']['id']
        for st in ['received', 'checking']:
            self.ad.patch(f'/api/admin/cases/{cid}', json={'status': st, 'note': 'ขั้นตอน'})
        self.ad.patch(f'/api/admin/cases/{cid}', json={'status': 'awaiting_approval', 'note': 'เสนอราคา', 'quoted_price': price})
        return cid

    def test_open_case_needs_explicit_confirmation(self):
        self.routes['จอ iPhone 13 แตก อยากส่งซ่อม'] = route(topic='open', models=[('13', 'base')], services=['screen'])
        r = self.say('จอ iPhone 13 แตก อยากส่งซ่อม')
        self.assertEqual(r['pending']['label'], 'ส่งเคส iPhone 13'); self.assertEqual(self.cases(), [])
        done = self.say('ยืนยันครับ')
        self.assertEqual(done['route'], 'action'); self.assertIn('PLM-', done['answer'])
        case = self.cases()[0]
        self.assertEqual((case['model'], case['status'], case['conversation_id']), ('iPhone 13', 'submitted', self.conv))
        self.assertIn('จอ iPhone 13 แตก', case['issue'])
        self.assertIsNone(self.say('ยืนยัน').get('pending'))  # nothing pending any more
        self.assertEqual(len(self.cases()), 1)
    def test_open_case_asks_for_missing_model_or_symptom(self):
        self.routes['อยากส่งซ่อม'] = route(topic='open')
        self.assertIn('รุ่น', self.say('อยากส่งซ่อม')['answer'])
        self.routes['iPhone 14'] = route(topic='open', models=[('14', 'base')])
        r = self.say('iPhone 14')
        self.assertIn('อาการ', r['answer']); self.assertNotIn('pending', r)
        self.routes['iPhone 8 จอแตก ส่งซ่อม'] = route(topic='open', models=[('8', 'base')], services=['screen'])
        self.assertIn('11–17', self.say('iPhone 8 จอแตก ส่งซ่อม')['answer'])
    def test_guest_cannot_open_case(self):
        self.routes['จอ iPhone 13 แตก อยากส่งซ่อม'] = route(topic='open', models=[('13', 'base')], services=['screen'])
        r = self.say('จอ iPhone 13 แตก อยากส่งซ่อม', TestClient(main.app))
        self.assertIn('เข้าสู่ระบบ', r['answer']); self.assertNotIn('pending', r)
    def test_decline_or_other_message_drops_the_proposal(self):
        self.routes['จอ iPhone 13 แตก อยากส่งซ่อม'] = route(topic='open', models=[('13', 'base')], services=['screen'])
        self.say('จอ iPhone 13 แตก อยากส่งซ่อม')
        self.assertIn('ยกเลิกรายการ', self.say('ยกเลิก')['answer'])
        self.say('จอ iPhone 13 แตก อยากส่งซ่อม')
        self.routes['ร้านเปิดกี่โมง'] = route(intent='shop_info', standalone='ร้านเปิดกี่โมง')
        self.say('ร้านเปิดกี่โมง')
        self.say('ยืนยัน')
        self.assertEqual(self.cases(), [])
    def test_quote_approval_by_chat_and_stale_quote_refused(self):
        cid = self.quoted_case()
        self.routes['อนุมัติราคาเลย'] = route(topic='approve', ref=cid)
        r = self.say('อนุมัติราคาเลย')
        self.assertIn('3,200.00', r['answer']); self.assertIn('pending', r)
        # The shop revises the price before the member confirms: the old proposal must not apply.
        self.ad.patch(f'/api/admin/cases/{cid}', json={'status': 'awaiting_approval', 'note': 'ราคาใหม่', 'quoted_price': 3900})
        self.assertIn('ไม่สำเร็จ', self.say('ยืนยัน')['answer'])
        self.assertEqual(self.cases()[0]['quote']['status'], 'pending'); self.assertEqual(self.cases()[0]['quote']['amount'], 3900)
        self.say('อนุมัติราคาเลย')
        self.assertIn('บันทึกการอนุมัติ', self.say('ยืนยัน')['answer'])
        self.assertEqual(self.cases()[0]['quote']['status'], 'approved')
    def test_other_members_case_gets_no_proposal(self):
        cid = self.quoted_case()
        self.routes['อนุมัติราคา'] = route(topic='approve', ref=cid)
        r = self.say('อนุมัติราคา', self.b)
        self.assertIn('ไม่พบเคส', r['answer']); self.assertNotIn('pending', r)
        self.say('ยืนยัน', self.b)
        self.assertEqual(self.cases()[0]['quote']['status'], 'pending')
    def test_confirm_word_alone_does_nothing(self):
        cid = self.quoted_case()
        self.say('ยืนยัน')
        self.assertEqual(self.cases()[0]['quote']['status'], 'pending')
    def test_admin_assist_rejects_invalid_suggestions(self):
        cid = self.quoted_case()
        self.llm_out = json.dumps({'summary': 'ลูกค้าจอ iPhone 13 แตก', 'missing_info': ['ทัชยังใช้ได้ไหม'], 'suggested_status': 'closed', 'suggested_price': 500,
                                   'quote_items': [{'name': 'เปลี่ยนหน้าจอ iPhone 13', 'price': 3200}, {'name': 'ส่วนลดพิเศษ', 'price': 100}],
                                   'customer_note': 'ราคาพิเศษ 500 บาทครับ', 'reason': 'ทดสอบ'})
        a = self.ad.post(f'/api/admin/cases/{cid}/assist').json()
        self.assertIsNone(a['suggested_status']); self.assertIsNone(a['suggested_price']); self.assertEqual(a['customer_note'], '')
        self.assertEqual([i['name'] for i in a['quote_items']], ['เปลี่ยนหน้าจอ iPhone 13'])
        self.assertEqual(len(a['warnings']), 4)
        self.assertEqual(self.a.post(f'/api/admin/cases/{cid}/assist').status_code, 403)
    def test_admin_assist_valid_suggestion_passes(self):
        cid = self.a.post('/api/member/cases', json={'model': 'iPhone 13', 'issue': 'หน้าจอแตก'}).json()['case']['id']
        for st in ['received', 'checking']:
            self.ad.patch(f'/api/admin/cases/{cid}', json={'status': st, 'note': 'ขั้นตอน'})
        self.llm_out = json.dumps({'summary': 'จอแตก', 'missing_info': [], 'suggested_status': 'awaiting_approval', 'suggested_price': 3200,
                                   'quote_items': [{'name': 'เปลี่ยนหน้าจอ iPhone 13', 'price': 3200}], 'customer_note': 'ราคาประเมิน 3,200 บาทครับ', 'reason': 'ตรวจแล้ว'})
        a = self.ad.post(f'/api/admin/cases/{cid}/assist').json()
        self.assertEqual((a['suggested_status'], a['suggested_price'], a['warnings']), ('awaiting_approval', 3200, []))
    def test_insights_log_has_no_raw_personal_text(self):
        self.routes['ผมชื่อสมชาย 0812345678 จอ iPhone 13 เท่าไหร่'] = route(intent='price', standalone='เปลี่ยนหน้าจอ iPhone 13 ราคาเท่าไหร่', models=[('13', 'base')], services=['screen'])
        self.say('ผมชื่อสมชาย 0812345678 จอ iPhone 13 เท่าไหร่', TestClient(main.app))
        self.say('จ่ายด้วยบัตร 4242 4242 4242 4242', TestClient(main.app))
        log = json.dumps(main.cache.lists, ensure_ascii=False)
        self.assertIn('เปลี่ยนหน้าจอ iPhone 13', log)
        for secret in ['สมชาย', '0812345678', '4242']:
            self.assertNotIn(secret, log)
        d = self.ad.get('/api/admin/insights').json()
        self.assertEqual(d['total'], 2); self.assertEqual(d['top_questions'][0]['q'], 'เปลี่ยนหน้าจอ iPhone 13 ราคาเท่าไหร่')
        self.assertEqual(self.a.get('/api/admin/insights').status_code, 403)

if __name__ == '__main__':
    unittest.main()
