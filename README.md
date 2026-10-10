# Plimo — เว็บร้านซ่อม iPhone และ Chatbot RAG

เว็บร้านหน้าเดียวที่เน้น Chatbot ภาษาไทย รองรับข้อความและภาพ พร้อมระบบสมาชิก ประวัติแชท และเคสซ่อมที่อ้างอิงบทสนทนา มีหน้า Admin สำหรับติดตามและอัปเดตงานซ่อม

> สำหรับการตรวจงาน: ใช้ **http://127.0.0.1:8081/** เพื่อทดสอบระบบเต็มบน Docker local ส่วนเว็บ `chatgpt.site` เป็น static preview และไม่ได้ deploy ระบบสมาชิกหรือ RAG backend ไว้ที่นั่น รายการสินค้า/บริการและราคา 16 รายการเป็นข้อมูลสาธิต ไม่ใช่ราคาที่ร้านยืนยัน

## เริ่มทดสอบสำหรับอาจารย์

เครื่องต้องมี Docker และ Docker Compose หากทดสอบ RAG จริง ต้องตั้งค่า OpenAI API key พร้อมสิทธิ์ใช้งาน API ใน `.env` ฝั่งเซิร์ฟเวอร์ก่อน ไม่ใส่ key ในหน้าเว็บหรือ README

1. สำหรับการติดตั้งครั้งแรกเท่านั้น คัดลอก `.env.example` เป็น `.env` และตั้งค่า `OPENAI_API_KEY` และ `LIGHTRAG_API_KEY` ถ้ามี `.env` แล้ว ให้ใช้ไฟล์เดิม
2. รันบริการทั้งหมด:

   ```sh
   docker compose --profile rag up --build -d
   ```

3. สำหรับ workspace ใหม่ ให้สร้างคลังข้อมูลสาธิตแล้วรอ LightRAG ประมวลผลเอกสารเสร็จก่อนทดสอบ:

   ```sh
   docker compose exec api python ingest.py --include-demo
   ```

   ถ้าคลังเดิมประมวลผลเสร็จแล้ว ไม่ต้อง ingest ซ้ำเพื่อทดสอบแต่ละครั้ง
4. สร้างบัญชีและข้อมูลตัวอย่าง:

   ```sh
   docker compose exec api python seed_demo.py
   ```

   คำสั่งนี้เรียกซ้ำได้โดยไม่สร้างข้อมูลตัวอย่างซ้ำหรือรีเซ็ตสถานะเดิม
5. เปิด http://127.0.0.1:8081/ และเข้าสู่ระบบด้วยบัญชีด้านล่าง

| บทบาท | Username | Password |
|---|---|---|
| สมาชิกตัวอย่าง | `demo_user` | `PlimoMemberDemo2026!` |
| ผู้ดูแลตัวอย่าง | `demo_admin` | `PlimoAdminDemo2026!` |

บัญชีนี้จัดไว้สำหรับ local demo ตามโจทย์ มีประวัติแชทตัวอย่าง 3 บทสนทนา และเคสตัวอย่าง 8 เคส ข้อความที่ seed มีป้ายข้อมูลตัวอย่าง ไม่ใช่หลักฐานว่าผ่านการตอบจาก GPT จริง สถานะเคสอาจเปลี่ยนจากการทดสอบครั้งก่อน

## ฟีเจอร์ที่มีและขั้นตอนตรวจรับ

ตารางนี้เป็นพฤติกรรมที่พัฒนาแล้ว ผลทดสอบและขอบเขตการตรวจจริงอยู่ในหัวข้อถัดไป ไม่ได้หมายความว่าทุกกรณีผ่านการทดสอบ AI จริงครบแล้ว

