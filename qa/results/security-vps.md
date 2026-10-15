# ผลตรวจความปลอดภัย (OWASP Top 10:2025) — 2026-10-15 15:17

เป้าหมาย: `https://203-156-66-86.sslip.io` · **ผ่าน 51/51**

| OWASP | Test | รายการ | ผล | รายละเอียด |
|---|---|---|---|---|
| A01 | W01 | IDOR: อ่านเคสคนอื่น | ผ่าน | HTTP 404 |
| A01 | W01 | IDOR: ตัดสินใบเสนอของคนอื่น | ผ่าน | HTTP 404 |
| A01 | W01 | IDOR: สร้าง checkout ของคนอื่น | ผ่าน | HTTP 503 |
| A01 | W01 | IDOR: บทสนทนาที่ไม่ใช่ของตัวเอง | ผ่าน | HTTP 404 |
| A01 | W02 | สิทธิ์ admin: /api/admin/cases | ผ่าน | member 403, guest 401 |
| A01 | W02 | สิทธิ์ admin: /api/admin/metrics | ผ่าน | member 403, guest 401 |
| A01 | W02 | สิทธิ์ admin: /api/admin/insights | ผ่าน | member 403, guest 401 |
| A01 | W02 | สิทธิ์ admin: /api/admin/cases/14 | ผ่าน | member 403, guest 401 |
| A01 | W02 | สิทธิ์ admin: AI วิเคราะห์เคส | ผ่าน | member 403, guest 401 |
| A01 | W13 | CSRF: POST ข้าม origin ถูกปฏิเสธ | ผ่าน | HTTP 403 |
| A02 | W03 | CSP ไม่มี unsafe-inline/eval และห้าม frame จากเว็บอื่น | ผ่าน | default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis |
| A02 | W03 | header x-content-type-options | ผ่าน | nosniff |
| A02 | W03 | header x-frame-options | ผ่าน | SAMEORIGIN |
| A02 | W03 | header referrer-policy | ผ่าน | strict-origin-when-cross-origin |
| A02 | W03 | header permissions-policy | ผ่าน | camera=(), microphone=(), geolocation=(), payment=() |
| A02 | W03 | ไม่เปิดเผยเวอร์ชัน server | ผ่าน |  |
| A04 | W06 | HSTS บน HTTPS | ผ่าน | max-age=31536000; includeSubDomains |
| A02 | W04 | ไม่ serve /.env | ผ่าน | HTTP 403 |
| A02 | W04 | ไม่ serve /.git/config | ผ่าน | HTTP 403 |
| A02 | W04 | ไม่ serve /backend/main.py | ผ่าน | HTTP 404 |
| A02 | W04 | ไม่ serve /compose.yaml | ผ่าน | HTTP 404 |
| A02 | W04 | ไม่ serve /nginx.conf | ผ่าน | HTTP 404 |
| A02 | W04 | ไม่ serve /docs | ผ่าน | HTTP 404 |
| A02 | W04 | ไม่ serve /openapi.json | ผ่าน | HTTP 404 |
| A02 | W04 | ไม่ serve /redoc | ผ่าน | HTTP 404 |
| A02 | W04 | ไม่ serve /api/docs | ผ่าน | HTTP 404 |
| A02 | W04 | ไม่ serve /api/openapi.json | ผ่าน | HTTP 404 |
| A10 | W12 | error ไม่มี stack trace | ผ่าน | HTTP 404 |
| A03 | W05 | image ทุกตัว pin เวอร์ชัน (ไม่มี latest) | ผ่าน | redis:7.4.11-alpine, ghcr.io/hkuds/lightrag@sha256:5bdbd524931b011df246fe20888d1 |
| A03 | W05 | Dockerfile base image pin เวอร์ชัน | ผ่าน | FROM nginx:1.31.6-alpine |
| A03 | W05 | backend/Dockerfile base image pin เวอร์ชัน | ผ่าน | FROM python:3.12.15-slim |
| A03 | W05 | Python dependency ล็อกเวอร์ชันตรงที่ทดสอบ | ผ่าน | requirements.lock |
| A02 | W05 | API container ไม่รันเป็น root | ผ่าน |  |
| A04 | W06 | cookie สมาชิก HttpOnly + SameSite=Strict | ผ่าน | plimo_member=bh4i1Ex9AMjcaJPdH-_UGEK0NzZhzM_poyslFxQ98mk; Ht |
| A04 | W06 | cookie มี Secure บน HTTPS | ผ่าน | plimo_member=bh4i1Ex9AMjcaJPdH-_UGEK0NzZhzM_poyslFxQ98mk; Ht |
| A07 | W09 | ปฏิเสธรหัสผ่านสั้น | ผ่าน | HTTP 422 |
| A07 | W09 | brute force บัญชีเดียวถูกล็อก | ผ่าน | 401,401,401,401,401,401,401,401,401,429,429 |
| A07 | W09 | บัญชีอื่นจาก IP เดียวกันยังเข้าได้ (NAT ห้องเรียน) | ผ่าน | HTTP 200 |
| A05 | W07 | SQL injection ที่ login | ผ่าน | HTTP 422 |
| A05 | W07 | stored XSS เก็บเป็นข้อความเดิม | ผ่าน | HTTP 200 |
| A05 | W07 | frontend ไม่ใช้ innerHTML/eval กับข้อมูล | ผ่าน |  |
| A06 | W08 | เริ่มซ่อมก่อนลูกค้าอนุมัติราคาไม่ได้ | ผ่าน | HTTP 409 |
| A06 | W08 | อนุมัติใบเสนอเก่าไม่ได้ | ผ่าน | HTTP 409 |
| A06 | W08 | ชำระก่อนอนุมัติไม่ได้ | ผ่าน | HTTP 503 |
| A08 | W10 | webhook ลายเซ็นปลอมถูกปฏิเสธ | ผ่าน | HTTP 503 |
| A10 | W12 | ข้อความยาวเกินถูกปฏิเสธ | ผ่าน |  |
| A10 | W12 | ไฟล์ที่ไม่ใช่ภาพถูกปฏิเสธ | ผ่าน |  |
| A10 | W12 | ภาพใหญ่เกิน 10 MB ถูกปฏิเสธ | ผ่าน |  |
| A10 | W12 | JSON เสียไม่ทำให้ 500 | ผ่าน | HTTP 422 |
| A09 | W11 | ตัวนับ guard/rate/budget ใน admin metrics | ผ่าน | action_done, admin_assist, answer_hit, answer_miss, chats, cost_micro_usd, fast_ |
| LLM06 | K04 | nginx จำกัดคำขอแชทถี่ต่อ IP | ผ่าน | 19x200 7x429 |
