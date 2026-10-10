"""Offline contract tests: no external requests, credentials or API charges."""
import io
import json
import unittest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from PIL import Image
import main

class MemoryRedis:
    def __init__(self): self.values = {}
    async def get(self, key): return self.values.get(key)
    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.values: return False
        self.values[key] = value
        return True
    async def delete(self, key): self.values.pop(key, None)
    async def incr(self, key):
        self.values[key] = int(self.values.get(key, 0)) + 1
        return self.values[key]
    async def expire(self, key, seconds): return True

class ChatTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.no_context = False
        self.transport = httpx.MockTransport(self.upstream)
        original_client = httpx.AsyncClient
        self.patches = [
            patch.object(main, 'OPENAI_KEY', 'offline-test'),
            patch.object(main, 'RAG_KEY', 'offline-test'),
            patch.object(main, 'cache', MemoryRedis()),
            patch.object(main.httpx, 'AsyncClient', lambda **kw: original_client(transport=self.transport, **kw)),
        ]
        for p in self.patches: p.start()
        self.client = TestClient(main.app)
    def tearDown(self):
        self.client.close()
        for p in reversed(self.patches): p.stop()
    def upstream(self, request):
        payload = json.loads(request.content)
        self.calls.append((request.url.path, payload))
        if request.url.path == '/query/data':
            chunks = [] if self.no_context else [{'content':'ร้าน Plimo เปิด 10:00–20:00 ยกเว้นวันพุธ ตรวจเช็คฟรี','reference_id':'1'}]
            return httpx.Response(200, json={'status':'success','data':{'chunks':chunks,'references':[{'file_path':'shop.md','reference_id':'1'}]}})
        if request.url.path == '/v1/responses':
            content=payload['input'][0]['content']
            is_vision=any(c['type']=='input_image' for c in content)
            if not is_vision:
                self.assertIn('ข้อมูลร้านที่ค้นพบ', content[0]['text'])
                self.assertIn('ห้ามแต่งราคา', payload['instructions'])
            return httpx.Response(200,json={'output':[{'content':[{'type':'output_text','text':'เห็นรอยแตกที่หน้าจอ ยังไม่ทราบรุ่น' if is_vision else 'ร้านเปิด 10:00–20:00 ยกเว้นวันพุธครับ'}]}]})
        raise AssertionError('Unexpected upstream URL: '+str(request.url))
    def test_text_retrieves_then_generates_and_repeats_hit_cache(self):
        first=self.client.post('/api/chat', data={'text':'ร้านเปิดกี่โมง'})
        self.assertEqual(first.status_code,200)
        self.assertTrue(first.json()['rag_used'])
        self.assertEqual(first.json()['sources'][0]['label'],'shop.md')
        self.assertEqual([c[0] for c in self.calls],['/query/data','/v1/responses'])
        second=self.client.post('/api/chat',data={'text':'ร้านเปิดกี่โมง'})
        third=self.client.post('/api/chat',data={'text':'ร้านเปิดกี่โมง'})
        self.assertTrue(second.json()['cache']['answer'])
        self.assertTrue(third.json()['cache']['answer'])
        self.assertEqual(len(self.calls),2)
    def test_images_analyzed_before_retrieval_and_session_isolation(self):
        image=io.BytesIO();Image.new('RGB',(120,160),'green').save(image,'PNG')
        files={'images':('phone.png',image.getvalue(),'image/png')}
        result=self.client.post('/api/chat',data={'text':'ช่วยดูภาพ'},files=files)
        self.assertEqual(result.status_code,200)
        self.assertEqual([c[0] for c in self.calls],['/v1/responses','/query/data','/v1/responses'])
        self.assertIn('เห็นรอยแตก',self.calls[1][1]['query'])
        before=len(self.calls)
        self.client.cookies.clear()
        result=self.client.post('/api/chat',data={'text':'ช่วยดูภาพ'},files=files)
        self.assertFalse(result.json()['cache']['answer'])
        self.assertFalse(result.json()['cache']['vision'])
        self.assertEqual(len(self.calls),before+3)
    def test_missing_context_skips_answer_model(self):
        self.no_context=True
        result=self.client.post('/api/chat',data={'text':'มีส่วนลดไหม'})
        self.assertEqual(result.status_code,200)
        self.assertIn('ยังไม่พบข้อมูล',result.json()['answer'])
        self.assertEqual([c[0] for c in self.calls],['/query/data'])
    def test_invalid_image_rejected_before_provider_call(self):
        result=self.client.post('/api/chat',files={'images':('fake.png',b'not an image','image/png')})
        self.assertEqual(result.status_code,415)
        self.assertEqual(self.calls,[])
    def test_no_key_does_not_fake_rag(self):
        with patch.object(main,'OPENAI_KEY',''):
            self.assertEqual(self.client.get('/api/health').json()['mode'],'demo')
            self.assertEqual(self.client.post('/api/chat',data={'text':'ทดสอบ'}).status_code,503)
            self.assertEqual(self.calls,[])

if __name__=='__main__': unittest.main()
