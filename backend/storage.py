"""Chat image storage: a private Cloudflare R2 bucket when configured, otherwise the server disk.

Only cleaned JPEGs (re-encoded, EXIF/GPS removed) are stored. Nothing is public: images
are read back through the API, which checks who is asking.
"""
import asyncio
import os
from pathlib import Path

LOCAL_DIR = Path(os.getenv('IMAGE_DIR', '/app/data/images'))
_client = None

def r2_settings():
    keys = ('R2_ACCOUNT_ID', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY')
    values = [os.getenv(k, '') for k in keys]
    return values if all(values) else None

def backend():
    return 'r2' if r2_settings() else 'local'

def bucket():
    return os.getenv('R2_BUCKET', 'plimo-chat-images')

def client():
    global _client
    if _client is None:
        import boto3
        from botocore.config import Config
        account, key, secret = r2_settings()
        _client = boto3.client('s3', endpoint_url=f'https://{account}.r2.cloudflarestorage.com', aws_access_key_id=key,
                               aws_secret_access_key=secret, region_name='auto',
                               config=Config(signature_version='s3v4', retries={'max_attempts': 3}, connect_timeout=5, read_timeout=20))
    return _client

def _local(key):
    path = (LOCAL_DIR / key).resolve()
    if LOCAL_DIR.resolve() not in path.parents:
        raise ValueError('bad image key')
    return path

def _put(where, key, data):
    if where == 'r2':
        client().put_object(Bucket=bucket(), Key=key, Body=data, ContentType='image/jpeg')
    else:
        path = _local(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

def _get(where, key):
    if where == 'r2':
        try:
            return client().get_object(Bucket=bucket(), Key=key)['Body'].read()
        except client().exceptions.NoSuchKey:
            return None
    path = _local(key)
    return path.read_bytes() if path.exists() else None

async def put(key, data):
    """Store and return the backend used, so reads go to the same place after a switch."""
    where = backend()
    await asyncio.to_thread(_put, where, key, data)
    return where

async def get(where, key):
    return await asyncio.to_thread(_get, where, key)
