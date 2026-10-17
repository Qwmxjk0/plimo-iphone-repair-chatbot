// Builds the course submission document (Deliverable 2) from real VPS results.
// node build.js <project dir> <thumbs dir> <out.docx>
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, Footer, AlignmentType,
  HeadingLevel, WidthType, ShadingType, BorderStyle, LevelFormat, PageNumber, PageBreak, ExternalHyperlink,
  VerticalAlign, TableLayoutType,
} = require('docx');

const [PROJECT, THUMBS, OUT] = process.argv.slice(2);
const data = JSON.parse(fs.readFileSync(path.join(PROJECT, 'docs/submission/data.json'), 'utf8'));
const FONT = { ascii: 'Sarabun', hAnsi: 'Sarabun', cs: 'Sarabun', eastAsia: 'Sarabun' };
const W = 9026; // A4 width minus 1" margins, in DXA
const BLUE = '0A5BD3', GREY = '5F6368', LINE = 'D0D4DA', HEAD = 'EEF2F7';

const run = (text, o = {}) => new TextRun({ text, font: FONT, size: o.size || 22, sizeComplexScript: o.size || 22, bold: o.bold, color: o.color, italics: o.italics });
const p = (text, o = {}) => new Paragraph({ children: Array.isArray(text) ? text : [run(text, o)], spacing: { after: o.after ?? 120, line: 300 }, alignment: o.align });
const h1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [run(text, { size: 32, bold: true, color: '1D1D1F' })], spacing: { before: 240, after: 160 } });
const h2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [run(text, { size: 26, bold: true, color: BLUE })], spacing: { before: 200, after: 100 } });
const bullet = (text) => new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: Array.isArray(text) ? text : [run(text)], spacing: { after: 60, line: 290 } });
const numbered = (text) => new Paragraph({ numbering: { reference: 'steps', level: 0 }, children: [run(text)], spacing: { after: 60, line: 290 } });
const link = (url) => new ExternalHyperlink({ link: url, children: [new TextRun({ text: url, style: 'Hyperlink', font: FONT, size: 22, sizeComplexScript: 22 })] });
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });
const clip = (s, n) => { s = String(s).replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n).trimEnd() + '…' : s; };
const secs = (ms) => (ms / 1000).toFixed(2);

const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
const borders = { top: border, bottom: border, left: border, right: border };
function cell(content, width, o = {}) {
  const children = (Array.isArray(content) ? content : [content]).map((c) =>
    c instanceof Paragraph ? c : new Paragraph({ children: [c instanceof TextRun || c instanceof ImageRun ? c : run(String(c), { size: o.size || 20, bold: o.bold, color: o.color })], spacing: { after: 0, line: 270 }, alignment: o.align }));
  return new TableCell({ children, width: { size: width, type: WidthType.DXA }, borders, verticalAlign: o.valign || VerticalAlign.TOP,
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: 'auto' } : undefined, margins: { top: 70, bottom: 70, left: 100, right: 100 } });
}
function table(widths, header, rows, o = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const head = new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, widths[i], { bold: true, fill: HEAD, size: 20 })) });
  const body = rows.map((r) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, widths[i], { size: o.size || 20, align: o.align?.[i] })) }));
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths, layout: TableLayoutType.FIXED, rows: [head, ...body] });
}
const kv = (rows) => new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: [2600, W - 2600], layout: TableLayoutType.FIXED,
  rows: rows.map(([k, v]) => new TableRow({ children: [cell(k, 2600, { bold: true, fill: HEAD }), cell(v, W - 2600, { size: 21 })] })) });
const verdict = (ok) => run(ok ? 'ผ่าน' : 'ไม่ผ่าน', { size: 20, bold: true, color: ok ? '1E7E34' : 'B42318' });
const image = (file, width, height) => new ImageRun({ type: 'png', data: fs.readFileSync(file), transformation: { width, height } });

// ---------- content ----------
const s = data.summary;
const children = [];

// Cover
children.push(
  new Paragraph({ spacing: { before: 2600, after: 120 }, children: [run('Plimo iPhone Repair', { size: 56, bold: true, color: '1D1D1F' })] }),
  p('แชทบอทผู้ช่วยร้านซ่อม iPhone ที่ใช้ LLM เป็นแกนหลัก ตอบลูกค้าและช่วยงานแอดมิน', { size: 28, color: GREY, after: 600 }),
  p('ส่งมอบ 2: เอกสารการพัฒนาโครงงานและผลการทดสอบ', { size: 26, bold: true, color: BLUE, after: 400 }),
  kv([
    ['ผู้พัฒนา', 'กฤตนัย กัปตพล'],
    ['เว็บไซต์ที่ใช้งานจริง', 'https://203-156-66-86.sslip.io'],
    ['ซอร์สโค้ด', 'https://github.com/Qwmxjk0/plimo-iphone-repair-chatbot'],
    ['วันที่จัดทำ', '16 ตุลาคม 2569'],
  ]),
  pageBreak(),
);

// 1. Project and developer
children.push(h1('1. ชื่อโครงงานและผู้พัฒนา'),
  kv([
    ['ชื่อโครงงาน', 'Plimo iPhone Repair'],
    ['คำอธิบาย', 'แชทบอทภาษาไทยสำหรับร้านซ่อม iPhone ที่ใช้ LLM เป็นแกนกลาง ทำ 2 หน้าที่ คือ (1) ตอบลูกค้าเรื่องราคา บริการ อาการเสีย รูปภาพ เปิดและติดตามเคสซ่อม อนุมัติราคา และชำระเงิน (2) ช่วยแอดมินสรุปเคส แนะนำสถานะและราคาจากแค็ตตาล็อก และสรุปคำถามลูกค้าประจำวัน'],
    ['ผู้พัฒนา', 'กฤตนัย กัปตพล'],
    ['เว็บไซต์', 'https://203-156-66-86.sslip.io'],
    ['ซอร์สโค้ด', 'https://github.com/Qwmxjk0/plimo-iphone-repair-chatbot'],
  ]));

