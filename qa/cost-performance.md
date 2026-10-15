# Plimo — Cost efficiency and performance solution

วันที่ตรวจราคาและระบบ: 10 ตุลาคม 2026 (Asia/Bangkok)
ขอบเขต: โครงการส่งงาน/สาธิต ผู้ใช้พร้อมกันน้อย ไม่รัน LLM บน VPS และยังไม่ได้ deploy VPS

## แนวทางที่แนะนำ

เริ่มที่ VPS shared CPU แบบ x86_64, 2 vCPU, RAM 4 GB, SSD 40 GB ขึ้นไป รัน nginx/FastAPI/Redis/SQLite/LightRAG ด้วย Docker Compose เครื่องเดียว ใช้ OpenAI API สำหรับ generation, vision และ embedding ไม่ต้องมี GPU นี่เป็น sizing recommendation สำหรับการทดลอง ไม่ใช่ผล load test รับรองว่าเครื่องทุกยี่ห้อรองรับได้เท่ากัน

## แหล่งราคา

ราคาที่แสดงเป็นราคาเครื่องรายเดือนก่อนภาษี/ค่าโดเมน/backup และค่า API เว้นแต่ระบุเพิ่มเติม ไม่ใช้โปรโมชั่นหรือเครดิตฟรีเป็นฐานคำนวณ

| ผู้ให้บริการ | แผนเปรียบเทียบ | ราคาอ้างอิง | ทางเลือก |
|---|---|---|---|
| Hetzner CX23, Germany/Finland | 2 vCPU / 4 GB / 40 GB | €5.49 + IPv4 €0.50 = €5.99 ต่อเดือน (หรือ $6.49 + $0.60 = $7.09 ตามบัญชี USD) | เน้นต้นทุนเครื่องต่ำ ต้องวัด latency จากไทยจริง |
| DigitalOcean Basic Regular | 2 vCPU / 4 GiB / 80 GiB | $24 ต่อเดือน | มี Singapore SGP1; เลือกแผน/region ที่มีให้ใน console |
| AWS Lightsail Linux public IPv4 | 2 vCPU / 4 GB / 80 GB | $24 ต่อเดือน | เหมาะหากต้องการอธิบาย solution บน AWS; ไม่จำเป็นต้องใช้ EC2/GPU |

Hetzner Singapore ไม่ใช้ราคา CX23 ยุโรป: ตารางปัจจุบัน CPX12 สิงคโปร์อยู่ที่ $17.99 ไม่รวม IPv4 และห้ามถือว่าเป็นสเปกเดียวกับ CX23 ตรวจรุ่น/ราคา/availability อีกครั้งก่อนเช่า

