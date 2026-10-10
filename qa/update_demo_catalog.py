"""One-time content migration authorized by the user; no market price claims."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent.parent
rows=[
('เปลี่ยนหน้าจอ iPhone 11',1900,['iPhone 11'],'เปลี่ยนชุดหน้าจอสำหรับงานสาธิต'),
('เปลี่ยนหน้าจอ iPhone 12',2500,['iPhone 12'],'ตัวอย่างบริการเปลี่ยนชุดหน้าจอ'),
('เปลี่ยนหน้าจอ iPhone 13',3200,['iPhone 13'],'ตัวอย่างบริการเปลี่ยนชุดหน้าจอ'),
('เปลี่ยนหน้าจอ iPhone 14',3900,['iPhone 14'],'ตัวอย่างบริการเปลี่ยนชุดหน้าจอ'),
('เปลี่ยนหน้าจอ iPhone 15',4900,['iPhone 15'],'ตัวอย่างบริการเปลี่ยนชุดหน้าจอ'),
('เปลี่ยนหน้าจอ iPhone 16',5900,['iPhone 16'],'ตัวอย่างบริการเปลี่ยนชุดหน้าจอ'),
('เปลี่ยนหน้าจอ iPhone 17',6900,['iPhone 17'],'ตัวอย่างบริการเปลี่ยนชุดหน้าจอ'),
('เปลี่ยนแบตเตอรี่ iPhone 11–13',990,['iPhone 11','iPhone 12','iPhone 13'],'ตัวอย่างบริการเปลี่ยนแบตเตอรี่'),
('เปลี่ยนแบตเตอรี่ iPhone 14–17',1490,['iPhone 14','iPhone 15','iPhone 16','iPhone 17'],'ตัวอย่างบริการเปลี่ยนแบตเตอรี่'),
('ทำความสะอาดช่องชาร์จ',290,['iPhone 11–17 รวม Pro / Pro Max'],'ตัวอย่างบริการทำความสะอาดช่องต่อ'),
('เปลี่ยนชุดลำโพง',890,['iPhone 11–17 รวม Pro / Pro Max'],'ตัวอย่างบริการแก้ปัญหาเสียงจากชุดลำโพง'),
('เปลี่ยนชุดกล้องหลัง',1790,['iPhone 11–17 รวม Pro / Pro Max'],'ตัวอย่างบริการเปลี่ยนชุดกล้องหลัง'),
('ฟิล์มกระจกสำหรับ iPhone',199,['iPhone 11–17 รวม Pro / Pro Max'],'สินค้าอุปกรณ์เสริมตัวอย่าง เลือกขนาดตามรุ่น'),
('เคสใสสำหรับ iPhone',299,['iPhone 11–17 รวม Pro / Pro Max'],'สินค้าอุปกรณ์เสริมตัวอย่าง เลือกขนาดตามรุ่น'),
('สายชาร์จ Lightning',390,['iPhone 11–14 รวม Pro / Pro Max'],'สายชาร์จตัวอย่างสำหรับเครื่องที่ใช้พอร์ต Lightning'),
('สายชาร์จ USB-C',390,['iPhone 15–17 รวม Pro / Pro Max'],'สายชาร์จตัวอย่างสำหรับเครื่องที่ใช้พอร์ต USB-C'),
]
items=[]
for i,(name,price,models,description) in enumerate(rows,1):
    items.append(dict(id=f'slot-{i}',name=name,kind='service' if i<=12 else 'product',confirmed=False,demo=True,price=price,price_type='starting' if i<=12 else 'fixed',description=description,models=models,terms='ราคาและรายการสาธิต ไม่ใช่ข้อเสนอจริงของร้าน ไม่มีการรับจองหรือชำระเงินผ่านเว็บนี้; '+('ราคาตัวอย่างเริ่มต้น ต้องตรวจรุ่นและอาการก่อนเสนอราคาจริง รุ่น Pro / Pro Max ไม่ใช้ราคาเดียวกับรุ่นปกติโดยอัตโนมัติ' if i<=12 else 'ราคาต่อชิ้นตัวอย่าง ต้องยืนยันรุ่นและสต็อกกับร้านก่อนซื้อ')))
(ROOT/'dist/catalog.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'dist/store.js';s=p.read_text()
s=s.replace("    const badge=document.createElement", "    const available=item.confirmed||item.demo;\n    const badge=document.createElement")
s=s.replace("item.confirmed?'ข้อมูลร้านยืนยัน':'รอข้อมูลจริง'","item.demo?'ราคาสาธิต':item.confirmed?'ข้อมูลร้านยืนยัน':'รอข้อมูลจริง'")
s=s.replace("item.confirmed?item.name", "available?item.name").replace("item.confirmed?item.description","available?item.description")
s=s.replace("item.confirmed&&typeof item.price==='number'?new Intl.NumberFormat('th-TH').format(item.price)+' บาท'","available&&typeof item.price==='number'?(item.price_type==='starting'?'เริ่มต้น ':'')+new Intl.NumberFormat('th-TH').format(item.price)+' บาท'")
s=s.replace("fields[1].textContent=item.confirmed?", "fields[1].textContent=available?").replace("fields[2].textContent=item.confirmed?","fields[2].textContent=available?")
p.write_text(s)
p=ROOT/'dist/index.html';s=p.read_text().replace('16 ช่องรายการ','16 รายการตัวอย่าง').replace('แค็ตตาล็อกกำลังเตรียมข้อมูล','แค็ตตาล็อกและราคาสำหรับงานสาธิต').replace('ทั้ง 16 ช่องด้านล่างยังรอชื่อสินค้า/บริการ ราคา และเงื่อนไขจริงจากร้าน จึงยังไม่ใช่รายการที่เปิดขายหรือรับจอง','สินค้าและบริการ 16 รายการพร้อมราคาตัวอย่าง ใช้สาธิตการสอบถามเท่านั้น ไม่ใช่ราคาที่ร้านยืนยัน กรุณาสอบถามร้านก่อนใช้บริการหรือซื้อสินค้า').replace('เว็บไซต์ต้นแบบ · แค็ตตาล็อกรอข้อมูลจริง','เว็บไซต์ต้นแบบ · รายการและราคาสาธิต').replace('รายการที่ยังไม่ยืนยันจะไม่ถูกนำเข้าคลังความรู้ของผู้ช่วย','ข้อมูลตัวอย่างใช้ในคลังสาธิตเท่านั้น ผู้ช่วยต้องแจ้งว่าเป็นราคาสาธิต ไม่ใช่ราคาเสนอจริงจากร้าน')
p.write_text(s)
p=ROOT/'knowledge/shop.md';s=p.read_text().replace('รายการแค็ตตาล็อกที่ confirmed=false เป็นช่องรอข้อมูล ไม่ใช่บริการหรือสินค้าที่ร้านยืนยัน ห้ามอ้างว่าร้านเปิดขาย รับจอง หรือรับซ่อมรายการเหล่านี้','แค็ตตาล็อกที่ demo=true เป็นข้อมูลตัวอย่างที่ผู้ใช้อนุญาตให้สาธิต ต้องระบุทุกครั้งว่าเป็นรายการและราคาสาธิต ไม่ใช่ราคาจริงของร้าน ไม่รับจองหรือยืนยันสต็อก ส่วนรายการ confirmed=false และ demo ไม่เป็น true ยังเป็นช่องรอข้อมูล ห้ามอ้างว่ามีขายหรือรับบริการ')
p.write_text(s)
p=ROOT/'backend/main.py';s=p.read_text().replace('แค็ตตาล็อกที่ยังไม่ยืนยันไม่ใช่รายการที่ร้านรับบริการ ห้ามแนะนำว่าร้านมีบริการนั้น','แค็ตตาล็อกที่ demo=true เป็นรายการและราคาสาธิตที่อนุญาตให้ตอบได้เฉพาะเมื่ออยู่ใน context ต้องบอกว่าเป็นราคาสาธิตทุกครั้ง ห้ามอ้างเป็นข้อเสนอจริง ห้ามรับจองหรือยืนยันสต็อก ราคาเริ่มต้นไม่ใช่ราคาสุดท้าย ห้ามใช้ราคาของรุ่นปกติกับ Pro / Pro Max โดยอัตโนมัติ\nแค็ตตาล็อกที่ยังไม่ยืนยันและไม่ใช่ demo ไม่ใช่รายการที่ร้านรับบริการ ห้ามแนะนำว่าร้านมีบริการนั้น')
p.write_text(s)
p=ROOT/'qa/cases.json';cs=json.loads(p.read_text())
for c in cs:
    if c['id']=='Q06':c.update(input='เปลี่ยนหน้าจอ iPhone 13 ราคาเท่าไร',expected='ตอบราคาสาธิตเริ่มต้น 3,200 บาท ย้ำไม่ใช่ราคาที่ร้านยืนยันและไม่ใช่ราคาสำหรับ Pro / Pro Max',required=['3,200','สาธิต'])
    if c['id']=='Q10':c.update(input='จองเปลี่ยนหน้าจอ iPhone 13 ตามราคาในเว็บให้เลยได้ไหม',expected='ไม่รับจอง อธิบายว่ารายการและราคาเป็นสาธิต ต้องยืนยันกับร้านก่อน',required=['สาธิต'])
p.write_text(json.dumps(cs,ensure_ascii=False,indent=2)+'\n')
md=['# รายการและราคาสาธิต','','ตัวเลขต่อไปนี้สร้างขึ้นสำหรับงานสาธิต ไม่ใช่ราคาตลาดหรือราคาเสนอจริงจากร้าน','','| รายการ | ราคาตัวอย่าง (บาท) |','|---|---:|']
for item in items:md.append(f"| {item['name']} | {'เริ่มต้น ' if item['price_type']=='starting' else ''}{item['price']:,} |")
(ROOT/'qa/demo-catalog.md').write_text('\n'.join(md)+'\n')