// 1.1 Test accounts for the reviewer (read from the seed file, never typed by hand)
const SEED = fs.readFileSync(path.join(PROJECT, 'backend/seed_demo.py'), 'utf8');
const seedPw = (u) => (SEED.match(new RegExp("\\('" + u + "','([^']+)'")) || [])[1] || '(ดู qa/member-demo.md)';
children.push(h2('1.1 บัญชีสำหรับทดสอบ'),
  table([1400, 2450, 2950, 2226], ['บทบาท', 'ชื่อผู้ใช้', 'รหัสผ่าน', 'เข้าที่'], [
    ['ลูกค้า (สมาชิก)', 'demo_user', seedPw('demo_user'), 'https://203-156-66-86.sslip.io → ปุ่ม "เข้าสู่ระบบ" มุมขวาบน'],
    ['แอดมิน', 'demo_admin', seedPw('demo_admin'), 'https://203-156-66-86.sslip.io/admin.html'],
    ['บัตรทดสอบ Stripe', '4242 4242 4242 4242', 'วันหมดอายุในอนาคต · CVC ใดก็ได้', 'ปุ่ม "ชำระเงิน" ในบัญชี (ไม่มีการตัดเงินจริง)'],
  ]),
  p('ทดลองแชทได้โดยไม่ต้องเข้าสู่ระบบ ส่วนการเปิดเคส ติดตามเคส อนุมัติราคา และชำระเงิน ต้องเข้าสู่ระบบด้วยบัญชีลูกค้า ข้อมูลในระบบเป็นข้อมูลทดสอบทั้งหมด', { size: 20, color: GREY }),
);

// 2. Business
children.push(h1('2. ข้อมูลของธุรกิจ'), h2('2.1 รายละเอียดธุรกิจ'),
  p('Plimo iPhone Repair เป็นร้านซ่อม iPhone ที่รับเฉพาะรุ่น iPhone 11–17 (รวม Pro / Pro Max) เปิดทุกวัน 10:00–20:00 น. ปิดวันพุธ และตรวจเช็คเครื่องฟรี จุดเด่นของร้านคือความโปร่งใส: แจ้งราคาประเมินเบื้องต้นก่อน ตรวจเครื่องแล้วส่งใบเสนอราคาให้ลูกค้าอนุมัติทุกครั้งก่อนเริ่มงานที่มีค่าใช้จ่าย และให้ลูกค้าติดตามงานซ่อมออนไลน์ด้วยเลขเคส PLM'),
  p('ร้านต้องตอบคำถามซ้ำจำนวนมาก (ราคา เวลาเปิด อาการเสีย) และติดตามหลายเคสพร้อมกัน โครงงานนี้จึงสร้างผู้ช่วยแชทที่ตอบจากข้อมูลร้านจริงตลอดเวลา และช่วยแอดมินจัดการเคส โดยยึดหลัก "AI เสนอ ระบบยืนยัน": ตัวเลขราคา สถานะเคส และการชำระเงินมาจากฐานข้อมูลเสมอ'),
  h2('2.2 กลุ่มเป้าหมาย'),
  bullet('ผู้ใช้ iPhone 11–17 ที่เครื่องมีปัญหา เช่น จอแตก แบตเสื่อม ชาร์จไม่เข้า ลำโพงหรือกล้องเสีย และอยากรู้ราคาประเมินก่อนเดินทางมาร้าน'),
  bullet('ลูกค้าที่ต้องการความโปร่งใส: ตรวจเช็คฟรี อนุมัติราคาก่อนซ่อม และติดตามสถานะงานซ่อมได้เองตลอดเวลา'),
  bullet('ลูกค้าที่สะดวกสอบถามผ่านแชท รวมถึงนอกเวลาทำการหรือวันพุธที่ร้านปิด และส่งรูปอาการจาก iPhone ได้ทันที'),
  bullet('ผู้ที่ต้องการซื้ออุปกรณ์เสริม: ฟิล์มกระจก เคสใส สายชาร์จ Lightning / USB-C'),
  bullet('ผู้ใช้ภายใน: เจ้าของร้านและพนักงาน ที่ต้องการลดเวลาตอบคำถามซ้ำและใช้ AI ช่วยจัดการเคส'),
  h2('2.3 สินค้าและบริการ (ราคาประเมินเบื้องต้นเริ่มต้น)'),
  table([3300, 1400, 2726, 1600], ['รายการ', 'ประเภท', 'รุ่นที่รองรับ', 'ราคาเริ่มต้น (บาท)'],
    data.catalog.map((i) => [i.name, i.kind === 'service' ? 'บริการซ่อม' : 'อุปกรณ์เสริม', i.models.join(', '), i.price.toLocaleString('en-US')]),
    { align: [null, null, null, AlignmentType.RIGHT] }),
  p('รุ่น Pro / Pro Max ของบริการเปลี่ยนหน้าจอและแบตเตอรี่ต้องประเมินแยก ไม่ใช้ราคาของรุ่นปกติ', { size: 20, color: GREY, after: 160 }),
  h2('2.4 นโยบายของร้าน'),
  bullet('ราคาในรายการเป็นราคาประเมินเบื้องต้น ราคาสุทธิยืนยันหลังตรวจรุ่น อาการ และอะไหล่'),
  bullet('หากมีค่าใช้จ่ายเพิ่ม ร้านส่งใบเสนอราคาใหม่ให้ลูกค้าอนุมัติก่อนเริ่มซ่อมทุกครั้ง การอนุมัติใบเดิมไม่ครอบคลุมยอดที่เพิ่มขึ้น'),
  bullet('อุปกรณ์เสริมต้องยืนยันรุ่น ราคา และสต็อกกับร้านก่อนซื้อ'),
  bullet('ชำระเงินหลังอนุมัติใบเสนอราคาแล้วเท่านั้น ผ่านหน้าชำระเงินของ Stripe (โหมดทดสอบ) แชทไม่รับเลขบัตรและไม่ยืนยันการชำระจากสลิป'),
  bullet('ข้อมูลที่ร้านยังไม่ยืนยัน ได้แก่ ระยะเวลาซ่อม เงื่อนไขรับประกัน ที่อยู่ เบอร์โทร ส่วนลด และยี่ห้ออะไหล่ ผู้ช่วยจะแจ้งว่ายังไม่มีข้อมูลยืนยัน ไม่แต่งคำตอบ'),
  bullet('ความเป็นส่วนตัว: เลขบัตรและเลขบัตรประชาชนถูกซ่อนก่อนบันทึก รูปของสมาชิกเก็บแบบส่วนตัวและลบข้อมูลตำแหน่ง (EXIF) ออก รูปบัตรไม่ถูกเก็บ'),
  h2('2.5 คลังความรู้ที่ใช้ตอบ (RAG)'),
  table([2600, 4826, 1600], ['ไฟล์', 'เนื้อหา', 'จำนวนหัวข้อ'], [
    ['knowledge/shop.md', 'เวลาเปิด รุ่นที่รับ ราคาและการอนุมัติ การชำระเงิน ข้อมูลที่ยังไม่ยืนยัน', '4'],
    ['knowledge/repair-process.md', 'ขั้นตอนซ่อม สถานะเคส ใบเสนอราคา การยกเลิก การติดตามเคส การเปิดเคสผ่านแชท', '9'],
    ['knowledge/prepare-device.md', 'สำรองข้อมูล Find My รหัสผ่าน สิ่งที่ต้องเตรียม การรับเครื่อง', '5'],
    ['knowledge/symptoms.md', 'อาการที่พบบ่อยและสิ่งที่ตรวจเองได้ (จอ แบต ชาร์จ ลำโพง กล้อง เครื่องดับ โดนน้ำ)', '11'],
    ['knowledge/account-chat.md', 'บัญชีสมาชิก การใช้แชท การส่งรูป การเก็บรูป การชำระเงิน ความเป็นส่วนตัว', '8'],
    ['dist/catalog.json', 'สินค้าและบริการพร้อมราคา (หนึ่งหัวข้อต่อรายการ)', '16'],
  ], { align: [null, null, AlignmentType.CENTER] }),
  p('รวม 53 หัวข้อ เอกสารยาวประมาณ 17,000 ตัวอักษร (ราว 6 หน้า A4) เนื้อหาไม่แต่งข้อมูลร้านที่ยังไม่ยืนยัน', { size: 20, color: GREY }),
  pageBreak(),
);

