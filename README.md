# Plimo storefront + embedded chatbot

A single storefront with a floating chat panel. `chat.html` is an internal embedded widget, not a separate customer navigation page. Thai UI, 16 catalog slots, search/type filters, item details, shop hours, image previews, remove attachments, paste/drop, and responsive chat. Catalog now has 16 explicitly labeled demo items with illustrative prices, not confirmed shop offers.

## Preview without API keys

Run `docker compose up --build -d` and open http://localhost:8081. The frontend and FastAPI run with Redis. With no keys, the chat explicitly uses demo replies; it does not upload images or claim to analyze them. The hosted Sites preview is also this static demonstration. Docker backend is not deployed to Sites.

## Enable OpenAI + LightRAG

1. Copy `.env.example` to `.env`. Enter `OPENAI_API_KEY` and a separately generated `LIGHTRAG_API_KEY` on your machine. Never put keys in browser JS or commit `.env`.
2. Run `docker compose --profile rag up --build -d`.
3. Run `docker compose exec api python ingest.py`. This submits approved knowledge asynchronously; inspect document processing status before testing. For a local admin view, use a temporary loopback port mapping to LightRAG and authenticate with your LightRAG key. Do not expose its admin API publicly.
4. Open http://localhost:8081. The chat switches to live mode when the keys are configured. A misconfigured/unavailable upstream produces an error, never a fabricated live answer.

Images go to OpenAI's Responses API for observation, then observations and the question are used to retrieve source chunks through LightRAG `/query/data`. Only those chunks support the final Thai answer. Responses include retrieved sources, timings and cache-hit flags. No raw image is stored server-side. Sessions and observations expire in Redis after 24 hours; answer cache after 30 minutes; retrieval cache after one hour. Cached data is scoped by session and version. These are prototype prompt protections, not a guarantee against all prompt injection.

Use JPEG, PNG or WebP, up to 3 images/10 MB each. Server checks decoding, pixel limits, re-encodes without EXIF and reduces size. HEIC must be converted before attaching in this version.

## Real catalog data

Edit `dist/catalog.json`: keep a stable `id`, set `name`, `kind` (`service` or `product`), `description`, `price` (number in THB or null), `models`, `terms`, and `confirmed: true` only after shop approval. Only confirmed items enter RAG by default. Use ingest.py --include-demo to index labeled examples in the separate demo workspace. `knowledge/shop.md` contains the actual facts supplied by the user. The 16 demo records have confirmed=false and demo=true; do not present them as actual shop services.

When changing knowledge, update `KB_VERSION` and use a fresh named LightRAG workspace/volume (preserve the old volume), then ingest again; changing a cache version alone does not delete obsolete source documents from LightRAG. Rebuild API and web after catalog edits. Pin `LIGHTRAG_IMAGE` to a tested release/digest after the first live integration; current default follows the official latest image and its contract may change.

For production Docker hosting, place an HTTPS reverse proxy in front of the loopback web port and set `COOKIE_SECURE=true`. Redis and LightRAG remain internal. API requests are limited at nginx and Redis; a per-session lock prevents overlapping chat turns. The hosted static demo does not connect to your localhost backend.

Live OpenAI requests and LightRAG indexing require a valid key and API billing. No paid live requests were made during prototype development.
# ภาพประกอบและหลักฐานทดสอบ

การ์ด 16 ช่องใช้ภาพการ์ตูนใหม่ 3 แบบจาก built-in ImageGen ใน `dist/assets/` เป็นภาพประกอบทั่วไป รายการและราคาเป็นสาธิต เข้า RAG ได้ด้วย --include-demo และต้องคงป้ายสาธิต ดู prompt ที่ `qa/art-prompts.md`

ชุดทดสอบ 10 คำถาม + 5 ภาพ + 5 ความปลอดภัย: `qa/test-plan.md`; ผลจริงที่เก็บ: `qa/results/live-results.json`; สถานะ stack: `qa/stack-audit.md`; แผนภาพ PNG/SVG: `qa/diagrams/stack-flow.*`


## Demo price catalog

See qa/demo-catalog.md. The current Compose uses a fresh rag-data-demo-v2 volume and KB_VERSION=plimo-demo-v2. Previous volumes are preserved. Index with docker compose exec api python ingest.py --include-demo, then wait for document processing. Never relabel examples as confirmed shop prices.