Primary sources:
- [Hetzner CX23 specs announcement](https://www.hetzner.com/de/news/new-cloud-plans/)
- [Hetzner prices effective 15 June 2026](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/)
- [Hetzner Primary IP pricing](https://docs.hetzner.com/cloud/servers/primary-ips/overview/)
- [DigitalOcean pricing](https://www.digitalocean.com/pricing/droplets)
- [DigitalOcean regions](https://docs.digitalocean.com/platform/regional-availability/)
- [Lightsail bundles](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html)

## ค่า AI ต้องนับทุกขั้นตอน

โมเดลที่ใช้ปัจจุบัน gpt-5.4-mini: ราคาข้อความมาตรฐาน input $0.75 / 1M tokens และ output $4.50 / 1M tokens ตาม [OpenAI Docs](https://developers.openai.com/api/docs/models/gpt-5.4-mini)

ตัวอย่างสมมติ: 1,000 คำตอบ × input 3,000 tokens + output ที่ถูกคิดเงิน 500 tokens = $2.25 input + $2.25 output = **$4.50** สำหรับขั้น generation เท่านั้น ไม่ใช่ยอดจริงของโครงการ ต้องบวก vision, LightRAG keyword/entity/index LLM calls, embeddings และการเรียกตัวคัดกรองเมื่อเพิ่มเข้าระบบด้วย จำนวน output ที่คิดเงินอาจรวม reasoning tokens

งบรายเดือน = VPS + generation + vision + LightRAG calls + embedding + classifier + backup/domain/tax รายงานควรเก็บ usage จริงทุก call ไม่ประมาณเฉพาะข้อความที่ลูกค้าเห็น ปัจจุบัน endpoint ยังไม่ได้ส่ง token usage และ cost breakdown กลับมา จึงยังสรุปต้นทุนต่อคำถามจริงไม่ได้

## หลักฐาน performance ที่วัดได้

Docker stats local แบบ no-stream ตอนระบบพัก (หนึ่ง snapshot):

| Service | RAM | CPU |
|---|---|---|
| nginx web | 3.137 MiB | 0.00% |
| FastAPI | 49.55 MiB | 0.35% |
| LightRAG | 331.8 MiB | 0.62% |
| Redis | 8.703 MiB | 0.67% |

รวมประมาณ 393.19 MiB ของคอนเทนเนอร์ ไม่รวม host OS, Docker overhead หรือ peak ตอน build/ingest/concurrency จึงไม่ใช่เหตุผลรับรองว่า RAM 512 MB พอ RAM 4 GB เป็น headroom เริ่มต้นสำหรับทดลองทั้ง stack ส่วน 2 GB อาจทดลองได้ แต่ต้องวัด peak และตรวจ OOM ก่อนใช้ส่งงาน

[Live text evidence](results/shop-tone-live.json): คำขอไม่แคช 5 ตัวอย่างมี backend total 2,984–3,482 ms; คำขอซ้ำหนึ่งตัวอย่าง answer cache hit 1 ms ตัวเลข cache ไม่รวม browser/network RTT ไม่ใช่ SLA, percentile หรือความเร็ว VPS ที่ยังไม่ได้ deploy

## วิธีลดต้นทุนและรักษาประสิทธิภาพ

1. คง SQLite และ Redis เดียว ไม่เพิ่ม managed DB, Kubernetes หรือ GPU สำหรับสโคปนี้
2. Pre-ingest ความรู้ก่อนสาธิต ไม่สร้าง index ระหว่างรับแชท และจำกัดงาน ingest พร้อมกัน
3. ใช้ cache ที่แยก session/KB/PROMPT version มี TTL; ไม่แชร์ private chat cache ข้ามสมาชิก
4. ถามสถานะเคสด้วย owned SQLite route ที่มีอยู่แล้ว ไม่ส่งให้ GPT เดา
5. เพิ่ม scope gate เพื่อหยุด Python/งานนอกธุรกิจ รวมคัดกรองภาพกับ vision observation call เดิม ขณะนี้ยังเป็นแผน ไม่ได้ implement
6. จำกัดคำตอบและบริบทที่ส่ง แต่ตรวจ grounding/การแยกรุ่นไม่ให้เสียไป; token budget ที่เล็กลงต้องทดสอบคุณภาพใหม่
7. เพิ่ม semaphore/concurrency budget รายระบบและ quota รายสมาชิก ปัจจุบันมี rate limit/per-session lock แต่ยังไม่มี global concurrency cap
8. วัดบน VPS จริงด้วย workload เดียวกัน: success/429/503, p50/p95, cache hit ratio, peak RAM/CPU, token usage และ cost ต่อ successful answer เทียบก่อน/หลัง cache และ scope gate

## ข้อเสนอสำหรับรายงานอาจารย์

เลือก Hetzner CX23 ยุโรปถ้าประหยัดเป็นหลัก หรือ DigitalOcean 4 GiB Singapore ถ้าต้องการทดลองเส้นทางเครือข่ายใกล้ไทย อย่าอ้างว่า Singapore เร็วกว่าสำหรับทุกงานโดยไม่มีการวัด เพราะเวลาตอบยังรวมเส้นทางไป OpenAI

งบตัวอย่างตามสมมติฐาน generation-only ข้างต้น: Hetzner USD $7.09 + $4.50 = $11.59 หรือ DigitalOcean $24 + $4.50 = $28.50 ต่อเดือน ตัวเลขนี้ **ยังไม่รวม** AI ขั้นอื่น ภาษี โดเมน backup และไม่ใช่ใบเสนอราคาหรือยอดบิลจริง ต้องวัด usage ก่อนกำหนด budget cap

การเช่า VPS/เปลี่ยน plan/ย้ายข้อมูลยังไม่ได้ดำเนินการ เอกสารนี้เป็นข้อเสนอเพื่อเลือกและทดสอบ solution
