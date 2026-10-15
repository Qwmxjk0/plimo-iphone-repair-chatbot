# Guardrails ของ Plimo และการจับคู่ OWASP

ปรับปรุง: 15 ตุลาคม 2026 (แทนฉบับ 10 ตุลาคม 2026)

Guardrails ของ Plimo มีสามชั้น: **โค้ดตรวจ input ก่อนถึงโมเดล**, **router แยกเส้นทางคำตอบ** และ **โค้ดตรวจ output หลังโมเดลตอบ** ข้อมูลเชิงธุรกรรม (เคส ใบเสนอ การชำระเงิน) มาจาก SQLite เสมอ โมเดลไม่มี tool ที่แก้ข้อมูลได้ ตารางนี้เป็นการประเมินโค้ดของโครงการโดยผู้พัฒนา ไม่ใช่การรับรองจาก OWASP และไม่อ้างว่าป้องกันได้ 100%

## มาตรการ

| ID | ป้องกันอะไร | ทำอย่างไร | โค้ด | Test |
|---|---|---|---|---|
| G01 | ราคาผิดรุ่น/แต่งราคา | ราคาจาก `catalog.json` ตรงรุ่นและรุ่นย่อย ส่งเข้า prompt เป็นข้อมูลหลัก แล้ว**ตรวจทุกตัวเลข "บาท" ในคำตอบ** ถ้าไม่ตรง catalog ใช้คำตอบ template แทน | `catalog.py`, `main.py: checked()` | P01–P30, A15–A16, `test_logic`, `test_chat` |
| G02 | Prompt injection | input guard จับรูปแบบชัดเจน (ไม่เรียกโมเดล), router จัด `unsafe` ตอบข้อความคงที่, instructions ให้ถือข้อความ/ภาพ/เอกสาร/ประวัติเป็นข้อมูล | `nlu.py: INJECTION`, `router.py`, `main.py` | S01, S04, S05, S12, S13, S15 |
| G03 | ข้อมูลสมาชิกข้ามบัญชี | ทุก query ของเคส/บทสนทนา/การชำระใช้ `user_id`; เคสคนอื่นกับเคสที่ไม่มีได้ข้อความเดียวกัน | `membership.py`, `payments.py` | C07, C08, W01, W02, `test_membership`, `test_payments` |
| G04 | เริ่มซ่อม/จ่ายเงินผิดขั้นตอน | state machine ใบเสนอ: เริ่มซ่อมต้องอนุมัติ, ใบเสนอเก่าตอบไม่ได้, จ่ายได้เฉพาะใบที่อนุมัติ, จ่ายแล้วออกใบใหม่/ยกเลิกไม่ได้ | `membership.py: update_case`, `payments.py` | W08, `test_payments` |
| G05 | ไฟล์/คำขอผิดรูป | ภาพ JPEG/PNG/WebP ≤10 MB ≤3 ภาพ ≤20 ล้านพิกเซล re-encode ตัด EXIF; ข้อความ ≤3,000 ตัวอักษร | `main.py: clean_image/chat` | W12 |
| G06 | ใช้ทรัพยากรเกิน | nginx 30 คำขอแชท/นาที/IP และ login 20/นาที; API: ต่อสมาชิก 120/ชม. ต่อ session 60/ชม. ต่อ IP 400/ชม.; lock ต่อบทสนทนา; **เพดาน token รายวัน** (เกินแล้วยังตอบจาก cache/DB ได้); single-flight ทุกชั้น | `nginx.conf`, `main.py` | K04, `test_chat` (budget, rate, single-flight), load test |
| G07 | รัน HTML/script จากคำตอบ | frontend ใช้ `textContent` ทุกจุด ไม่มี `innerHTML`; CSP ไม่อนุญาต inline script | `dist/*.js`, `nginx.conf` | S16, W07, W03 |
| G08 | เผย prompt/key/บริบทภายใน | key อยู่ฝั่ง server เท่านั้น; output validator แทนคำตอบที่มีเครื่องหมายภายใน (`price_status`, `confirmed=`, รูปแบบ key) | `main.py: LEAK` | S03, S11, `test_chat` |
| G09 | ข้อมูลส่วนตัว (PDPA) | ซ่อนเลขบัตร (Luhn + ชนิดบัตร) และเลขบัตรประชาชน (checksum) ก่อนเก็บ log หรือส่งต่อ; ข้อความที่มีเลขบัตรไม่ถูกส่งให้โมเดลเลย; cache ร่วมสร้างจากคำถามฉบับเต็มที่ตัดข้อมูลส่วนตัว ไม่ใช้ history ดิบ | `nlu.py: inspect`, `main.py` | S08, S09, M07, `test_chat` |
| G10 | นอกขอบเขตร้าน | router จัด `out_of_scope` แล้วตอบข้อความคงที่ ไม่เรียก generation (แก้ RT01) | `router.py`, `main.py` | S06, S07, S14 |
| G11 | แชททำรายการเกินสิทธิ์ | โมเดลไม่มี tool; ขอให้ยกเลิก/อนุมัติ/เปลี่ยนสถานะผ่านแชทได้คำตอบแนะนำทางที่ถูก และ eval ตรวจซ้ำว่าสถานะใน DB ไม่เปลี่ยน | `membership.py: case_lines` | C16, C17, S18 |
| G12 | ยืนยันการชำระผิด | สถานะการชำระมาจาก DB ที่ยืนยันกับ Stripe แล้วเท่านั้น; ไม่เชื่อ query ของ redirect; webhook ตรวจ HMAC + เวลา + กันซ้ำ; รับเฉพาะ `sk_test_` | `payments.py` | S10, I05, Y01, `test_payments`, W10 |
| G13 | ข้อมูลเก่า/ผิดเวลา | วันเวลาปัจจุบันใส่ใน prompt เมื่อคำถามขึ้นกับเวลา และ cache สั้น 10 นาที; เปลี่ยน KB/prompt/catalog แล้ว cache key เปลี่ยนเอง | `main.py: now_text/answer_key` | F03, F04 |
| G14 | Upstream ล่ม | router ล่ม → ใช้กฎ (เคสยังตอบได้); OpenAI/LightRAG ล่ม → ข้อความ error ที่ปลอดภัย ไม่สร้างคำตอบปลอม; Stripe ล่ม → ไม่บันทึกว่าจ่ายแล้ว | `main.py`, `payments.py` | `test_chat` (provider error, budget), W12 |