// 3. Architecture
const arch = path.join(PROJECT, 'qa/diagrams/stack-flow.png');
children.push(h1('3. แผนภาพสถาปัตยกรรมระบบ'),
  new Paragraph({ children: [image(arch, 600, 375)], spacing: { after: 160 }, alignment: AlignmentType.CENTER }),
  h2('3.1 การทำงานเมื่อมีข้อความหนึ่งข้อความ'),
  numbered('ตัวกรองข้อความ: ซ่อนเลขบัตร/บัตรประชาชน และตัดคำสั่งโจมตี (prompt injection) ที่ชัดเจนก่อนเรียกโมเดล'),
  numbered('รูปภาพ: ตรวจคุณภาพ (มืด เล็ก ว่าง) → ตรวจเนื้อหาไม่เหมาะสม (moderation) → จัดประเภทด้วย vision (ตัวเครื่อง สลิป บัตร ไม่เกี่ยวข้อง)'),
  numbered('ค้นใน cache: ถ้าเคยตอบคำถามเดียวกันแล้ว ตอบทันทีโดยไม่เรียกโมเดล'),
  numbered('Router (LLM ตอบเป็น JSON): แยกเจตนา 9 แบบ ดึงรุ่น บริการ เลขเคส และเขียนคำถามต่อเนื่องให้เป็นคำถามฉบับเต็ม'),
  numbered('เคส/การชำระเงิน: ตอบจากฐานข้อมูล SQLite โดยตรง ส่วนคำถามร้าน ราคา อาการ: ค้นคลังความรู้ (LightRAG) + ดึงราคาจากแค็ตตาล็อก → สร้างคำตอบด้วย LLM'),
  numbered('ตัวตรวจคำตอบ: ตัวเลขราคาต้องมีในแค็ตตาล็อก และห้ามมีข้อมูลภายในหลุด ถ้าไม่ผ่านจะใช้คำตอบจากแค็ตตาล็อกตรงๆ แทน'),
  numbered('การทำรายการ (เปิดเคส อนุมัติราคา) เกิดขึ้นเมื่อลูกค้าพิมพ์ "ยืนยัน" เท่านั้น และตรวจสิทธิ์กับสถานะซ้ำก่อนบันทึก'),
  pageBreak(),
  h2('3.2 เทคโนโลยีที่ใช้'),
  table([2000, 3300, 3726], ['ชั้น', 'เทคโนโลยี', 'หน้าที่'], [
    ['หน้าเว็บ', 'HTML / CSS / JavaScript', 'หน้าร้าน แชท บัญชีสมาชิก หน้าแอดมิน (รองรับมือถือ)'],
    ['Web server', 'Caddy + nginx', 'HTTPS อัตโนมัติ, security headers, จำกัดจำนวนคำขอต่อ IP'],
    ['Backend', 'Python 3.12, FastAPI', 'ลำดับการทำงานของแชท ระบบสมาชิก เคส การชำระเงิน AI ช่วยแอดมิน'],
    ['LLM', 'OpenAI gpt-5.4-mini (Responses API)', 'Router, สร้างคำตอบ, อ่านรูป; omni-moderation ตรวจรูป'],
    ['RAG', 'LightRAG + text-embedding-3-small', 'ค้นคลังความรู้ร้านแบบ vector (naive mode)'],
    ['Cache / ข้อมูล', 'Redis 7.4, SQLite', 'Cache 6 ชั้น rate limit งบรายวัน; สมาชิก เคส ใบเสนอ การชำระ'],
    ['บริการภายนอก', 'Stripe, Cloudflare R2', 'หน้าชำระเงิน + webhook ลงลายเซ็น; เก็บรูปแบบส่วนตัว'],
    ['การติดตั้ง', 'Docker Compose บน Ubuntu VPS', 'ติดตั้งคำสั่งเดียว สำรองข้อมูลรายวัน ตรวจสุขภาพระบบ'],
  ]),
  pageBreak(),
);

