"""Stripe test-mode payments with a mocked Stripe API: no network, no charges."""
import hashlib, hmac, json, os, tempfile, time, unittest
from unittest.mock import patch
from urllib.parse import parse_qs
import httpx
from fastapi.testclient import TestClient
import main, membership, payments
from test_chat import MemoryRedis

SESSION = 'cs_test_' + 'a' * 24

class PaymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.stripe_calls = []
        self.session = {}
        original = httpx.AsyncClient
        self.patches = [patch.object(membership, 'DB_PATH', self.tmp.name + '/pay.sqlite3'),
                        patch.dict(os.environ, {'STRIPE_SECRET_KEY': 'sk_test_offline', 'STRIPE_WEBHOOK_SECRET': 'whsec_offline', 'PUBLIC_BASE_URL': 'https://shop.example',
                                                'ADMIN_USERNAME': 'admin', 'ADMIN_PASSWORD': 'test-admin-password'}),
                        patch.object(main.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(self.stripe), **kw)),
                        patch.object(main.net, '_client', None), patch.object(main, 'cache', MemoryRedis()), patch.object(main, 'OPENAI_KEY', '')]
        for p in self.patches: p.start()
        membership.init_db()
        self.a, self.b, self.ad = TestClient(main.app), TestClient(main.app), TestClient(main.app)
        self.a.post('/api/auth/register', json={'username': 'alice', 'password': 'alice-test-password'})
        self.b.post('/api/auth/register', json={'username': 'bob', 'password': 'bob-test-password'})
        self.ad.post('/api/auth/login', json={'username': 'admin', 'password': 'test-admin-password'})
    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.tmp.cleanup()
    def stripe(self, request):
        self.stripe_calls.append(request)
        if request.method == 'POST':
            form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            self.form = form
            return httpx.Response(200, json={'id': SESSION, 'url': 'https://checkout.stripe.com/c/pay/' + SESSION, 'livemode': self.session.get('livemode', False)})
        return httpx.Response(200, json=self.session)
    def approved_case(self, price=3200, approve=True):
        cid = self.a.post('/api/member/cases', json={'model': 'iPhone 13', 'issue': 'หน้าจอแตกทดสอบ'}).json()['case']['id']
        for status in ['received', 'checking']:
            self.ad.patch(f'/api/admin/cases/{cid}', json={'status': status, 'note': 'ทดสอบขั้นตอน'})
        self.ad.patch(f'/api/admin/cases/{cid}', json={'status': 'awaiting_approval', 'note': 'เสนอราคา', 'quoted_price': price})
        quote = self.a.get(f'/api/member/cases/{cid}').json()['case']['quote']['id']
        if approve:
            self.a.post(f'/api/member/cases/{cid}/quote-decision', json={'quote_id': quote, 'decision': 'approve'})
        return cid, quote
    def paid_session(self, cid, quote, **override):
        s = {'id': SESSION, 'livemode': False, 'status': 'complete', 'payment_status': 'paid', 'amount_total': 320000, 'currency': 'thb',
             'metadata': {'case_id': str(cid), 'quote_id': str(quote), 'user_id': self.a.get('/api/auth/me').json()['user']['id']}}
        s.update(override)
        return s
    def signed(self, event, stamp=None, secret='whsec_offline'):
        body = json.dumps(event).encode(); stamp = str(stamp or int(time.time()))
        sig = hmac.new(secret.encode(), stamp.encode() + b'.' + body, hashlib.sha256).hexdigest()
        return body, {'stripe-signature': f't={stamp},v1={sig}', 'content-type': 'application/json'}

    def test_checkout_uses_server_amount_and_reuses_pending_session(self):
        cid, quote = self.approved_case()
        self.assertTrue(self.a.get('/api/member/cases').json()['cases'][0]['can_pay'])
        r = self.a.post(f'/api/member/cases/{cid}/checkout')
        self.assertEqual(r.status_code, 200); self.assertTrue(r.json()['url'].startswith('https://checkout.stripe.com/'))
        self.assertEqual((self.form['line_items[0][price_data][unit_amount]'], self.form['line_items[0][price_data][currency]']), ('320000', 'thb'))
        self.assertEqual(self.form['metadata[quote_id]'], str(quote))
        self.assertTrue(self.form['success_url'].startswith('https://shop.example/?payment=success'))
        self.assertEqual(self.a.post(f'/api/member/cases/{cid}/checkout').json()['url'], r.json()['url'])
        self.assertEqual(len(self.stripe_calls), 1)
    def test_only_owner_and_only_approved_quote(self):
        cid, _ = self.approved_case(approve=False)
        self.assertEqual(self.a.post(f'/api/member/cases/{cid}/checkout').status_code, 409)
        self.assertEqual(self.b.post(f'/api/member/cases/{cid}/checkout').status_code, 404)
        self.assertEqual(TestClient(main.app).post(f'/api/member/cases/{cid}/checkout').status_code, 401)
        self.assertEqual(self.stripe_calls, [])
    def test_confirm_asks_stripe_and_is_idempotent(self):
        cid, quote = self.approved_case(); self.a.post(f'/api/member/cases/{cid}/checkout')
        self.session = self.paid_session(cid, quote)
        r = self.a.get('/api/member/payments/confirm', params={'session_id': SESSION})
        self.assertEqual(r.json()['status'], 'paid')
        calls = len(self.stripe_calls)
        self.assertEqual(self.a.get('/api/member/payments/confirm', params={'session_id': SESSION}).json()['status'], 'paid')
        self.assertEqual(len(self.stripe_calls), calls)
        case = self.a.get(f'/api/member/cases/{cid}').json()
        self.assertEqual(case['case']['payment']['status'], 'paid'); self.assertFalse(case['case']['can_pay'])
        self.assertIn('ชำระเงินแล้ว', case['events'][-1]['note'])
        self.assertEqual(self.a.post(f'/api/member/cases/{cid}/checkout').status_code, 409)
        # Another member cannot confirm or read this payment.
        self.assertEqual(self.b.get('/api/member/payments/confirm', params={'session_id': SESSION}).status_code, 404)
        self.assertEqual(self.a.get('/api/member/payments/confirm', params={'session_id': 'cs_live_x'}).status_code, 422)
    def test_mismatched_session_is_not_marked_paid(self):
        cid, quote = self.approved_case(); self.a.post(f'/api/member/cases/{cid}/checkout')
        self.session = self.paid_session(cid, quote, amount_total=100)
        self.assertEqual(self.a.get('/api/member/payments/confirm', params={'session_id': SESSION}).json()['status'], 'failed')
    def test_webhook_signature_timestamp_and_duplicates(self):
        cid, quote = self.approved_case(); self.a.post(f'/api/member/cases/{cid}/checkout')
        event = {'id': 'evt_1', 'type': 'checkout.session.completed', 'livemode': False, 'data': {'object': self.paid_session(cid, quote)}}
        body, headers = self.signed(event, secret='whsec_wrong')
        self.assertEqual(self.a.post('/api/stripe/webhook', content=body, headers=headers).status_code, 400)
        body, headers = self.signed(event, stamp=int(time.time()) - 3600)
        self.assertEqual(self.a.post('/api/stripe/webhook', content=body, headers=headers).status_code, 400)
        body, headers = self.signed(event)
        guest = TestClient(main.app)
        self.assertEqual(guest.post('/api/stripe/webhook', content=body, headers=headers).json(), {'received': True})
        self.assertEqual(guest.post('/api/stripe/webhook', content=body, headers=headers).json(), {'duplicate': True})
        self.assertEqual(self.a.get(f'/api/member/cases/{cid}').json()['case']['payment']['status'], 'paid')
    def test_live_keys_and_live_sessions_are_refused(self):
        cid, _ = self.approved_case()
        with patch.dict(os.environ, {'STRIPE_SECRET_KEY': 'sk_live_should_not_work'}):
            self.assertEqual(self.a.post(f'/api/member/cases/{cid}/checkout').status_code, 503)
        self.session = {'livemode': True}
        self.assertEqual(self.a.post(f'/api/member/cases/{cid}/checkout').status_code, 502)
    def test_paid_case_cannot_be_requoted_or_cancelled(self):
        cid, quote = self.approved_case(); self.a.post(f'/api/member/cases/{cid}/checkout')
        self.session = self.paid_session(cid, quote); self.a.get('/api/member/payments/confirm', params={'session_id': SESSION})
        for body in [{'status': 'awaiting_approval', 'note': 'ขอเปลี่ยนราคา', 'quoted_price': 5000}, {'status': 'cancelled', 'note': 'ยกเลิก'}]:
            self.assertEqual(self.ad.patch(f'/api/admin/cases/{cid}', json=body).status_code, 409)
        self.assertEqual(self.ad.patch(f'/api/admin/cases/{cid}', json={'status': 'repairing', 'note': 'เริ่มซ่อม'}).status_code, 200)
    def test_chat_reports_payment_from_database_only(self):
        cid, quote = self.approved_case()
        before = self.a.post('/api/chat', data={'text': f'PLM-{cid:05d} จ่ายเงินแล้วหรือยัง'}).json()['answer']
        self.assertIn('ยังไม่ชำระ', before)
        self.a.post(f'/api/member/cases/{cid}/checkout'); self.session = self.paid_session(cid, quote)
        self.a.get('/api/member/payments/confirm', params={'session_id': SESSION})
        after = self.a.post('/api/chat', data={'text': f'PLM-{cid:05d} จ่ายเงินแล้วหรือยัง'}).json()['answer']
        self.assertIn('ชำระแล้ว 3,200.00 บาท', after)

if __name__ == '__main__':
    unittest.main()