| ID | Feature | วิธีทดสอบ | ผลที่คาดหวัง |
|---|---|---|---|
| F01 | เว็บร้านหน้าเดียวและแค็ตตาล็อก | เปิดเว็บ เลื่อนไปสินค้า/บริการ | มี 16 รายการพร้อมภาพ ราคา และป้ายข้อมูลสาธิต |
| F02 | ค้นหาและกรองรายการ | ค้น `แบตเตอรี่` เลือกบริการ/สินค้า และเปิดรายละเอียด | แสดงเฉพาะรายการที่ตรงคำค้น/ประเภท รายละเอียดและราคาตรงรายการ |
| F03 | Chatbot ภาษาไทยด้วย RAG + OpenAI | เมื่อ live backend พร้อม ถาม `เปลี่ยนจอ iPhone 13 เท่าไร` | ตอบจากคลังข้อมูลว่าเป็นราคาสาธิตเริ่มต้น 3,200 บาท พร้อมแหล่งข้อมูล |
| F04 | ขอบเขตข้อมูลและรุ่น | ถาม `iPhone 13 Pro Max ใช้ราคาเดียวกับ iPhone 13 ได้ไหม` | ไม่ใช้ราคาของรุ่นปกติแทน Pro Max และแจ้งว่าราคาเฉพาะรุ่นยังไม่มีข้อมูล |
| F05 | แนบภาพและข้อความ | แนบ JPEG/PNG/WebP พร้อมถามอาการ ลองลบภาพก่อนส่ง | มีภาพ preview และลบได้ เมื่อ live backend พร้อม ระบบส่งภาพให้ OpenAI วิเคราะห์ก่อนค้น RAG; คุณภาพคำตอบต้องตรวจด้วยคน |
| F06 | Cache ลดคำขอซ้ำ | รัน `python qa/run_price_smoke.py` กับ local backend ที่พร้อม | ดูผลเวลาและ cache flag ในไฟล์ผลลัพธ์ คำขอซ้ำที่เข้าเงื่อนไขใช้ answer cache; คำถามซ้ำไม่ได้แคชเสมอเมื่อบริบทเปลี่ยน |
| F07 | สมัคร/เข้าสู่ระบบ/ออกจากระบบ | สมัครบัญชีใหม่ แล้วออกและเข้าใหม่ | บัญชีใหม่เป็น user และเข้าใช้งานข้อมูลของตัวเองได้ |
| F08 | ประวัติแชทของสมาชิก | เข้าด้วย `demo_user` → บัญชี → ประวัติแชท → เปิดบทสนทนา | เห็น 3 บทสนทนาตัวอย่าง เปิดข้อความเก่าในช่องแชทและคุยต่อได้ แชทที่สำเร็จหลัง login เก็บในบัญชี |
| F09 | ส่งเคสอ้างอิงบทสนทนา | เลือกประวัติ → ใช้บทสนทนานี้ส่งเคส หรือกดส่งเคสซ่อมในแชท แล้วกรอกอาการ | ได้เลข `PLM-xxxxx` พร้อมรุ่น/อาการและการเชื่อมบทสนทนา เป็นเคสในระบบสาธิต ไม่ใช่ยืนยันจองจริง |
| F10 | สมาชิกติดตามเคส | เปิดงานซ่อมของฉัน → ประวัติสถานะ | เห็นสถานะ ราคาเสนอเมื่อมี และ timeline ที่เปิด–พับได้ |
| F11 | Admin จัดการเคส | เข้าด้วย `demo_admin` เปิด `/admin.html` เลือกเคส เปลี่ยนสถานะตามขั้นตอนและกรอกหมายเหตุ | จำนวนเคส/สถานะอัปเดต เปิดแชทที่แนบได้ และบันทึกเหตุการณ์การเปลี่ยนสถานะ |
| F12 | แยกสิทธิ์สมาชิก/Admin | ใช้บัญชี user เปิด Admin และเทียบประวัติระหว่างสองสมาชิก | API ปฏิเสธสิทธิ์ Admin ของ user สมาชิกแต่ละคนเห็นเฉพาะข้อมูลของตน |
| F13 | ข้อมูลถาวร | บันทึกแชทหรือเคสแล้วรัน `docker compose restart api` จากนั้นเข้าใหม่ | ข้อมูลยังอยู่ใน SQLite volume `member-data` การหมดอายุแคชไม่ลบประวัติถาวร |
| F14 | Layout เดสก์ท็อป/มือถือ | เปิดหน้าบัญชีและแชทบนจอแคบ | การ์ดเคสเปลี่ยนเป็นหนึ่งคอลัมน์ เมนูและฟอร์มใช้งานได้ ไม่มีข้อความล้นแนวนอน |
| F15 | ถามสถานะเคสผ่านแชท | Login แล้วถาม `เคสของฉันถึงไหนแล้ว` หรือ `สถานะเคส PLM-00005` | อ่านเคสของสมาชิกจาก SQLite สดทุกครั้ง ไม่ใช้แคชคำตอบหรือ GPT เดาสถานะ บันทึกข้อความในประวัติสมาชิก |
| F16 | ลูกค้าอนุมัติ/ปฏิเสธราคา | Admin ส่งราคาในสถานะรออนุมัติ สมาชิกเลือกคำตอบแล้วกดยืนยัน | อนุมัติแล้ว Admin เริ่มซ่อมตามราคานั้นได้ ปฏิเสธแล้วกลับตรวจเช็ค ราคาใหม่ต้องอนุมัติใหม่ เก็บผู้ตัดสินใจและเวลา |

