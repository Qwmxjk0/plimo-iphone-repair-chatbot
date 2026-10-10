"""Real Redis integration, mocked AI providers, unique keys and no API charges."""
import io, os, uuid, unittest
from unittest.mock import patch
from redis import Redis as SyncRedis
from redis.asyncio import Redis
from PIL import Image
import test_chat
import main

class ScopedRedis:
    def __init__(self, url, prefix):
        self.redis=Redis.from_url(url,decode_responses=True)
        self.prefix=prefix
    @property
    def values(self):
        sync=SyncRedis.from_url(os.getenv('REDIS_URL','redis://redis:6379/0'),decode_responses=True)
        try:return {k[len(self.prefix):]:sync.get(k) for k in sync.scan_iter(self.prefix+'*')}
        finally:sync.close()
    async def get(self,k):return await self.redis.get(self.prefix+k)
    async def set(self,k,v,**kw):return await self.redis.set(self.prefix+k,v,**kw)
    async def delete(self,k):return await self.redis.delete(self.prefix+k)
    async def incr(self,k):return await self.redis.incr(self.prefix+k)
    async def expire(self,k,t):return await self.redis.expire(self.prefix+k,t)
    async def eval(self,script,n,k,token):return await self.redis.eval(script,n,self.prefix+k,token)
    async def ping(self):return await self.redis.ping()

class RedisIntegration(test_chat.ChatTests):
    # Reuse provider contract tests with real Redis instead of MemoryRedis.
    def setUp(self):
        super().setUp()
        url=os.getenv('REDIS_URL','redis://redis:6379/0')
        self.prefix='qa:'+uuid.uuid4().hex+':'
        self.sync=SyncRedis.from_url(url,decode_responses=True)
        self.sync.ping()
        self.scoped=ScopedRedis(url,self.prefix)
        self.redis_patch=patch.object(main,'cache',self.scoped);self.redis_patch.start()
        self.client.__enter__()
    def tearDown(self):
        self.client.portal.call(self.scoped.redis.aclose)
        self.client.__exit__(None,None,None)
        keys=list(self.sync.scan_iter(self.prefix+'*'))
        if keys:self.sync.delete(*keys)
        self.sync.close();self.redis_patch.stop();super().tearDown()
    def keys(self,kind):return list(self.sync.scan_iter(self.prefix+kind+':*'))
    def test_all_cache_layers_ttls_and_locks(self):
        im=io.BytesIO();Image.new('RGB',(60,80),'green').save(im,'PNG')
        files={'images':('test.png',im.getvalue(),'image/png')}
        self.assertEqual(self.client.post('/api/chat',data={'text':'ช่วยดูภาพ'},files=files).status_code,200)
        self.assertEqual(len(self.calls),3)
        for kind,ttl in [('answer',1800),('retrieve',3600),('vision',86400),('history',86400)]:
            keys=self.keys(kind);self.assertEqual(len(keys),1)
            self.assertTrue(ttl-30<=self.sync.ttl(keys[0])<=ttl,(kind,self.sync.ttl(keys[0])))
        self.assertFalse(self.keys('lock'))
        repeat=self.client.post('/api/chat',data={'text':'ช่วยดูภาพ'},files=files)
        self.assertTrue(repeat.json()['cache']['answer']);self.assertEqual(len(self.calls),3)
        # Same observation + query, but remove only this test's answer/history.
        self.sync.delete(*(self.keys('answer')+self.keys('history')))
        r=self.client.post('/api/chat',data={'text':'ช่วยดูภาพ'},files=files)
        self.assertTrue(r.json()['cache']['vision']);self.assertTrue(r.json()['cache']['retrieval'])
        self.assertEqual(len(self.calls),4)
    def test_rate_limit_and_existing_lock(self):
        self.client.post('/api/chat',data={'text':'ร้านเปิดกี่โมง'})
        session=self.client.cookies.get('plimo_session')
        lock=self.prefix+'lock:'+session
        self.sync.set(lock,'another-request',ex=60)
        self.assertEqual(self.client.post('/api/chat',data={'text':'ร้านเปิดกี่โมง'}).status_code,409)
        self.assertEqual(self.sync.get(lock),'another-request')
        self.sync.delete(lock)
        self.sync.set(self.keys('rate')[0],60,ex=3600)
        self.assertEqual(self.client.post('/api/chat',data={'text':'ร้านเปิดกี่โมง'}).status_code,429)
    def test_lock_release_does_not_delete_replacement(self):
        original=self.upstream
        def replace(request):
            if request.url.path=='/v1/responses':
                for key in self.keys('lock'):self.sync.set(key,'replacement-owner',ex=60)
            return original(request)
        self.transport.handler=replace
        r=self.client.post('/api/chat',data={'text':'ร้านเปิดกี่โมง'})
        self.assertEqual(r.status_code,200)
        self.assertEqual(self.sync.get(self.keys('lock')[0]),'replacement-owner')

if __name__=='__main__':unittest.main()
