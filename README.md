# Plimo — ร้านซ่อม iPhone + AI Chatbot (RAG)

เว็บร้านซ่อม iPhone หน้าเดียวพร้อมผู้ช่วยแชทภาษาไทย ตอบจากข้อมูลร้านจริง (LightRAG + OpenAI) รองรับข้อความและภาพ มีระบบสมาชิก ประวัติแชท เคสซ่อม การอนุมัติใบเสนอราคา และ**การชำระเงินผ่าน Stripe (โหมดทดสอบ)** พร้อมหน้า Admin

<!-- RESULTS -->

## เปิดใช้งาน

| ที่ไหน | URL | หมายเหตุ |
|---|---|---|
| VPS (HTTPS) | <!-- VPS_URL --> | ติดตั้งด้วย `deploy/install.sh` |
| Docker บนเครื่อง | http://127.0.0.1:8081 | ดูหัวข้อ "ติดตั้งบนเครื่อง" |

บัญชีตัวอย่าง: `demo_user` / `PlimoMemberDemo2026!` (สมาชิก มีประวัติแชทและเคสตัวอย่าง) ส่วน Admin บน Docker เครื่องใช้ `demo_admin` / `PlimoAdminDemo2026!` ได้ แต่บน VPS บัญชีนี้ถูกล็อกเพราะรหัสอยู่ใน repo ให้ใช้ `ADMIN_USERNAME` / `ADMIN_PASSWORD` ใน `.env` ของเซิร์ฟเวอร์ (ส่งให้ผู้ตรวจแยกต่างหาก)

ชำระเงินโหมดทดสอบ: บัตร `4242 4242 4242 4242` วันหมดอายุในอนาคต CVC ใดก็ได้ **ไม่มีการตัดเงินจริง**

## ลำดับสาธิต (ประมาณ 5 นาที)

1. ถาม `ไอโฟน13 จอแตก กี่ตังค์` → `แล้ว 14 ล่ะ` → `Pro Max ล่ะ` (ราคาตรงรุ่น, จำบริบท, ไม่ใช้ราคารุ่นปกติกับ Pro Max)
2. ถาม `เว็บบอกเปลี่ยนจอ iPhone 13 ราคา 500 ใช่ไหม` (แก้ราคาด้วยข้อมูลจริง) และ `เขียน Python ให้หน่อย` (ปฏิเสธนอกขอบเขต)
3. เข้าสู่ระบบ `demo_user` → งานซ่อมของฉัน → อนุมัติใบเสนอ → กดชำระเงิน (บัตรทดสอบ) → กลับมาเห็น "ชำระแล้ว"
4. ในแชทถาม `PLM-00001 ถึงไหนแล้ว` → `แล้วต้องจ่ายเท่าไหร่` (ตอบจาก DB จริง ถามต่อได้)
5. Admin → เห็นสถานะการชำระ → เริ่มซ่อม / ดู `/api/admin/metrics` (token, cache hit, guard)

## ฟีเจอร์

