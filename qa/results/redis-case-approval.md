# Redis + case chat + quote approval — 10 October 2026

## Completed verification

Command: `docker compose exec -T api python -m unittest test_chat test_ingest test_membership test_redis_integration -v`

Result: **25 tests passed in 3.964 seconds**. 15 offline contract/member tests and 10 tests using the running Redis instance with mocked OpenAI/LightRAG responses. No paid AI request was needed for this run. Test Redis keys have unique `qa:<uuid>:` prefixes and are cleaned without FLUSHDB.

Verified Redis behavior:

- Answer cache avoids provider calls on a matching repeated turn.
- Vision and retrieval caches are reused independently on a miss in the answer cache.
- TTLs: answer 1,800s; retrieval 3,600s; vision and context 86,400s.
- Session isolation; existing lock returns 409 without deleting another request's lock.
- Lock release uses atomic compare-and-delete with a unique owner token, preserving a replacement lock.
- Hourly request limit returns 429.
- Upstream errors return 503 and release owned locks.
- Readiness reports a Redis connection failure rather than claiming dependencies are ready.

`GET /api/ready` returned 200 with `redis=true`, `members=true`, `lightrag=true` on the current local deployment. This checks dependency connectivity, not OpenAI billing or indexed-document completeness.

Verified member workflow:

- Case status is fetched from owned SQLite rows on each recognized case query, even with no OpenAI key; status changes appear on the next request without stale answer-cache hits.
- Another member cannot read the case, act on its quote, or attach its conversation. Guests are asked to sign in.
- Case answers are persisted to the member's text history.
- Repairing a quoted case requires approval for the current exact price.
- New quotes invalidate previous decisions; a stale/repeated decision returns 409.
- Rejection returns the case to checking. Decisions retain actor, time and note in the quote and event audit.

## Actual browser verification

Using the local `demo_user` account:

1. Opened the pending quote for example case PLM-00005, quote #1, 990 THB.
2. Selected approval and submitted a demo note. UI showed approval recorded and waiting for the shop to begin repair.
3. Asked `สถานะเคส PLM-00005` in the embedded chat. It displayed the owned case's newly approved state with a case-system source label.

Screenshots are in the parent workspace `output/`: `plimo-quote-form.png`, `plimo-quote-approved.png`, `plimo-case-chat.png`.

## Scope

All prices remain demonstration data; approval does not charge payment. Case intent detection supports explicit case-status phrases and PLM references; it is deterministic routing, not general LLM tool calling. When a case-status message includes an image, it currently follows the image/RAG path. The full live vision-quality test suite remains pending. The production VPS has not yet been deployed.
