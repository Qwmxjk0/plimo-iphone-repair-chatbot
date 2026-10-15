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
        try:return {k[len(self.prefix):]:sync.get(k) for k in sync.scan_iter(self.prefix+'*') if sync.type(k)=='string'}
        finally:sync.close()
    async def get(self,k):return await self.redis.get(self.prefix+k)
    async def set(self,k,v,**kw):return await self.redis.set(self.prefix+k,v,**kw)
    async def delete(self,k):return await self.redis.delete(self.prefix+k)
    async def incr(self,k):return await self.redis.incr(self.prefix+k)
    async def expire(self,k,t):return await self.redis.expire(self.prefix+k,t)
    async def eval(self,script,n,k,token):return await self.redis.eval(script,n,self.prefix+k,token)
    async def ping(self):return await self.redis.ping()
    async def hincrby(self,k,f,n):return await self.redis.hincrby(self.prefix+k,f,n)
    async def hget(self,k,f):return await self.redis.hget(self.prefix+k,f)
    async def hgetall(self,k):return await self.redis.hgetall(self.prefix+k)
    async def rpush(self,k,v):return await self.redis.rpush(self.prefix+k,v)
    async def ltrim(self,k,a,b):return await self.redis.ltrim(self.prefix+k,a,b)
    async def lrange(self,k,a,b):return await self.redis.lrange(self.prefix+k,a,b)

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
        self.assertEqual(self.kinds(),['router','vision','retrieve','answer'])
        for kind,ttl in [('answer',1800),('retrieve',43200),('vision',86400),('history',86400),('router',43200)]:
            keys=self.keys(kind);self.assertEqual(len(keys),1,kind)
            self.assertTrue(ttl-30<=self.sync.ttl(keys[0])<=ttl,(kind,self.sync.ttl(keys[0])))
        self.assertFalse(self.keys('lock'));self.assertFalse(self.keys('inflight'))
        self.assertGreater(int(self.sync.hget(self.keys('metrics')[0],'tokens_total')),0)
        repeat=self.client.post('/api/chat',data={'text':'ช่วยดูภาพ'},files=files).json()
        # New context means a new routing decision; the image observation and answer are reused.
        self.assertTrue(repeat['cache']['answer']);self.assertTrue(repeat['cache']['vision'])
        self.assertEqual(self.kinds()[4:],['router'])
        self.sync.delete(*(self.keys('answer')+self.keys('history')))
        r=self.client.post('/api/chat',data={'text':'ช่วยดูภาพ'},files=files).json()
        self.assertTrue(r['cache']['router']);self.assertTrue(r['cache']['vision']);self.assertTrue(r['cache']['retrieval'])
        self.assertEqual(self.kinds()[5:],['answer'])
    def test_rate_limit_and_existing_lock(self):
        self.client.post('/api/chat',data={'text':'ร้านเปิดกี่โมง'})
        session=self.client.cookies.get('plimo_session')
        lock=self.prefix+'lock:'+session
        self.sync.set(lock,'another-request',ex=60)
        self.assertEqual(self.client.post('/api/chat',data={'text':'ร้านเปิดกี่โมง'}).status_code,409)
        self.assertEqual(self.sync.get(lock),'another-request')
        self.sync.delete(lock)
        for key in self.keys('rate'):self.sync.set(key,10**6,ex=3600)
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
