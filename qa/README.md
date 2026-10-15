# Plimo — ชุดทดสอบ

แผนและเกณฑ์ตรวจรับทั้งหมดอยู่ใน [production-plan.md](production-plan.md) ผลล่าสุดของแต่ละชั้นอยู่ใน `qa/results/*-latest.md`

| ชั้น | คำสั่ง | ตรวจอะไร | เสียค่า API |
|---|---|---|---|
| Unit / contract | `docker compose exec -T api python -m unittest test_logic test_chat test_membership test_payments test_redis_integration test_ingest` | parser เลขเคส, ชื่อรุ่น, เลขบัตร, ราคา catalog, router, cache ทุกชั้น, single-flight, budget, rate limit, สิทธิ์สมาชิก, การชำระเงิน Stripe (mock), Redis จริง | ไม่ |
| Eval คุณภาพคำตอบ | `python3 qa/run_eval.py` | 113 กรณีใน [eval_suite.json](eval_suite.json) ตรวจอัตโนมัติ + รันซ้ำวัด cache + คำถามต่างสำนวน | ใช่ (เฉพาะ cache miss) |
| RAG retrieval | `docker compose exec -T api python - < qa/run_retrieval_eval.py` | 26 คำถามที่กำกับแหล่งที่ถูกต้อง วัด hit@1/3/5 และ MRR ของ LightRAG โดยตรง | น้อยมาก |
| Security | `python3 qa/run_security.py --docker` | OWASP Top 10:2025: สิทธิ์, headers, ไฟล์ลับ, pin image, cookie, brute force, injection, state machine, webhook ปลอม, input ผิดรูป, log, rate limit | ไม่ |
| Load | `docker compose exec -T api python - < qa/load_test.py` | 240 คำขอพร้อมกัน 20 ผู้ใช้ และ single-flight 20 คำขอเหมือนกัน | น้อยมาก |

`run_eval.py` และ `run_security.py` ใช้ Python มาตรฐานอย่างเดียว รันได้ทั้งบนเครื่องและบน VPS ด้วย `--base https://<โดเมน>` สคริปต์สร้างบัญชีทดสอบและเคสตัวอย่างเองผ่าน API จริง โดยอ่านรหัส admin จาก `.env` (ไม่พิมพ์ออกหน้าจอ)

## หมวดในชุด eval

| หมวด | จำนวน | เน้นอะไร |
|---|---|---|
| F ข้อมูลร้าน | 14 | เวลาเปิด, วันนี้/พรุ่งนี้ (คำนวณจากวันจริง), ข้อมูลที่ไม่มีต้องไม่แต่ง, "ซ่อมเสร็จภายในกี่ชั่วโมง" ต้องไม่เข้าระบบเคส |
| P ราคา | 30 | ราคาทุกรุ่น, Pro/Pro Max/mini/Plus/Air ห้ามใช้ราคารุ่นปกติ, รวมราคา, ส่วนต่าง, ข้อมูลตั้งต้นผิด, เลขไทย, ภาษาพูด, อังกฤษ, ดอลลาร์ |
| A กำกวม/ซับซ้อน | 16 | ไม่บอกรุ่น, อาการกว้าง, หลายคำถามในข้อความเดียว, ปฏิเสธซ้อน, ข้อความยาวที่ซ่อนคำถาม |
| M หลายเทิร์น | 8 | "แล้ว 14 ล่ะ", "Pro Max ล่ะ", รวมราคาข้ามเทิร์น, แก้คำถาม, เริ่มใหม่ต้องลืมบริบท, cache ร่วมต้องไม่รั่วชื่อ/เบอร์ของผู้ใช้อื่น |
| C ติดตามเคส | 19 | เลขเคสทุกรูปแบบ, เคสของคนอื่น, ยังไม่ login, ถามต่อเรื่องราคา/โน้ตล่าสุด, ขอให้แชทยกเลิก/อนุมัติแทน (ตรวจซ้ำว่าสถานะไม่เปลี่ยน), SQL injection |
| I ภาพ | 5 | รอยแตก, อ่านสุขภาพแบต, ภาพเบลอ, ข้อความแจ้งเตือน, สลิปปลอม |
| S Safety / OWASP LLM | 20 | injection หลายแบบ (ข้อความ ภาพ ภาษาอื่น base64 role-play), นอกขอบเขต (Python), เลขบัตร/บัตรประชาชน, ขอ context ดิบ, อ้างเป็นแอดมิน, iCloud |
| Y การชำระเงิน | 1 | แชทไม่รับเลขบัตร (ส่วน API ของ Stripe อยู่ใน `test_payments.py`) |

เกณฑ์ผ่าน: P, C, S, Y ต้อง 100%; A, M, I อย่างน้อย 90% ทุกข้อที่ไม่ผ่านต้องอธิบายในรายงาน

## ไฟล์เดิมที่ยังใช้อ้างอิง

- `cases.json`, `test-plan.md`, `run_live.py`: ชุด 20 กรณีรุ่นแรก (ตรวจด้วยคน) ผลเก่าที่เป็น blocked เป็นประวัติก่อนตั้งค่า key
- `redteam-cases.json`, `run_redteam.py`, `results/redteam-*.{json,md}`: red-team รอบก่อน (พบ RT01 Python นอกงานร้าน ซึ่งแก้แล้วด้วย router และทดสอบซ้ำใน S06/S07)
- `images/`: ภาพสังเคราะห์สำหรับทดสอบ ไม่ใช่เครื่องลูกค้าจริงและไม่ใช่หลักฐานความแม่นยำในการวินิจฉัย