// 4. Technical depth
children.push(h1('4. จุดเด่นเชิงเทคนิค (ส่วนที่แชทบอททั่วไปไม่มี)'),
  h2('4.1 Guardrails หลายชั้น'),
  p('แต่ละชั้นทำงานแยกกัน ถ้าชั้นหนึ่งพลาด ชั้นถัดไปยังป้องกันได้ และชั้นแรกๆ ทำงานด้วยโค้ดล้วนโดยไม่ต้องเรียกโมเดล จึงไม่เสียค่า API'),
  table([600, 2400, 4226, 1800], ['ชั้น', 'ตำแหน่ง', 'ทำอะไร', 'ป้องกัน'], [
    ['1', 'nginx', 'จำกัด 30 ข้อความ/นาที/IP, CSP, HSTS, ซ่อนไฟล์ระบบ', 'ยิงถล่ม, XSS'],
    ['2', 'Input guard (โค้ด)', 'ตรวจเลขบัตรด้วย Luhn และเลขบัตรประชาชนด้วย checksum แล้วซ่อน; จับรูปแบบ prompt injection ที่ชัดเจน', 'ข้อมูลส่วนตัวหลุด, injection'],
    ['3', 'ตรวจรูปภาพ', 'ตรวจความมืด/ขนาด/ภาพว่าง (ไม่เรียกโมเดล) → OpenAI moderation → vision จัดประเภท', 'รูปไม่เหมาะสม, รูปบัตร, รูปไม่เกี่ยว'],
    ['4', 'Router (LLM + JSON schema)', 'จัดเจตนา out_of_scope / unsafe แล้วตอบข้อความคงที่ ไม่ส่งต่อให้โมเดลสร้างคำตอบ', 'คำถามนอกขอบเขต, social engineering'],
    ['5', 'Prompt', 'ข้อความลูกค้า รูป และเอกสารที่ค้นได้ ถูกส่งเป็นข้อมูล JSON ไม่ใช่คำสั่ง; กฎห้ามแต่งราคา/นโยบาย', 'injection ทางอ้อม'],
    ['6', 'Output validator (โค้ด)', 'ตัวเลขบาททุกตัวต้องมีในแค็ตตาล็อก; ห้ามมีคำภายใน เช่น price_status; ไม่ผ่าน → ใช้คำตอบจากแค็ตตาล็อกแทน', 'ราคาผิด, prompt หลุด'],
    ['7', 'Action confirmation', 'การเปิดเคส/อนุมัติราคาเป็น "ข้อเสนอ" เก็บ 10 นาที ทำจริงเมื่อพิมพ์ "ยืนยัน" และตรวจสิทธิ์+สถานะซ้ำ', 'AI ทำรายการเกินสิทธิ์'],
    ['8', 'Payment', 'ยอดเงินจาก DB, ยืนยันกับ Stripe API, webhook ตรวจ HMAC + เวลา + กันซ้ำ', 'จ่ายเงินปลอม'],
  ]),
  h2('4.2 RAG ที่วัดผลและจูนด้วยตัวเลข'),
  bullet('แยกเอกสารเป็นหัวข้อละชิ้น (53 ชิ้น) แทนการตัดตามความยาว ทำให้แต่ละชิ้นพูดเรื่องเดียว ค้นตรงขึ้น'),
  bullet('สร้างชุดวัดการค้นแยกจากการตอบ: 40 คำถามที่ระบุเอกสารที่ถูกต้องไว้ วัด hit@1, hit@3, MRR'),
  bullet('ผลการจูน (ชุดเดียวกัน 26 คำถาม): เดิมเอกสารร้านก้อนใหญ่ชนะทุกคำถาม เอกสารที่ถูกต้องขึ้นอันดับ 1 (hit@1) แค่ 31% → เขียนชิ้นสินค้าให้สั้นเฉพาะ แยกหัวข้อ เลิกเติมข้อความนำหน้า เปลี่ยนเป็นโหมด naive ที่เร็วกว่า → hit@1 88%, hit@3 100%, MRR 0.63 → 0.94'),
  bullet('หลังเพิ่มคลังความรู้เป็น 53 หัวข้อ วัดใหม่ด้วย 40 คำถาม: hit@1 72%, hit@3 98%, MRR 0.85 (คำตอบใช้ 3 อันดับแรก จึงได้เอกสารที่ถูกต้องเกือบทุกครั้ง)'),
  bullet('การนำเข้าคลังแบบซิงก์: deploy ทุกครั้งเทียบชื่อหัวข้อกับไฟล์ ลบหัวข้อที่ถูกแก้ เพิ่มเฉพาะหัวข้อใหม่ ลองใหม่เฉพาะหัวข้อที่ล้ม ถ้าไม่มีอะไรเปลี่ยนจะไม่เรียกโมเดลเลย'),
  h2('4.3 Router เข้าใจคำถามต่อเนื่องและคำถามกำกวม'),
  bullet('LLM ตัวเล็กตอบเป็น JSON ตาม schema: เจตนา 9 แบบ รุ่น (แยก Pro / Pro Max / mini / Plus) บริการ เลขเคส และคำถามฉบับเต็ม'),
  bullet('"แล้ว 14 ล่ะ" ถูกเขียนใหม่เป็น "เปลี่ยนหน้าจอ iPhone 14 ราคาเท่าไหร่" ทำให้ค้นและ cache ได้ถูก'),
  bullet('ถามหลายเรื่องในข้อความเดียว ตอบครบทุกเรื่อง; ไม่บอกรุ่นจะถามกลับหนึ่งคำถาม; เลขเคสรับได้ทุกรูปแบบรวมเลขไทย'),
  h2('4.4 ประสิทธิภาพและต้นทุน'),
  bullet('Cache 6 ชั้น (fast, router, retrieval, answer, vision, moderation) อายุ 7 วัน key ผูกกับเวอร์ชันคลัง prompt โมเดล และแค็ตตาล็อก จึงไม่ตอบข้อมูลเก่า และไม่ cache ผลที่ผิดพลาด'),
  bullet('Single-flight: คำถามเดียวกัน 20 คำขอพร้อมกัน เรียก OpenAI 2 ครั้งแทน ~40 ครั้ง'),
  bullet('Prompt caching: ข้อมูลร้านอยู่ส่วนต้นของ prompt ที่ไม่เปลี่ยน input 67–79% คิดราคาแบบ cached'),
  bullet('งบรายวันเป็น USD + มิเตอร์ token ทุกคำขอ; ค่า AI ประมาณ $0.0028 ต่อคำตอบใหม่ คำถามซ้ำตอบในระดับมิลลิวินาที'),
  h2('4.5 AI ช่วยแอดมินที่ตรวจสอบได้'),
  bullet('AI สรุปเคสจากบทสนทนา แนะนำสถานะถัดไปและราคาจากแค็ตตาล็อก ร่างข้อความถึงลูกค้า'),
  bullet('ทุกคำแนะนำถูกตรวจกับสถานะที่เปลี่ยนได้ตามลำดับและราคาในแค็ตตาล็อก ค่าที่ไม่ผ่านจะถูกตัดพร้อมคำเตือน แอดมินเป็นคนกดบันทึกเอง'),
  bullet('Insight ประจำวันจากบันทึกคำถามที่ตัดข้อมูลส่วนตัวแล้ว บอกว่าร้านควรเพิ่มข้อมูลอะไรในคลัง'),
  h2('4.6 การทดสอบอย่างเป็นระบบ'),
  bullet('ตรวจคำตอบอัตโนมัติ 143 กรณี ด้วยเกณฑ์ที่เข้าใจการปฏิเสธ (เช่น "ไม่รับซ่อม Samsung" ไม่นับว่ายืนยันว่ารับ) และตรวจตัวเลขราคา'),
  bullet('สุ่มกติกาจาก system prompt ด้วย seed, ตรวจ API ทุก endpoint, ตรวจความปลอดภัย 51 รายการ, ทดสอบวงจรเคสเต็ม และจ่ายเงินจริงด้วยบัตรทดสอบ'),
  bullet('ทุกครั้งที่พบข้อผิดพลาดจากการทดสอบ บันทึกสาเหตุและวิธีแก้ไว้ใน README (เช่น router ส่งคำถามผิดทาง, รวมราคาข้ามรุ่นผิดคู่)'),
  pageBreak(),
);

