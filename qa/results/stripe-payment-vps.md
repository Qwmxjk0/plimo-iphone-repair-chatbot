# ทดสอบชำระเงินจริงผ่าน Stripe (โหมดทดสอบ) — 2026-10-15 (เวลาไทย)

เป้าหมาย: `https://203-156-66-86.sslip.io` · บัญชี Stripe โหมดทดสอบ (`sk_test_`, `livemode: false`) · บัตรทดสอบ 4242 4242 4242 4242

**ผล: ผ่าน** ลูกค้าจ่ายผ่านหน้า Stripe Checkout แล้วระบบบันทึกการชำระในเคส และ Stripe ส่ง webhook ถึงเซิร์ฟเวอร์สำเร็จทุก event

| ขั้น | ผล |
|---|---|
| เคส PLM-00034 · iPhone 13 · ใบเสนอ #21 3,200 บาท | สมาชิกอนุมัติแล้ว → ปุ่ม "ชำระเงิน" ใช้ได้ (`can_pay: true`) |
| `POST /api/member/cases/34/checkout` | 200 · ได้ลิงก์ `checkout.stripe.com` · ยอดจากฐานข้อมูล ไม่ใช่จากหน้าเว็บ |
| ลูกค้ากรอกบัตรทดสอบในหน้า Stripe (22:13 น.) | จ่ายสำเร็จ |
| ตาราง `payments` | `status: paid` · 320000 สตางค์ (3,200.00 บาท) · `thb` |
| ไทม์ไลน์เคส | "ชำระเงินแล้ว 3,200.00 บาท (Stripe โหมดทดสอบ · ใบเสนอ #21)" |
| Event `checkout.session.completed` (22:13:03 น.) | `pending_webhooks: 0` = ส่งถึง `/api/stripe/webhook` และได้รับคำตอบสำเร็จ |
| Event `checkout.session.expired` (22:00:00 น.) ของลิงก์ที่สร้างไว้ก่อนแล้วไม่ได้จ่าย | `pending_webhooks: 0` · รายการนั้นเปลี่ยนเป็น `expired` เอง |
| Webhook ปลอม (ไม่มีลายเซ็นที่ถูกต้อง) | 400 ปฏิเสธ ([api-check-vps.md](api-check-vps.md)) |

หมายเหตุ: ข้อมูลจาก Stripe อ่านด้วย Events API (อ่านอย่างเดียว) ไม่มีการพิมพ์ key หรือ signing secret ลงไฟล์ใด
