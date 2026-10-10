# สถานะ stack วันที่ 10 ตุลาคม 2026

ระบบยังไม่ครบสำหรับ RAG จริง: Docker มี Nginx, FastAPI และ Redis ทำงาน ส่วน LightRAG ยังไม่เปิด และยังไม่มี OpenAI API key

| ส่วน | สถานะที่ตรวจพบ | หลักฐาน / ข้อจำกัด |
|---|---|---|
| เว็บร้านหน้าเดียว + ช่องแชท | ทำแล้ว | Catalog 16 ช่องรอข้อมูลจริง; รองรับแนบภาพ |
| Nginx | ทำงาน | localhost:8081, proxy /api |
| FastAPI | ทำงานใน demo | /api/health: configured=false, mode=demo |
| Redis | ทำงาน | Container healthy; PING=PONG |
| LightRAG | เตรียม compose แล้ว ยังไม่เปิด | อยู่ใน profile rag; ยังไม่มีหลักฐาน retrieval จริง |
| OpenAI Vision / generation / embedding | เขียน integration แล้ว ยังไม่ทดสอบจริง | ไม่มี API key; ไม่ได้เรียกบริการแบบเสียเงิน |
| Knowledge ingestion | มี script | ยังไม่ยืนยันว่าประมวลผลเอกสารใน LightRAG เสร็จ |
| Cache | มี implementation และ mock tests | ยังไม่วัดความเร็ว cache บน RAG จริง |
| เว็บที่เผยแพร่บน Sites | Static preview | ไม่ใช่การ deploy Docker backend |

ข้อมูลที่เข้า RAG ได้ตอนนี้มีเฉพาะข้อเท็จจริงร้านที่ได้รับ: รุ่นที่รับ เวลาเปิด วันหยุด และตรวจเช็คฟรี รายการรอข้อมูล 16 ช่อง ภาพประกอบการ์ด และภาพทดสอบไม่ใช่ข้อมูลยืนยันของร้าน

ผลทดสอบ offline contract 5 กรณีผ่าน แต่จำลอง OpenAI, LightRAG และ Redis จึงไม่รับรองคุณภาพคำตอบจริง ชุด live 20 กรณีบันทึก blocked ตามสถานะจริง ดู [ผลทดสอบ](results/live-results.json) และ [โจทย์ทดสอบ](test-plan.md)

Health endpoint ปัจจุบันตรวจค่าตั้งค่าเท่านั้น ไม่ใช่ readiness ของ LightRAG และการ ingest จึงต้องตรวจ dependencies และ index ก่อนสรุปว่าพร้อมใช้งานจริง

## ขั้นตอนเปิดระบบจริง

1. ตั้ง OPENAI_API_KEY ใน .env บนเครื่อง โดยไม่ส่ง key ลงแชท
2. เปิด `docker compose --profile rag up --build -d` แล้วตรวจ LightRAG และ Redis
3. รัน ingestion ตาม README และรอ LightRAG ประมวลผลเสร็จ
4. ทดสอบ Q01 ก่อน จากนั้นเก็บคำตอบจริงครบ 20 กรณี ตรวจด้วยคน และวัด cache แยก cold/warm

[แผนภาพ PNG](diagrams/stack-flow.png) / [SVG](diagrams/stack-flow.svg) ใช้กรอบและลูกศรจากแนวภาพตัวอย่าง ไม่ได้ใช้ AWS Organizations, KMS, DynamoDB หรือ RDS