การทดสอบ F06 และการถาม live AI มีการเรียก OpenAI API และใช้โควตาของ key ที่ตั้งไว้ ไฟล์ภาพรองรับสูงสุด 3 ภาพ ขนาดไม่เกิน 10 MB ต่อภาพ ไม่รองรับ HEIC

## ลำดับสาธิตแนะนำ

1. ดูรายการ/ราคา → ถามราคา iPhone 13 → ถามราคา Pro Max เพื่อแสดงขอบเขตข้อมูล
2. Login สมาชิก → เปิดประวัติเดิม → เลือกบทสนทนาส่งเคส → ดูเลขและสถานะเคส
3. Logout → Login Admin → อ่านแชทที่แนบ → อัปเดตเคสพร้อมหมายเหตุ
4. Login สมาชิกอีกครั้ง → เปิด timeline เพื่อดูสถานะที่ Admin อัปเดต
5. แสดง Architecture เพื่ออธิบาย Redis, LightRAG, OpenAI และ SQLite

## หลักฐานทดสอบและแผนภาพ

| เอกสาร | ขอบเขต |
|---|---|
| [Architecture ล่าสุด](qa/diagrams/architecture.md) | ภาพรวม Docker / สมาชิก / เคส / Redis / RAG / OpenAI พร้อม PNG และ SVG |
| [Flow สมาชิกและเคส](qa/diagrams/member-case-flow.md) | สิทธิ์เจ้าของข้อมูลและขั้นตอนเคส |
| [Flow ตอบคำถาม RAG](qa/diagrams/rag-flow.md) | Cache → Vision เมื่อมีภาพ → ค้นข้อมูล → สร้างคำตอบ |
| [ผลสมาชิกและสิทธิ์](qa/results/membership-results.md) | ผลชุดทดสอบอัตโนมัติและการตรวจ UI |
| [ผล live text RAG และ cache](qa/results/price-cache-model.json) | ทดสอบราคา คำขอซ้ำ และรุ่น Pro Max ผ่าน API จริง |
| [แผนทดสอบ AI](qa/test-plan.md) | 10 คำถาม + 5 ภาพ + 5 กรณีความปลอดภัย |
| [วิธีรันชุดทดสอบ](qa/README.md) | วิธีเก็บผลและตรวจคำตอบด้วยคน |

ทดสอบ text RAG กับ OpenAI, answer cache และ UI สมาชิก/ประวัติจริงแล้ว การทดสอบคุณภาพภาพและชุดคำถาม live ครบ 20 กรณียังไม่เสร็จ ไฟล์ผลเก่าที่ระบุ blocked เป็นประวัติช่วงก่อนตั้งค่า key ไม่ใช้เป็นผลผ่านของระบบปัจจุบัน

## ยังไม่อยู่ในขอบเขตฟีเจอร์ที่เสร็จ

- ประวัติเก็บข้อความและจำนวนภาพ ไม่เก็บไฟล์ภาพต้นฉบับถาวร
- ยังไม่มีรีเซ็ตรหัสผ่าน ระบบแจ้งเตือน ชำระเงิน หรือจองซ่อมจริง
- สินค้า/บริการและราคาเป็นข้อมูลสาธิต ยังไม่มีข้อมูลจริงครบจากร้าน
- Backend ยังไม่ได้ deploy ออนไลน์พร้อมเว็บ static