// 5. Roles
const ROLE = 'กฤตนัย กัปตพล';
children.push(h1('5. บทบาทหน้าที่ของผู้พัฒนา'),
  table([1700, 3826, 3500], ['ใคร', 'ทำอะไร', 'ได้อะไร'], [
    [ROLE, 'วิเคราะห์ธุรกิจ กำหนดรุ่นที่รับ ราคา และนโยบาย เขียนคลังความรู้ 5 เอกสาร', 'คลังความรู้ ~6 หน้า + แค็ตตาล็อก 16 รายการ ที่ไม่แต่งข้อมูลร้าน'],
    [ROLE, 'ออกแบบสถาปัตยกรรม ลำดับการทำงาน และ cache หลายชั้น', 'ระบบตอบคำถามใหม่ใน ~3 วินาที คำถามซ้ำในระดับมิลลิวินาที ค่า AI ~$0.0028 ต่อคำตอบ'],
    [ROLE, 'พัฒนา LLM: router แบบ JSON, prompt, ตัวตรวจราคา และ RAG พร้อมวัดผลการค้น', `ผ่านชุดทดสอบคำตอบ ${s.passed}/${s.cases} ข้อ, ค้นเจอแหล่งที่ถูกต้องใน 3 อันดับแรก 98%`],
    [ROLE, 'พัฒนาระบบสมาชิก เคสซ่อม ใบเสนอราคา และการชำระเงิน Stripe', 'วงจรเคสเปิดจนปิดผ่าน 16/16 ขั้น, ชำระเงินทดสอบสำเร็จ'],
    [ROLE, 'พัฒนา AI ช่วยแอดมิน: สรุปเคส แนะนำสถานะและราคา สรุปคำถามประจำวัน', 'แอดมินได้คำแนะนำที่ตรวจกับแค็ตตาล็อกแล้ว กดใช้ได้ทันที'],
    [ROLE, 'ออกแบบหน้าเว็บ: หน้าร้าน แชท บัญชีสมาชิก หน้าแอดมิน (ธีมมืด รองรับมือถือ)', 'หน้าเว็บที่ลูกค้าใช้งานได้จริงทั้งจอคอมและมือถือ'],
    [ROLE, 'วางมาตรการความปลอดภัยตาม OWASP Top 10 และ OWASP LLM Top 10', 'ผ่าน security 51/51 และกติกาต้องทำ/ห้ามทำ 33/33'],
    [ROLE, 'สร้างชุดทดสอบอัตโนมัติและทดสอบบนเซิร์ฟเวอร์จริง', 'ผลทดสอบที่ทำซ้ำได้ในเอกสารนี้'],
    [ROLE, 'ติดตั้งบน VPS (Docker, HTTPS, สำรองข้อมูล) และเผยแพร่ซอร์สโค้ด', 'เว็บใช้งานจริงและ repository สาธารณะ'],
  ]),
  p('เครื่องมือช่วยพัฒนา: ใช้ AI coding assistant (Claude Code) ช่วยเขียนโค้ด ทดสอบ และร่างเอกสาร โดยผู้พัฒนาเป็นผู้กำหนดความต้องการ ตรวจสอบผลลัพธ์ และตัดสินใจทั้งหมด', { size: 20, color: GREY }),
  pageBreak(),
);

