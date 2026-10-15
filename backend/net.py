"""One keep-alive HTTP client for OpenAI, LightRAG and Stripe: no TLS setup per request."""
import httpx

_client = None

def client():
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(90, connect=10), limits=httpx.Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=60))
    return _client

async def close():
    if _client is not None:
        await _client.aclose()