## OWASP Top 10 for LLM Applications 2026

อ้างอิง [OWASP GenAI LLM Top 10 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/)

| หมวด | มาตรการ | Test |
|---|---|---|
| LLM01 Prompt Injection | G02, G07, G11 | S01, S04, S05, S12, S13, S15 |
| LLM02 Sensitive Information Disclosure | G03, G08, G09 | S02, S08, S09, S17, M07, C07 |
| LLM03 Excessive Agency | G04, G11, G12 | C16, C17, S18, S10 |
| LLM04 Supply Chain | image ทุกตัว pin เวอร์ชัน/digest, Python lock ตรงเวอร์ชันที่ทดสอบ, container ไม่รันเป็น root | W05 |
| LLM05 Data and Model Poisoning | คลัง RAG ingest จาก `knowledge/` และ `catalog.json` ใน repo เท่านั้น แชทแก้คลังไม่ได้, ไม่ fine-tune | S04 |
| LLM06 Unbounded Consumption | G05, G06 | S14, K04, load test |
| LLM07 Misinformation | G01, G13, router ถามกลับเมื่อกำกวม | P*, A*, F06–F10, S20 |
| LLM08 Hidden Context Exposure | G08 | S03, S11 |
| LLM09 Vector and Embedding Weaknesses | คลัง RAG เฉพาะข้อมูลร้าน แยก workspace ตาม `KB_VERSION`; ข้อมูลสมาชิกอยู่ SQLite ไม่เข้า RAG; ผลค้นเป็นข้อมูลไม่ใช่คำสั่ง | S04, S11 |
| LLM10 Improper Output Handling | G07, ตรวจ URL ชำระเงินต้องเป็น `checkout.stripe.com` ก่อน redirect | S16, W07 |

## OWASP Top 10:2025 (web)

อ้างอิง [OWASP Top 10:2025](https://top10.owasp.org/2025)

| หมวด | มาตรการ | Test (`qa/run_security.py`) |
|---|---|---|
| A01 Broken Access Control | G03, admin ตรวจ role, origin check กัน CSRF | W01, W02, W13 |
| A02 Security Misconfiguration | CSP เข้ม, nosniff, frame-ancestors, Referrer/Permissions-Policy, ซ่อนเวอร์ชัน, ปิด docs/openapi, ไม่ serve ไฟล์ลับ | W03, W04 |
| A03 Software Supply Chain Failures | pin image + `requirements.lock` | W05 |
| A04 Cryptographic Failures | HTTPS (Caddy) + HSTS, cookie Secure/HttpOnly/SameSite=Strict, PBKDF2 600k, token เก็บแบบ hash | W06 |
| A05 Injection | SQL parameter ทุกจุด, `textContent`, prompt แยกข้อมูลผู้ใช้เป็น JSON | W07, C15, S16 |
| A06 Insecure Design | G04, G06 | W08 |
| A07 Authentication Failures | จำกัดต่อบัญชี+IP (ไม่ล็อกทั้ง NAT), รหัสผ่าน ≥10, session หมดอายุ 7 วัน | W09 |
| A08 Software or Data Integrity Failures | webhook HMAC + timestamp + event id กันซ้ำ, ยืนยันการชำระกับ Stripe API | W10, `test_payments` |
| A09 Security Logging and Alerting Failures | log เหตุการณ์ (chat route, guard, router fallback, validator block, payment) ไม่มี key/เลขบัตร; ตัวนับใน `/api/admin/metrics` | W11 |
| A10 Mishandling of Exceptional Conditions | G14, input ผิดรูปได้ 4xx ไม่ใช่ 500 | W12 |

## ข้อจำกัดที่ยังเหลือ

- Router และ validator ลดความเสี่ยงได้มาก แต่ไม่รับประกันว่าป้องกัน prompt injection หรือ hallucination ได้ทุกกรณี
- Validator ตรวจตัวเลขราคา ไม่ได้ตรวจความหมายของทุกประโยค
- PDPA: มีการซ่อนข้อมูลละเอียดอ่อนและไม่เก็บไฟล์ภาพ แต่ยังไม่มีหน้า privacy notice ที่ผ่านการตรวจทางกฎหมาย และยังไม่มีปุ่มลบบัญชี/ลบประวัติด้วยตนเอง
- Stripe เป็นโหมดทดสอบ ไม่มีระบบคืนเงิน
