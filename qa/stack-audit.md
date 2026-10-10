# สถานะ stack วันที่ 10 ตุลาคม 2026

Flow ออกแบบและแผนภาพเสร็จแล้ว ครอบคลุมเว็บ แชทภาษาไทย ภาพ cache retrieval การตอบจากแหล่งข้อมูล และ ingestion แยกคลังสาธิต

| ส่วน | หลักฐานล่าสุด |
|---|---|
| เว็บร้านหน้าเดียว | 16 รายการสาธิต มีชื่อ ราคา และเงื่อนไข ครบทุกการ์ด |
| Nginx / FastAPI / Redis | ทำงานที่ localhost:8081; Redis healthy |
| LightRAG | /health HTTP 200 healthy |
| Index สาธิต | ประมวลผลครบ 17 เอกสาร failed=0 ใน volume rag-data-demo-v2; เก็บ volume เก่าไว้ |
| OpenAI extraction / embeddings | ประมวลผล index สำเร็จ |
| OpenAI answer + LightRAG retrieval | Q06 ตอบราคา iPhone 13 สาธิตเริ่มต้น 3,200 บาท มี source จาก demo-slot-3 |
| Vision | มี integration และ offline contract; ยังไม่มีผลทดสอบภาพจริงรอบล่าสุด |
| Cache | มี offline contract และไฟล์ผล smoke แยก |
| Sites | เผยแพร่ storefront แบบ static; backend RAG อยู่ Docker local |

รายการราคา demo=true และ confirmed=false ต้องแสดงป้ายสาธิตเสมอ ไม่ใช่ราคาเสนอจริง ไม่มีการรับจองหรือชำระเงิน ภาพประกอบและภาพทดสอบไม่ถูก ingest

[ผลราคา RAG](results/demo-price-verified.json) / [ผล cache และ Pro Max](results/price-cache-model.json) / [รายการราคา](demo-catalog.md)

ผล live-results.json ที่ blocked 20 กรณีเป็นหลักฐานจากรอบก่อนตั้ง key ไม่ใช่สถานะล่าสุด ยังไม่ได้รันทดสอบคุณภาพครบ 20 กรณีบนคลังใหม่นี้

ทดสอบ offline 6 กรณีผ่าน (5 chat contracts + demo-ingestion opt-in) ใช้ upstream จำลอง ไม่รับรองคุณภาพโมเดลครบทุกกรณี

พบและแก้ปัญหา context budget: graph ใช้พื้นที่จนไม่มี source chunks จึงจำกัด entity/relation อย่างละ 800 tokens และเหลืองบสำหรับ chunks ภายใน 5,000 tokens ไม่ตอบราคาจากกราฟที่ไม่มีต้นฉบับ

Health ของ FastAPI ยังตรวจเฉพาะค่าตั้งค่า ต้องตรวจ LightRAG และจำนวนเอกสารแยกก่อนบอกว่าพร้อมใช้งาน

[PNG](diagrams/stack-flow.png) / [SVG](diagrams/stack-flow.svg) / [RAG flow Mermaid](diagrams/rag-flow.md) ใช้กรอบและลูกศรตามแนวภาพตัวอย่าง ไม่ได้ใช้ AWS ใน stack นี้