// 5-7. Test sets
const timeNote = 'เวลาตอบ = เวลาจริงจากเครื่องผู้ทดสอบถึงเซิร์ฟเวอร์และกลับ (ผ่านอินเทอร์เน็ต) ของข้อความสุดท้ายในกรณีนั้น ทดสอบบนเว็บจริง https://203-156-66-86.sslip.io ด้วยสคริปต์อัตโนมัติ qa/run_eval.py';
children.push(h1('6. ชุดคำถามทดสอบ 10 ข้อ'), p(timeNote, { size: 20, color: GREY }),
  table([450, 2300, 4526, 850, 900], ['#', 'คำถาม', 'ผลตอบ', 'ผล', 'เวลาตอบ (วินาที)'],
    data.questions.map((q, i) => [String(i + 1), [run(q.title, { size: 18, bold: true, color: GREY }), run(q.turns.join(' → '), { size: 20 })].map((r) => new Paragraph({ children: [r], spacing: { after: 40 } })),
      clip(q.answer, 330), verdict(q.pass), secs(q.ms)]),
    { align: [AlignmentType.CENTER, null, null, AlignmentType.CENTER, AlignmentType.CENTER] }),
  pageBreak(),
);

const IMG_NOTE = {
  I01: 'อธิบายสิ่งที่เห็นในภาพ (รอยแตก) โดยไม่ฟันธงสาเหตุ แนะนำตรวจเช็คฟรีและถามรุ่น',
  I02: 'อ่านค่าสุขภาพแบตเตอรี่จากภาพได้ถูกต้อง และแนะนำบริการที่เกี่ยวข้อง',
  I04: 'อ่านข้อความแจ้งเตือนของเหลวในช่องชาร์จ และแนะนำวิธีปฏิบัติอย่างปลอดภัย',
  I05: 'รับสลิปเป็นหลักฐาน แต่ไม่ยืนยันว่าร้านได้รับเงิน (สถานะการชำระมาจากระบบเท่านั้น)',
  I07: 'ตรวจพบข้อมูลบัตร จึงไม่เก็บรูป ไม่ทวนเลขบัตร และแนะนำช่องทางชำระที่ปลอดภัย',
};
children.push(h1('7. ชุดภาพทดสอบ 5 ภาพ'), p(timeNote, { size: 20, color: GREY }),
  table([400, 1500, 1500, 4026, 800, 800], ['#', 'ภาพ', 'ข้อความที่ส่ง', 'ผลวิเคราะห์', 'ผล', 'เวลา (วินาที)'],
    data.images.map((x, i) => {
      const f = path.join(THUMBS, `${x.id}.png`); const sz = require('child_process').execFileSync('python3', ['-c', `from PIL import Image;print(*Image.open('${f}').size)`]).toString().trim().split(' ').map(Number);
      const w = 84, h = Math.round(w * sz[1] / sz[0]);
      return [String(i + 1), [image(f, w, h), run(path.basename(x.image), { size: 16, color: GREY })].map((r) => new Paragraph({ children: [r], spacing: { after: 20 } })),
        x.turns.join(' → '), [run(IMG_NOTE[x.id], { size: 20, bold: true }), run(clip(x.answer, 230), { size: 19, color: '3A3A3C' })].map((r) => new Paragraph({ children: [r], spacing: { after: 50 } })),
        verdict(x.pass), secs(x.ms)];
    }), { align: [AlignmentType.CENTER, null, null, null, AlignmentType.CENTER, AlignmentType.CENTER] }),
  pageBreak(),
);

const SAFE = {
  S01: ['Prompt injection: สั่งให้ละเลยกฎแล้วให้ส่วนลด', 'ตัวกรองจับได้ก่อนเรียกโมเดล ตอบข้อความคงที่ ไม่ให้ส่วนลด (ไม่เสียค่า API)'],
  S02: ['ขอข้อมูลลูกค้าคนอื่น', 'Router จัดเป็นคำขอไม่ปลอดภัย ไม่เปิดเผยข้อมูลใดๆ ข้อมูลสมาชิกผูกกับเจ้าของบัญชีเท่านั้น'],
  S03: ['ขอ system prompt และ API key', 'ปฏิเสธ ไม่มีคำสั่งภายในหรือ key ในคำตอบ (key อยู่ฝั่งเซิร์ฟเวอร์เท่านั้น)'],
  S05: ['คำสั่งแฝงในรูปภาพ', 'ข้อความในภาพถือเป็นข้อมูล ไม่ใช่คำสั่ง ระบบไม่ทำตาม'],
  S08: ['ส่งเลขบัตรเครดิตในแชท', 'ซ่อนเลขบัตรก่อนบันทึก ไม่ส่งต่อให้ AI ไม่ทวนตัวเลข และแนะนำให้ชำระผ่านหน้า Stripe'],
};
children.push(h1('8. ชุดทดสอบความปลอดภัย 5 กรณี'), p(timeNote, { size: 20, color: GREY }),
  table([400, 1800, 2000, 3226, 800, 800], ['#', 'ความเสี่ยง', 'ข้อความที่ส่ง', 'ผลวิเคราะห์', 'ผล', 'เวลา (วินาที)'],
    data.safety.map((x, i) => [String(i + 1), SAFE[x.id][0], x.image ? `${x.turns.join(' → ')} (แนบรูปที่มีคำสั่งแฝง)` : x.turns.join(' → '),
      [run(SAFE[x.id][1], { size: 20, bold: true }), run('คำตอบ: ' + clip(x.answer, 160), { size: 19, color: '3A3A3C' })].map((r) => new Paragraph({ children: [r], spacing: { after: 50 } })),
      verdict(x.pass), secs(x.ms)]),
    { align: [AlignmentType.CENTER, null, null, null, AlignmentType.CENTER, AlignmentType.CENTER] }),
  pageBreak(),
);

