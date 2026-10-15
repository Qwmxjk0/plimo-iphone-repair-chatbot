# API check — 2026-10-15 22:18 (เวลาไทย) · `https://203-156-66-86.sslip.io`

**33/33 checks ผ่าน · ครอบคลุม 24/24 endpoint**

| | Method | Endpoint | ได้ | ควรได้ | หมายเหตุ |
|---|---|---|---|---|---|
| ✅ | GET | `/api/health` | 200 | 200 |  |
| ✅ | GET | `/api/ready` | 200 | 200 | Redis + LightRAG พร้อม |
| ✅ | POST | `/api/chat` | 200 | 200 | ผู้เยี่ยมชม · route=shop_info · ตอบ 132 ตัวอักษร |
| ✅ | POST | `/api/session/new` | 200 | 200 |  |
| ✅ | POST | `/api/auth/register` | 200 | 200 |  |
| ✅ | GET | `/api/auth/me` | 200 | 200 | api_40cac8 |
| ✅ | POST | `/api/auth/logout` | 200 | 200 |  |
| ✅ | POST | `/api/auth/login` | 200 | 200 |  |
| ✅ | POST | `/api/chat` | 200 | 200 | สมาชิก + รูป · เก็บรูป 1 รูป |
| ✅ | GET | `/api/member/conversations` | 200 | 200 | 1 บทสนทนา |
| ✅ | GET | `/api/member/conversations/{cid}` | 200 | 200 | 2 ข้อความ |
| ✅ | GET | `/api/images/{image_id}` | 200 | 200 | เจ้าของเปิดได้ · image/jpeg · 44,197 bytes |
| ✅ | GET | `/api/images/{image_id}` | 404 | 404 | สมาชิกอื่นเปิดไม่ได้ |
| ✅ | POST | `/api/member/cases` | 200 | 200 | PLM-00035 |
| ✅ | GET | `/api/member/cases` | 200 | 200 |  |
| ✅ | GET | `/api/member/cases/{cid}` | 200 | 200 | submitted |
| ✅ | GET | `/api/admin/cases` | 200 | 200 | 35 เคส |
| ✅ | GET | `/api/admin/cases/{cid}` | 200 | 200 | รูปแนบ 1 |
| ✅ | GET | `/api/images/{image_id}` | 200 | 200 | ผู้ดูแลเปิดได้เมื่อแนบกับเคสแล้ว |
| ✅ | POST | `/api/admin/cases/{cid}/assist` | 200 | 200 | AI แนะนำสถานะ received ราคา None |
| ✅ | PATCH | `/api/admin/cases/{cid}` | 200 | 200 | → received |
| ✅ | PATCH | `/api/admin/cases/{cid}` | 200 | 200 | → checking |
| ✅ | PATCH | `/api/admin/cases/{cid}` | 200 | 200 | → awaiting_approval |
| ✅ | PATCH | `/api/admin/cases/{cid}` | 409 | 409 | ข้ามขั้นตอนถูกปฏิเสธ |
| ✅ | GET | `/api/admin/insights` | 200 | 200 | คำถามวันนี้ 895 |
| ✅ | GET | `/api/admin/metrics` | 200 | 200 |  |
| ✅ | POST | `/api/member/cases/{cid}/quote-decision` | 200 | 200 | อนุมัติใบเสนอราคา |
| ✅ | POST | `/api/member/cases/{cid}/checkout` | 200 | 200 / 503 | ได้ลิงก์ Stripe Checkout |
| ✅ | GET | `/api/member/payments/confirm` | 404 | 404 | รหัสที่ไม่มีอยู่ถูกปฏิเสธ |
| ✅ | POST | `/api/stripe/webhook` | 400 | 400 / 503 | ลายเซ็นไม่ถูกต้องถูกปฏิเสธ |
| ✅ | GET | `/api/member/cases` | 401 | 401 | ไม่เข้าสู่ระบบ → 401 |
| ✅ | GET | `/api/admin/cases` | 403 | 403 | สมาชิกเรียก API ผู้ดูแล → 403 |
| ✅ | GET | `/api/member/cases/{cid}` | 404 | 404 | เคสของคนอื่น → 404 |
