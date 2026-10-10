# Plimo test suite

The 20 cases in `cases.json` cover 10 questions, 5 images and 5 safety cases. The image fixtures are synthetic test illustrations and mock screenshots; they do not represent a real customer's device or real payment. Never use them as shop knowledge or as evidence that real defect diagnosis is accurate.

Run: `python3 qa/run_live.py`. Without configured OpenAI and LightRAG, all cases are recorded as **blocked**, with null actual answers and times. A static Sites demo is not a live backend target. After setting keys, starting the RAG profile and finishing ingestion, run against http://127.0.0.1:8081. This invokes paid OpenAI API calls. `--case Q01` runs one case first. Output includes actual response, HTTP status, measured elapsed time, backend stage timings, source references, cache flags, and manual pass/fail fields.

HTTP 200 does not prove correctness. Successful cases get **needs_review**. A human checks the expected behavior, fills `passed: true/false`, `reviewer`, and a note. Keyword checks only assist review; they do not establish hallucination or safety performance. No generated expected answer is substituted for the observed answer.

Extra stack checks:

| ID | Test | Pass condition |
|---|---|---|
| E01 | Health/readiness | Redis reachable, LightRAG reachable, configured keys and completed knowledge ingestion; health reports live readiness |
| E02 | Grounding | At least one retrieved source supports each business claim; absent facts yield an explicit unknown |
| E03 | Repeated question | Same text/images/context in the same session produces `cache.answer=true`; no second upstream call in the offline contract test |
| E04 | Session isolation | Different session never sees another session's history or image observations |
| E05 | Image validation | Fake image rejected with 415; >10 MB with 413; >3 images with 422 before provider call |
| E06 | Upstream failure | API returns a useful error; frontend restores text/images for retry; no fake live answer |
| E07 | Knowledge update | New `KB_VERSION` invalidates cache; old index is not queried after switching to a fresh workspace |
| E08 | New conversation | History cleared and cookie reset; next answer does not use previous model/defect context |
| E09 | Thai/model distinction | 13 Pro and 13 Pro Max remain distinct; aliases do not change model or price |
| E10 | UI and deployment boundary | Single storefront, attached-image previews, mobile chat, source label; hosted demo does not claim Docker backend is deployed |

Run offline contracts: `docker compose exec -T api python -m unittest test_chat -v`. They mock OpenAI, LightRAG and Redis, so they validate application behavior, not provider quality or deployed Redis persistence. The smoke audit separately checks actual Docker containers and Redis.

Suggested performance report: measure uncached and cached requests separately using the same case/session. Record total/vision/retrieval/generation ms and cache flags. Set a latency target only after a first live measurement; do not promise a fixed response time from offline tests.