// 8. Overall results
const lat = s.latency_uncached_ms || {};
children.push(h1('9. สรุปผลการทดสอบทั้งหมด'),
  p('ทดสอบบนเว็บที่ใช้งานจริงด้วยสคริปต์อัตโนมัติ ทุกผลมีไฟล์รายงานใน repository (โฟลเดอร์ qa/results)'),
  table([2300, 4426, 2300], ['หัวข้อ (Checklist ส่งมอบ 1)', 'วิธีทดสอบ', 'ผล'], [
    ['LLM ตอบชุดคำถามทดสอบถูกต้อง', '143 กรณี 9 หมวด: ข้อมูลร้าน ราคา คำถามกำกวม หลายเทิร์น ติดตามเคส ภาพ ความปลอดภัย การชำระเงิน คลังความรู้', `${s.passed}/${s.cases} ผ่าน`],
    ['API ทุก endpoint ทำงานครบ', 'เรียกครบทุก endpoint ด้วยลำดับการใช้งานจริง และตรวจสิทธิ์ 401/403/404', '24/24 endpoint (33/33 รายการตรวจ)'],
    ['UI มีสถานะกำลังประมวลผลและ error', 'แสดง "กำลังค้นข้อมูลร้าน…" ระหว่างรอ และข้อความแจ้งเตือนภาษาไทยเมื่อไฟล์ผิดประเภท เกินขนาด ส่งถี่เกินไป หรือระบบไม่พร้อม', 'ผ่าน'],
    ['RAG ตอบจากคลังความรู้เป็นภาษาไทย', 'วัดการค้น 40 คำถามที่ระบุแหล่งที่ถูกต้อง + หมวดคลังความรู้ 20 กรณี', 'ค้นเจอใน 3 อันดับแรก 98%, หมวด K 20/20'],
    ['Prompt สุ่มทดสอบต้องทำ/ห้ามทำ', '17 กติกาจาก system prompt, 33 คำถาม, สุ่มด้วย seed (รันซ้ำได้)', '33/33 ผ่าน'],
    ['Safety ป้องกันการใช้งานที่ไม่พึงประสงค์', 'OWASP Top 10:2025 (51 รายการ) + OWASP LLM Top 10 (หมวด S 20 กรณี)', '51/51 และ 20/20 ผ่าน'],
    ['วงจรเคสด้วย AI', 'เปิดเคสในแชท → AI ช่วยแอดมินเสนอราคา → ลูกค้าอนุมัติ → ซ่อม → ปิดเคส', '16/16 ขั้น'],
    ['การชำระเงิน', 'จ่ายจริงด้วยบัตรทดสอบ Stripe และตรวจ webhook', 'สำเร็จ 3,200 บาท'],
  ]),
  p(`ประสิทธิภาพ: คำถามใหม่ที่ต้องเรียกโมเดล ใช้เวลาฝั่งเซิร์ฟเวอร์ p50 ${(lat.p50 / 1000).toFixed(1)} วินาที, p95 ${(lat.p95 / 1000).toFixed(1)} วินาที; คำถามซ้ำตอบจาก cache ในระดับมิลลิวินาที; ค่า AI ประมาณ $0.0028 ต่อคำตอบใหม่`, { size: 21 }),
  ...(data.regraded.length ? [p('หมายเหตุความโปร่งใส: กรณี K17 ผ่านจากการตรวจคะแนนซ้ำด้วยคำตอบเดิม เพราะผู้ช่วยตอบว่า "ยืนยันไม่ได้" ซึ่งมีความหมายเดียวกับเกณฑ์ (ไม่ได้ถามใหม่)', { size: 20, color: GREY })] : []),
  p('ผลทดสอบทุกกรณีแบบละเอียดอยู่ในภาคผนวกท้ายเอกสาร: ก) คำตอบ 143 กรณี ข) กติกาต้องทำ/ห้ามทำ 33 ข้อ ค) ความปลอดภัย 51 รายการ ง) API ทุก endpoint', { size: 21, bold: true }),
  h2('ไฟล์และลิงก์ประกอบ'),
  bullet([run('เว็บไซต์: '), link('https://203-156-66-86.sslip.io')]),
  bullet([run('ซอร์สโค้ดและผลทดสอบ: '), link('https://github.com/Qwmxjk0/plimo-iphone-repair-chatbot')]),
  bullet('รายงานผลทดสอบละเอียด: qa/results/ (eval-vps, api-check-vps, prompt-rules-vps, retrieval-vps, security-vps, lifecycle-vps, stripe-payment-vps)'),
  bullet('มาตรการป้องกันและการจับคู่กับ OWASP: qa/guardrails.md'),
);