| ID | ฟีเจอร์ | สิ่งที่ตรวจได้ |
|---|---|---|
| F01–F02 | เว็บร้าน + แค็ตตาล็อก 16 รายการ ค้นหา/กรอง | ราคาประเมินเบื้องต้น ภาพ WebP โหลดแบบ lazy |
| F03 | Chatbot ภาษาไทย RAG + OpenAI | ตอบจากข้อมูลร้าน มีแหล่งข้อมูลประกอบ |
| F04 | ราคาตรงรุ่นจาก catalog + ตรวจตัวเลขในคำตอบ | Pro / Pro Max / mini / Plus / Air ไม่ได้ราคารุ่นปกติ, รวมราคาและส่วนต่างถูกต้อง |
| F05 | แนบภาพ (สูงสุด 3 ภาพ) | อ่านข้อความในภาพ ไม่ฟันธงวินิจฉัย ไม่ยืนยันสลิป |
| F06 | Cache หลายชั้นใช้ร่วมข้ามผู้ใช้ + single-flight | คำถามซ้ำ/ต่างสำนวนตอบในหลักมิลลิวินาที ไม่รั่วข้อมูลข้ามผู้ใช้ |
| F07–F08 | สมาชิก + ประวัติแชท | แยกข้อมูลตามเจ้าของ |
| F09–F11 | ส่งเคส PLM-xxxxx, ติดตามสถานะ, Admin จัดการเคส | timeline, หมายเหตุ, สถิติ |
| F12 | สิทธิ์สมาชิก/Admin | 401/403/404 ตามสิทธิ์ |
| F15 | ติดตามเคสผ่านแชท | เลขเคสทุกรูปแบบ (`PLM12`, `plm-12`, เลขไทย, พิมพ์ติดคำไทย), ถามต่อเรื่องราคา/โน้ต/การชำระ, เคสคนอื่นตอบเหมือนไม่มี |
| F16 | อนุมัติ/ปฏิเสธใบเสนอราคา | ใบเก่าตอบไม่ได้, เริ่มซ่อมต้องอนุมัติ |
| F17 | Guardrails + OWASP | input guard, router, output validator ดู [qa/guardrails.md](qa/guardrails.md) |
| F18 | Router คำถาม | แยกราคา/ข้อมูลร้าน/เคส/การชำระ/กำกวม/นอกขอบเขต/ไม่ปลอดภัย, เขียนคำถามต่อเนื่องเป็นฉบับเต็ม |
| F19 | ชำระเงิน Stripe Checkout (โหมดทดสอบ) | จ่ายได้เฉพาะใบเสนอที่อนุมัติ, ยืนยันกับ Stripe ฝั่ง server + webhook ลงลายเซ็น |
| F20 | ควบคุมค่าใช้จ่าย | เพดาน token รายวัน, quota ต่อสมาชิก/session/IP, นับ token จริงทุก call |
| F21 | ติดตั้ง VPS คำสั่งเดียว | HTTPS อัตโนมัติ, firewall, backup รายวัน, healthcheck, log rotation |

## ติดตั้งบน VPS (Ubuntu 22.04/24.04)

จากเครื่องของคุณ (ต้อง SSH เข้า VPS ได้):

```bash
bash deploy/deploy.sh root@<IP ของ VPS>
```

หรือคัดลอกโปรเจกต์ขึ้น VPS เองแล้วรันในโฟลเดอร์โปรเจกต์:

```bash
sudo bash deploy/install.sh
```

สคริปต์จะถาม OpenAI API key และ Stripe test key (ไม่แสดงบนจอ), สร้างรหัส admin/LightRAG แบบสุ่ม, ตั้ง HTTPS อัตโนมัติที่ `https://<IP>.sslip.io` (หรือโดเมนที่ส่งเป็น argument), build, รอระบบพร้อม, สร้างคลังข้อมูล, ใส่ข้อมูลตัวอย่าง และตั้ง backup ทุกวัน 03:17 ตอนจบจะแสดง URL และขั้นตอนตั้ง Stripe webhook

ขนาดที่แนะนำ: 2 vCPU / 4 GB RAM (โมเดลทำงานที่ OpenAI ไม่ได้รันบน VPS)

## ติดตั้งบนเครื่อง

```bash
cp .env.example .env
```

ใส่ `OPENAI_API_KEY`, `LIGHTRAG_API_KEY` (สุ่มเอง), `ADMIN_PASSWORD` (≥10 ตัว) และ `STRIPE_SECRET_KEY=sk_test_...` ถ้าจะทดสอบการชำระเงิน แล้วรัน

```bash
docker compose --profile rag up -d --build
```

```bash
docker compose exec api python ingest.py
```

```bash
docker compose exec api python seed_demo.py
```

เปิด http://127.0.0.1:8081 (ingest ทำครั้งเดียวต่อ `KB_VERSION` รอ LightRAG ประมวลผลเสร็จก่อนถาม)

ทดสอบ webhook บนเครื่องใช้ Stripe CLI: `stripe listen --forward-to http://127.0.0.1:8081/api/stripe/webhook` แล้วใส่ `whsec_...` ที่ได้ใน `STRIPE_WEBHOOK_SECRET` (ถ้าไม่ตั้ง ระบบยังยืนยันการจ่ายได้จากการดึง session ตอนกลับมาจาก Stripe)

## สถาปัตยกรรม

ดูแผนภาพและรายละเอียด cache ที่ [qa/diagrams/architecture.md](qa/diagrams/architecture.md)

