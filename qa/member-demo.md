# สมาชิกและเคส — local demo

เปิด http://127.0.0.1:8081/ แล้วกดสมาชิก / เข้าสู่ระบบ

| บทบาท | Username | Password |
|---|---|---|
| สมาชิกสาธิต | demo_user | PlimoMemberDemo2026! |
| Admin สาธิต | demo_admin | PlimoAdminDemo2026! |

บัญชีเหล่านี้สร้างตามคำขอสำหรับ local demo ไม่ใช่บัญชีใช้งานจริง มีประวัติแชทตัวอย่าง 3 บทสนทนา และเคสตัวอย่าง 8 เคสที่กระจายหลายสถานะ ข้อความที่ seed ระบุว่าเป็นประวัติตัวอย่าง ไม่ใช่ผลทดสอบ AI จริง

หน้า Admin: http://127.0.0.1:8081/admin.html ต้องเข้าสู่ระบบด้วยบทบาท admin ก่อน API ตรวจสิทธิ์แยกจาก UI

สมาชิกเปิดประวัติของตัวเอง ส่งเคสจากบทสนทนาหรือกรอกใหม่ และดู timeline ได้ Admin ดูเฉพาะแชทที่แนบกับเคส นับเคสตามสถานะ และอัปเดตตามลำดับพร้อมหมายเหตุ เก็บผู้แก้ไขและเวลา

SQLite อยู่ใน Docker volume member-data แยกจาก Redis และ LightRAG ข้อความเก็บย้อนหลังได้เมื่อ Redis หมดอายุ ภาพต้นฉบับไม่เก็บถาวร ไม่มีการ ingest ข้อมูลส่วนตัวเข้า RAG

Seed อีกครั้งได้ด้วย `docker compose exec api python seed_demo.py` จะไม่สร้างซ้ำหรือเขียนทับข้อมูลเดิม

ระบบสมาชิกและเคสใช้ backend Docker local ส่วน chatgpt.site เป็น static preview แสดงลิงก์ไป local เมื่อ backend ไม่พร้อม

[Flow ใหม่ PNG](diagrams/stack-flow.png) / [Flow สมาชิกและเคส Mermaid](diagrams/member-case-flow.md)
