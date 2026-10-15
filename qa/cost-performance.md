# Plimo — Cost efficiency และ performance

ปรับปรุง: 15 ตุลาคม 2026 (Asia/Bangkok) · ตัวเลขทุกตัวในหัวข้อ "ผลวัดจริง" มาจากการรันบน Docker local ของรอบนี้ ไฟล์ผลอยู่ใน `qa/results/`

## ผลวัดจริง

| ตัวชี้วัด | ผล | ที่มา |
|---|---|---|
| คำถามใหม่ทั้งหมด (router + retrieval + generation ไม่มี cache เลย) | p50 3,300 ms, p95 4,151 ms; แยกขั้น p50: router 1,571 · retrieval เสร็จก่อน router · generation 1,685 | `results/load-latest.md` |
| คำตอบที่ต้องสร้างใหม่ใน eval (บางข้อ router เคยเห็น) | p50 1,699 ms, p95 4,056 ms (62 คำตอบ) | `results/eval-latest.md` |
| LightRAG retrieval | naive p50 ~400 ms (mix ~520–1,600 ms) | `results/retrieval-latest.md` |
| ก่อนปรับ (เช้านี้, 72 คำถาม) | p50 3,090 ms, p95 5,500 ms | `results/eval-20261015-0808.json` |
| คำถามใน cache | backend p50 2 ms, p95 3 ms; client ผ่าน HTTP 20 ผู้ใช้พร้อมกัน p50 41 ms, p95 96 ms, p99 143 ms, 376 คำขอ/วินาที, error 0/240 | `results/eval-latest.md`, `results/load-latest.md` |
| Hit rate คำถามซ้ำ (session ใหม่) | 72/79 = 91% — ที่ไม่ hit คือเคส/การชำระ/guard ซึ่งตั้งใจไม่ cache | `results/eval-latest.md` |
| Hit rate คำถามต่างสำนวน | 8/8 (เช้านี้ 3/8 ก่อนให้ router ใช้สำนวนมาตรฐาน) | `results/eval-latest.md` |
| Single-flight | 20 คำขอเหมือนกันพร้อมกัน → OpenAI 2 calls, LightRAG 1 call, คำตอบเดียวกันทั้ง 20 | `results/load-latest.md` |
| ค่า AI ต่อคำตอบใหม่ | $0.00277 (router + คำตอบ, วัดจาก 5 คำถามใหม่, input cached 67%); ก่อนใช้ prompt caching ≈ $0.0034 | ตัวนับ `cost_micro_usd` |
| Prompt cache ทั้งรอบ eval | 78.5% ของ input tokens | `results/eval-latest.md` |

ตัวอย่างงบรายเดือน (สมมติ ไม่ใช่ใบแจ้งหนี้): 1,000 ข้อความ/วัน ถ้า 40% ต้องสร้างคำตอบใหม่ → 400 × $0.0028 ≈ $1.1/วัน ≈ $34/เดือน; ถ้า 20% → ≈ $17/เดือน บวก VPS $7–24/เดือน สัดส่วนคำถามซ้ำของลูกค้าจริงต้องวัดหลังเปิดใช้งาน ระบบตั้งเพดานไว้ที่ `DAILY_BUDGET_USD` (ค่าเริ่มต้น $5/วัน)

## สิ่งที่ทำเพื่อลดต้นทุนและเพิ่มความเร็ว

| มาตรการ | ผล |
|---|---|
| Cache ร่วมข้ามผู้ใช้ 4 ชั้น (fast / router / answer / retrieval) + normalize คำลงท้าย ชื่อรุ่น เลขไทย | คำถามซ้ำตอบในหลักมิลลิวินาทีและไม่เสียค่า API |
| Router เขียนคำถามเป็นสำนวนมาตรฐาน | คำถามต่างสำนวนเข้า cache เดียวกันได้มากขึ้น |
| Single-flight ทุกชั้น | คำถามเดียวกันพร้อมกันหลายคนเรียก OpenAI/LightRAG ครั้งเดียว |
| คำสั่งคงที่ + ข้อมูลร้านทั้งหมดอยู่ส่วนหน้าของ prompt | ได้ OpenAI prompt caching (input ส่วนที่ cache คิด 10% ของราคาปกติ) |
| นอกขอบเขต/ไม่ปลอดภัย/เลขบัตร ตอบด้วยข้อความคงที่ | ไม่เสียค่า generation กับคำถามที่ไม่ใช่งานร้าน |
| ถามสถานะเคสอ่าน SQLite ตรง | ไม่ใช้ LLM ในงานที่ตอบด้วยข้อมูลจริงได้ |
| HTTP client ตัวเดียวแบบ keep-alive | ไม่ต้องเปิด TLS ใหม่ทุกคำขอ |
| คำถามแรก: ค้น LightRAG คู่ขนานกับ router | ซ่อนเวลาค้นไว้ใต้เวลาของ router |
| เพดานค่าใช้จ่ายรายวัน (USD) + quota ต่อสมาชิก/session/IP | บิลมีขีดจำกัด เกินแล้วยังตอบจาก cache และ DB ได้ |
| ภาพหน้าเว็บเป็น WebP + lazy loading, gzip, cache header | หน้าแรกจาก ~4.5 MB เหลือ ~97 KB |
| LightRAG แบบ naive + chunk สั้นเฉพาะรายการ | retrieval แม่นขึ้น (hit@1 31% → 88%) และไม่ต้องเรียก LLM สกัด keyword ทุกคำถามใหม่ |

ทางเลือกที่วัดแล้วไม่ใช้: `gpt-5.4-nano` สำหรับ router ไม่เร็วกว่า mini (median 1,391 vs 1,202 ms เพราะเวลาส่วนใหญ่เป็น network/first token) และ streaming คำตอบไม่ใช้ เพราะต้องตรวจตัวเลขราคาทั้งคำตอบก่อนแสดง (เลือกความถูกต้องก่อนความรู้สึกเร็ว)

## VPS

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

## ราคา AI

`gpt-5.4-mini`: input $0.75, cached input $0.075, output $4.50 ต่อ 1M tokens ตาม [OpenAI](https://developers.openai.com/api/docs/models/gpt-5.4-mini) (ตรวจ 15 ตุลาคม 2026) ระบบนับ token จริงจาก `usage` ทุก call (router, vision, คำตอบ) ดูได้ที่ `/api/admin/metrics` และหน้า Admin ค่า embedding/การสร้างคลังของ LightRAG ไม่ได้นับรวมในตัวนับนี้ (เกิดตอน ingest และตอนค้นคำถามใหม่)

## RAM ของคอนเทนเนอร์ (Docker local ขณะใช้งานเบา)

| Service | RAM |
|---|---|
| FastAPI | 61 MiB |
| nginx | 4 MiB |
| LightRAG | 338 MiB |
| Redis | 15 MiB (จำกัดสูงสุด 256 MB) |

รวมประมาณ 420 MiB ไม่รวม OS และช่วง build จึงแนะนำ 2 vCPU / 4 GB เป็น headroom ตาราง VPS ด้านบนเป็นราคาที่ตรวจเมื่อ 10 ตุลาคม 2026 ต้องตรวจซ้ำก่อนเช่า