---

# รายละเอียดการติดตั้งและการทำงานเดิม

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

Live OpenAI requests and LightRAG indexing require a valid key and API billing. Live text RAG and answer-cache requests have been tested with OpenAI. The full live image-quality suite remains pending; see qa/results/price-cache-model.json and qa/results/membership-results.md.
# ภาพประกอบและหลักฐานทดสอบ

การ์ด 16 ช่องใช้ภาพการ์ตูนใหม่ 3 แบบจาก built-in ImageGen ใน `dist/assets/` เป็นภาพประกอบทั่วไป รายการและราคาเป็นสาธิต เข้า RAG ได้ด้วย --include-demo และต้องคงป้ายสาธิต ดู prompt ที่ `qa/art-prompts.md`

ชุดทดสอบ 10 คำถาม + 5 ภาพ + 5 ความปลอดภัย: `qa/test-plan.md`; ผลจริงที่เก็บ: `qa/results/live-results.json`; สถานะ stack: `qa/stack-audit.md`; แผนภาพ PNG/SVG: `qa/diagrams/stack-flow.*`


## Demo price catalog

See qa/demo-catalog.md. The current Compose uses a fresh rag-data-demo-v2 volume and KB_VERSION=plimo-demo-v2. Previous volumes are preserved. Index with docker compose exec api python ingest.py --include-demo, then wait for document processing. Never relabel examples as confirmed shop prices.
# Members and repair cases (local MVP)

Members can register, sign in, reopen their own text chat history and submit repair cases with a linked conversation. Admins have a separate `admin.html` dashboard with status counts, allowed transitions, quoted demo price, notes and audit timeline. API ownership and roles are checked server-side; session tokens are hashed in SQLite, passwords use salted PBKDF2, and cross-origin writes are rejected. SQLite persists in the `member-data` Docker volume. RAG does not index member records.

Run `docker compose exec api python seed_demo.py` for the explicitly requested example data and accounts; see `qa/member-demo.md`. Seeding is idempotent. The original bootstrap admin password is local-only in ignored `.admin-login.txt` / `.env`; changing the env does not reset an existing account password. Public registration always creates role=user.

History stores text and image count, not original image files. Admin reads conversations attached to cases only. This MVP has no password recovery, email notification or payment. Members can explicitly approve/reject a versioned quote in their portal. Sites remains a static preview; use localhost:8081 for membership and RAG.


## ตรวจระบบและ Redis (อัปเดต 10 ตุลาคม 2026)

`GET /api/health` บอกการตั้งค่าและโหมด ส่วน `GET /api/ready` ตรวจการเชื่อมต่อ Redis, SQLite และ LightRAG เมื่อมีการตั้งค่า AI คืน 503 หากบริการที่ตรวจไม่พร้อม Endpoint นี้ไม่ได้ยืนยันเครดิต OpenAI หรือความครบของ index

```sh
docker compose exec -T api python -m unittest test_chat test_ingest test_membership test_redis_integration -v
curl -fsS http://127.0.0.1:8081/api/ready
```

ผลล่าสุด: 25 tests ผ่าน รวม 10 integration tests ที่ใช้ Redis จริง โดย AI providers เป็น mock ไม่เสียค่า OpenAI เพิ่ม ใช้คีย์ทดสอบแยก prefix และลบเฉพาะคีย์ทดสอบ ไม่ใช้ FLUSHDB ดู [ผลตรวจ Redis และฟีเจอร์ใหม่](qa/results/redis-case-approval.md)

สถานะเคสใช้ตัวตรวจคำถามเฉพาะ เช่น `เคสของฉัน`, `สถานะเคส`, `PLM-xxxxx` ไม่ใช่ LLM tool calling ทุกคำถาม และไม่อนุมัติราคาผ่านข้อความแชท ต้องกดยืนยันใบเสนอในพอร์ทัลสมาชิก ราคาเสนอเปลี่ยนแล้วคำตอบต่อใบเสนอเก่าจะถูกปฏิเสธด้วย 409
