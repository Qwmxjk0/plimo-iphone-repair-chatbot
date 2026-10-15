# API check — 2026-10-15 19:46 (เวลาไทย) · `https://203-156-66-86.sslip.io`

**33/33 checks ผ่าน · ครอบคลุม 24/24 endpoint** · Stripe ปิดอยู่ (ยังไม่ใส่ test key) จึงตรวจได้แค่ว่าปิดอย่างปลอดภัย

| | Method | Endpoint | ได้ | ควรได้ | หมายเหตุ |
|---|---|---|---|---|---|
| ✅ | GET | `/api/health` | 200 | 200 |  |
| ✅ | GET | `/api/ready` | 200 | 200 | Redis + LightRAG พร้อม |
| ✅ | POST | `/api/chat` | 200 | 200 | ผู้เยี่ยมชม · route=shop_info · ตอบ 132 ตัวอักษร |
| ✅ | POST | `/api/session/new` | 200 | 200 |  |
| ✅ | POST | `/api/auth/register` | 200 | 200 |  |
| ✅ | GET | `/api/auth/me` | 200 | 200 | api_ab0878 |
| ✅ | POST | `/api/auth/logout` | 200 | 200 |  |
| ✅ | POST | `/api/auth/login` | 200 | 200 |  |
| ✅ | POST | `/api/chat` | 200 | 200 | สมาชิก + รูป · เก็บรูป 1 รูป |
| ✅ | GET | `/api/member/conversations` | 200 | 200 | 1 บทสนทนา |
| ✅ | GET | `/api/member/conversations/{cid}` | 200 | 200 | 2 ข้อความ |
| ✅ | GET | `/api/images/{image_id}` | 200 | 200 | เจ้าของเปิดได้ · image/jpeg · 44,197 bytes |
| ✅ | GET | `/api/images/{image_id}` | 404 | 404 | สมาชิกอื่นเปิดไม่ได้ |
| ✅ | POST | `/api/member/cases` | 200 | 200 | PLM-00029 |
| ✅ | GET | `/api/member/cases` | 200 | 200 |  |
| ✅ | GET | `/api/member/cases/{cid}` | 200 | 200 | submitted |
| ✅ | GET | `/api/admin/cases` | 200 | 200 | 29 เคส |
| ✅ | GET | `/api/admin/cases/{cid}` | 200 | 200 | รูปแนบ 1 |
| ✅ | GET | `/api/images/{image_id}` | 200 | 200 | ผู้ดูแลเปิดได้เมื่อแนบกับเคสแล้ว |
| ✅ | POST | `/api/admin/cases/{cid}/assist` | 200 | 200 | AI แนะนำสถานะ received ราคา None |
| ✅ | PATCH | `/api/admin/cases/{cid}` | 200 | 200 | → received |
| ✅ | PATCH | `/api/admin/cases/{cid}` | 200 | 200 | → checking |
| ✅ | PATCH | `/api/admin/cases/{cid}` | 200 | 200 | → awaiting_approval |
| ✅ | PATCH | `/api/admin/cases/{cid}` | 409 | 409 | ข้ามขั้นตอนถูกปฏิเสธ |
| ✅ | GET | `/api/admin/insights` | 200 | 200 | คำถามวันนี้ 784 |
| ✅ | GET | `/api/admin/metrics` | 200 | 200 |  |
| ✅ | POST | `/api/member/cases/{cid}/quote-decision` | 200 | 200 | อนุมัติใบเสนอราคา |
| ✅ | POST | `/api/member/cases/{cid}/checkout` | 503 | 200 / 503 | ปิดอยู่: ยังไม่ใส่ STRIPE_SECRET_KEY |
| ✅ | GET | `/api/member/payments/confirm` | 404 | 404 | รหัสที่ไม่มีอยู่ถูกปฏิเสธ |
| ✅ | POST | `/api/stripe/webhook` | 503 | 400 / 503 | ปิดอยู่: ยังไม่ใส่ STRIPE_WEBHOOK_SECRET |
| ✅ | GET | `/api/member/cases` | 401 | 401 | ไม่เข้าสู่ระบบ → 401 |
| ✅ | GET | `/api/admin/cases` | 403 | 403 | สมาชิกเรียก API ผู้ดูแล → 403 |
| ✅ | GET | `/api/member/cases/{cid}` | 404 | 404 | เคสของคนอื่น → 404 |