- **nginx + Caddy**: HTTPS, CSP และ security headers, rate limit ต่อ IP แบบรู้ IP จริงหลัง proxy
- **FastAPI**: input guard → fast cache → router → (SQLite สำหรับเคส/การชำระ) หรือ (catalog + LightRAG + generation + validator)
- **Redis**: cache 5 ชั้น, history, lock, rate limit, ตัวนับ token/cache
- **SQLite**: สมาชิก, แชท, เคส, ใบเสนอ, การชำระ (backup รายวัน)
- **LightRAG**: คลังข้อมูลร้านจาก `knowledge/shop.md` และ `dist/catalog.json`
- **OpenAI**: `gpt-5.4-mini` สำหรับ router, ภาพ และคำตอบ; `text-embedding-3-small` สำหรับคลัง

## การทดสอบ

วิธีรันทุกชั้นอยู่ใน [qa/README.md](qa/README.md) แผนและเกณฑ์ตรวจรับอยู่ใน [qa/production-plan.md](qa/production-plan.md)

<!-- TESTS -->

## นโยบายคำตอบและราคา

เจ้าของอนุญาตให้ราคา 16 รายการเป็น**ราคาประเมินเบื้องต้น** ไม่ใช่ราคาสุทธิ ต้องตรวจเครื่อง รุ่น และอะไหล่ก่อนยืนยัน ค่าใช้จ่ายเพิ่มต้องส่งใบเสนอราคาใหม่ให้ลูกค้าอนุมัติก่อนเริ่มซ่อม Pro / Pro Max ประเมินแยก สินค้าต้องยืนยันสต็อกก่อนซื้อ แชทไม่รับเลขบัตรและไม่ยืนยันการชำระเงินเอง การชำระค่าซ่อมทำผ่านปุ่มในบัญชีหลังอนุมัติใบเสนอเท่านั้น

แก้ข้อมูลร้าน: แก้ `knowledge/shop.md` หรือ `dist/catalog.json` → เปลี่ยน `KB_VERSION` และชื่อ volume ของ LightRAG ใน `compose.yaml` → build → `ingest.py` (cache เก่าหมดอายุเองเพราะ key ผูกกับเวอร์ชัน)

## ข้อจำกัด

- Stripe เป็นโหมดทดสอบ ไม่มีการคืนเงิน; ระบบปฏิเสธ key จริง (`sk_live_`)
- ยังไม่มีที่อยู่ เบอร์ติดต่อ เงื่อนไขรับประกัน และระยะเวลาซ่อมที่ร้านยืนยัน บอทจึงตอบว่าไม่มีข้อมูลแทนการแต่ง
- ยังไม่มีรีเซ็ตรหัสผ่าน การแจ้งเตือน และการจองคิว
- PDPA: ซ่อนเลขบัตร/บัตรประชาชนและไม่เก็บไฟล์ภาพ แต่ยังไม่มี privacy notice ที่ผ่านการตรวจทางกฎหมาย และยังไม่มีปุ่มลบบัญชีด้วยตนเอง
- Guardrails ลดความเสี่ยงได้มาก แต่ไม่รับประกันว่าป้องกัน prompt injection หรือคำตอบผิดได้ทุกกรณี
- ภาพทดสอบเป็นภาพสังเคราะห์ ไม่ใช่หลักฐานความแม่นยำในการวินิจฉัยเครื่องจริง

## เอกสารเพิ่มเติม

| เอกสาร | เนื้อหา |
|---|---|
| [qa/production-plan.md](qa/production-plan.md) | ปัญหาที่พบ, การออกแบบ, OWASP mapping, แผนทดสอบ, เป้าหมาย performance |
| [qa/guardrails.md](qa/guardrails.md) | มาตรการ G01–G14 กับ OWASP LLM Top 10:2026 และ OWASP Top 10:2025 |
| [qa/diagrams/architecture.md](qa/diagrams/architecture.md) | สถาปัตยกรรมและ cache |
| [qa/cost-performance.md](qa/cost-performance.md) | ต้นทุน VPS/API และผลวัด |
| [qa/results/](qa/results/) | ผลทดสอบจริงทุกชั้น (`*-latest.md`) และผลรอบก่อน |