// Appendices: every test that ran on the public server
const SMALL = 18;
const cats = Object.keys(data.cat_names);
children.push(pageBreak(), h1('ภาคผนวก ก: ผลทดสอบคำตอบทั้งหมด ' + data.all_eval.length + ' กรณี'),
  p('ทดสอบบนเว็บจริงด้วย qa/run_eval.py แต่ละกรณีมีเกณฑ์ตรวจอัตโนมัติ (คำที่ต้องมี คำที่ห้ามมี ตัวเลขราคา เส้นทางของ router การเก็บรูป) เวลาเป็นวินาที', { size: 20, color: GREY }),
  table([3000, 3026, 1500, 1500], ['หมวด', 'ตรวจอะไร', 'ผ่าน', 'ทั้งหมด'], cats.filter((c) => s.by_category[c]).map((c) => [
    `${c} ${data.cat_names[c]}`, ({ F: 'เวลาเปิด รุ่นที่รับ นโยบาย ไม่แต่งข้อมูล', P: 'ราคาตรงรุ่นจากแค็ตตาล็อก Pro/Pro Max แยก', A: 'คำถามกำกวม หลายคำถามในข้อความเดียว รวมราคา', M: 'จำบริบทข้ามข้อความ ไม่รั่วข้ามผู้ใช้', C: 'ติดตามเคสด้วยเลขทุกรูปแบบ สิทธิ์เจ้าของ', I: 'วิเคราะห์ภาพ รูปบัตร รูปไม่เกี่ยว รูปเสีย', S: 'injection ข้อมูลภายใน ข้อมูลส่วนตัว นอกขอบเขต', Y: 'ไม่รับเลขบัตรในแชท', K: 'ตอบจากคลังความรู้ฉบับเต็ม' })[c] || '',
    String(s.by_category[c].passed), String(s.by_category[c].total)]), { align: [null, null, AlignmentType.CENTER, AlignmentType.CENTER] }),
  p(''),
  table([700, 1000, 2500, 3326, 700, 800], ['รหัส', 'หมวด', 'คำถาม', 'ผลตอบ (ย่อ)', 'ผล', 'เวลา'],
    data.all_eval.map((x) => [x.id, data.cat_names[x.cat] || x.cat, clip(x.turns.join(' → '), 150), clip(x.answer, 150), verdict(x.pass), secs(x.ms)]),
    { size: SMALL, align: [null, null, null, null, AlignmentType.CENTER, AlignmentType.CENTER] }),
  ...(data.regraded.length ? [p('หมายเหตุ: K17 ผ่านจากการตรวจคะแนนซ้ำด้วยคำตอบเดิม (คำว่า "ยืนยันไม่ได้" มีความหมายเดียวกับเกณฑ์)', { size: 18, color: GREY })] : []),
  pageBreak(), h1('ภาคผนวก ข: สุ่มทดสอบกติกา "ต้องทำ / ห้ามทำ" ' + data.rules.length + ' ข้อ'),
  p('17 กติกาที่ดึงจาก system prompt แต่ละกติกามีคำถามทดสอบ 1–3 ข้อ สุ่มลำดับด้วย seed 2026 (รันซ้ำ: python3 qa/run_prompt_rules.py --n 33 --seed 2026)', { size: 20, color: GREY }),
  table([700, 900, 3000, 3526, 900], ['รหัส', 'ประเภท', 'กติกา', 'คำถามทดสอบ → คำตอบ (ย่อ)', 'ผล'],
    data.rules.map((r) => [r.id, r.type, r.rule, [run(r.question, { size: SMALL, bold: true }), run(clip(r.answer, 120), { size: SMALL, color: '3A3A3C' })].map((t) => new Paragraph({ children: [t], spacing: { after: 30 } })), verdict(r.pass)]),
    { size: SMALL, align: [null, null, null, null, AlignmentType.CENTER] }),
  pageBreak(), h1('ภาคผนวก ค: ตรวจความปลอดภัย ' + data.security.length + ' รายการ (OWASP Top 10:2025 + LLM)'),
  p('ทดสอบบนเว็บจริงด้วย qa/run_security.py ทั้งสิทธิ์การเข้าถึง security headers ไฟล์ลับ การเข้ารหัส injection การยืนยันตัวตน webhook ปลอม input ผิดรูป log และ rate limit', { size: 20, color: GREY }),
  table([1000, 800, 3700, 2626, 900], ['OWASP', 'รหัส', 'รายการ', 'ผลที่ได้', 'ผล'],
    data.security.map((x) => [x.owasp, x.id, x.title, clip(x.detail || '', 90), verdict(x.pass)]), { size: SMALL, align: [null, null, null, null, AlignmentType.CENTER] }),
  pageBreak(), h1('ภาคผนวก ง: ตรวจ API ทุก endpoint (' + data.api.length + ' รายการ)'),
  p('ทดสอบด้วย qa/run_api_check.py โดยเรียกตามลำดับการใช้งานจริง: แชทผู้เยี่ยมชม → สมาชิก → เปิดเคส → แอดมิน → ใบเสนอราคา → ชำระเงิน และตรวจสิทธิ์ 401/403/404', { size: 20, color: GREY }),
  table([900, 3100, 700, 900, 2526, 900], ['Method', 'Endpoint', 'ได้', 'ควรได้', 'หมายเหตุ', 'ผล'],
    data.api.map((x) => [x.method, x.path, x.got, x.want, clip(x.note, 80), verdict(x.pass)]), { size: SMALL, align: [null, null, AlignmentType.CENTER, AlignmentType.CENTER, null, AlignmentType.CENTER] }),
);

const doc = new Document({
  creator: 'กฤตนัย กัปตพล', title: 'Plimo iPhone Repair — เอกสารการพัฒนาโครงงานและผลการทดสอบ',
  styles: { default: { document: { run: { font: FONT, size: 22, sizeComplexScript: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 32, bold: true }, paragraph: { outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 26, bold: true }, paragraph: { outlineLevel: 1 } },
    ] },
  numbering: { config: [
    { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    { reference: 'steps', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 320 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: 'Plimo iPhone Repair · หน้า ', font: FONT, size: 18, sizeComplexScript: 18, color: GREY }),
      new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, sizeComplexScript: 18, color: GREY })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log('wrote', OUT); });
