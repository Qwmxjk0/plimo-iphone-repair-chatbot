"""Image guardrails and private image storage, with mocked OpenAI/LightRAG and a temp DB/disk."""
import io, os, tempfile, unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from PIL import Image
import main, membership, storage
from test_chat import ChatSetup, photo

def upload(data, name='phone.png', ctype='image/png'):
    return {'images': (name, data, ctype)}

class ImageTests(ChatSetup, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.more = [patch.object(membership, 'DB_PATH', self.tmp.name + '/i.sqlite3'), patch.object(storage, 'LOCAL_DIR', storage.Path(self.tmp.name) / 'images'),
                     patch.dict(os.environ, {'ADMIN_USERNAME': 'admin', 'ADMIN_PASSWORD': 'test-admin-password', 'R2_ACCOUNT_ID': ''})]
        for p in self.more: p.start()
        membership.init_db()
        self.a, self.b, self.ad = TestClient(main.app), TestClient(main.app), TestClient(main.app)
        self.a.post('/api/auth/register', json={'username': 'alice', 'password': 'alice-test-password'})
        self.b.post('/api/auth/register', json={'username': 'bob', 'password': 'bob-test-password'})
        self.ad.post('/api/auth/login', json={'username': 'admin', 'password': 'test-admin-password'})
    def tearDown(self):
        for p in reversed(self.more): p.stop()
        self.tmp.cleanup(); super().tearDown()
    def send(self, client, text, files):
        r = client.post('/api/chat', data={'text': text}, files=files)
        self.assertEqual(r.status_code, 200, r.text); return r.json()
    def stored(self):
        with membership.db() as c: return [dict(r) for r in c.execute('SELECT * FROM chat_images')]

    def test_heic_from_iphone_is_converted(self):
        import pillow_heif
        image = Image.open(io.BytesIO(photo())); out = io.BytesIO()
        pillow_heif.from_pillow(image).save(out, format='HEIF')
        r = self.send(self.client, 'ช่วยดูภาพ', upload(out.getvalue(), 'IMG_0001.HEIC', 'image/heic'))
        self.assertEqual(r['route'], 'shop_info')
        vision = [c[1] for c in self.calls if c[0] == 'vision'][0]
        self.assertTrue(vision['input'][0]['content'][1]['image_url'].startswith('data:image/jpeg;base64,'))
    def test_dark_blank_or_tiny_images_get_retake_without_model_calls(self):
        for data in [photo() and self._solid((0, 0, 0)), self._solid((240, 240, 240)), photo(size=(40, 40))]:
            r = self.send(self.client, 'ดูให้หน่อย', upload(data))
            self.assertEqual(r['route'], 'image_check'); self.assertIn('ถ่ายใหม่', r['answer'])
        self.assertEqual(self.calls, [])
    def _solid(self, colour):
        out = io.BytesIO(); Image.new('RGB', (200, 200), colour).save(out, 'PNG'); return out.getvalue()
    def test_moderated_image_is_refused_and_not_stored(self):
        self.flagged = True
        r = self.send(self.a, 'ดูให้หน่อย', upload(photo()))
        self.assertIn('ไม่เหมาะสม', r['answer']); self.assertEqual(self.kinds('vision'), 0); self.assertEqual(self.stored(), [])
    def test_card_number_read_from_image_is_never_stored_or_repeated(self):
        self.vision = {'relevance': 'device_or_screen', 'quality': 'ok', 'observation': 'เห็นบัตร VISA เลข 4242 4242 4242 4242'}
        r = self.send(self.a, 'ดูให้หน่อย', upload(photo()))
        self.assertIn('ข้อมูลบัตร', r['answer']); self.assertNotIn('4242', r['answer'])
        self.assertEqual(self.stored(), []); self.assertEqual(self.kinds('answer'), 0)
        self.assertNotIn('4242 4242', str(main.cache.values))
    def test_slip_is_kept_as_evidence_with_access_control(self):
        self.vision = {'relevance': 'receipt_or_slip', 'quality': 'ok', 'observation': 'สลิปโอนเงิน 3,200 บาท'}
        r = self.send(self.a, 'โอนแล้วนะครับ', upload(photo()))
        self.assertIn('หลักฐาน', r['answer']); self.assertNotIn('ได้รับเงินแล้ว', r['answer'])
        image_id = r['image_ids'][0]; row = self.stored()[0]
        self.assertEqual((row['kind'], row['storage']), ('receipt_or_slip', 'local'))
        conv = self.a.get('/api/member/conversations/' + r['conversation_id']).json()['messages']
        self.assertEqual(conv[0]['image_ids'], [image_id])
        got = self.a.get('/api/images/' + image_id)
        self.assertEqual((got.status_code, got.headers['content-type']), (200, 'image/jpeg'))
        self.assertEqual(self.b.get('/api/images/' + image_id).status_code, 404)
        self.assertEqual(TestClient(main.app).get('/api/images/' + image_id).status_code, 401)
        self.assertEqual(self.ad.get('/api/images/' + image_id).status_code, 404)  # not attached to a case yet
        cid = self.a.post('/api/member/cases', json={'model': 'iPhone 13', 'issue': 'ส่งสลิปค่าซ่อม', 'conversation_id': r['conversation_id']}).json()['case']['id']
        self.assertEqual(self.ad.get('/api/images/' + image_id).status_code, 200)
        self.assertEqual(self.ad.get(f'/api/admin/cases/{cid}').json()['images'][0]['kind'], 'receipt_or_slip')
    def test_unrelated_image_does_not_get_an_answer_about_it(self):
        self.vision = {'relevance': 'person_or_unrelated', 'quality': 'ok', 'observation': 'รูปแมวสีส้ม'}
        r = self.send(self.a, 'นี่คืออะไร', upload(photo()))
        self.assertIn('ไม่เกี่ยวกับตัวเครื่อง', r['answer']); self.assertEqual(self.kinds('answer'), 0); self.assertEqual(self.stored(), [])
    def test_guest_images_are_not_stored(self):
        self.send(self.client, 'ช่วยดูภาพ', upload(photo()))
        self.assertEqual(self.stored(), [])
    def test_r2_backend_used_when_configured(self):
        saved = {}
        class FakeS3:
            def put_object(self, **kw): saved[kw['Key']] = kw['Body']
            def get_object(self, Bucket, Key): return {'Body': io.BytesIO(saved[Key])}
        with patch.dict(os.environ, {'R2_ACCOUNT_ID': 'acc', 'R2_ACCESS_KEY_ID': 'k', 'R2_SECRET_ACCESS_KEY': 's'}), patch.object(storage, 'client', lambda: FakeS3()):
            r = self.send(self.a, 'ช่วยดูภาพหน้าจอ', upload(photo()))
            self.assertEqual(self.stored()[0]['storage'], 'r2'); self.assertEqual(len(saved), 1)
            self.assertEqual(self.a.get('/api/images/' + r['image_ids'][0]).status_code, 200)
    def test_storage_keys_cannot_escape_the_image_folder(self):
        with self.assertRaises(ValueError):
            storage._local('../../etc/passwd')

if __name__ == '__main__':
    unittest.main()
