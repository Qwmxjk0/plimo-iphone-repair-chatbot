"""Case actions requested in chat: open a case, approve or reject a quote.

The model only proposes. A proposal is stored server-side and runs only when the
member confirms in a separate message ("ยืนยัน"); execution goes through the same
membership functions as the portal, which re-check ownership and the current state.
"""
import re
from fastapi import HTTPException
import membership
import nlu

CONFIRM = re.compile(r'^\s*(?:ยืนยัน|ตกลง|ใช่|โอเค|ok|okay|confirm|yes)(?:\s*(?:ครับ|ค่ะ|คะ|ค่า|คับ|นะ|เลย|จ้า|ค่ะ))*\s*[.!]*\s*$', re.I)
DECLINE = re.compile(r'^\s*(?:ยกเลิก|ไม่|ไม่เอา|ไม่ใช่|ไม่ต้อง|cancel|no)(?:\s*(?:ครับ|ค่ะ|คะ|คับ|นะ|ก่อน|ดีกว่า))*\s*[.!]*\s*$', re.I)
VARIANT_NAMES = {'base': '', 'pro': ' Pro', 'pro_max': ' Pro Max', 'plus': ' Plus', 'mini': ' mini'}
PENDING_TTL = 600
# A real symptom must be known before a case is proposed ("อยากส่งซ่อม / iPhone 14" is not one).
SYMPTOM = re.compile(r'เสีย|แตก|ร้าว|ไม่ติด|ไม่เข้า|ไม่ทำงาน|ไม่ได้|ค้าง|ดับ|รีสตาร์ท|ร้อน|ช้า|หมดไว|บวม|เบลอ|เบา|ไม่ดัง|เป็นเส้น|ตกน้ำ|โดนน้ำ|ลาย|กระพริบ|ทัช|face ?id|wi-?fi|สัญญาณ', re.I)

def case_model(models):
    """The portal's model format, only for models the shop accepts (iPhone 11–17)."""
    for family, variant in models:
        if family.isdigit() and 11 <= int(family) <= 17 and variant in VARIANT_NAMES:
            return f'iPhone {family}{VARIANT_NAMES[variant]}'
    return None

def symptom_text(text, history):
    """The customer's own words about the problem: earlier user turns plus this message."""
    turns = [h.get('content', '') for h in history if h.get('role') == 'user'][-3:] + [text]
    turns = [t.replace(' [มีภาพประกอบ]', '').strip() for t in turns if t and t.strip()]
    return ' / '.join(dict.fromkeys(turns))[:500]

def propose_open(member, route, text, history):
    if not member:
        return 'ส่งเคสซ่อมผ่านแชทได้หลังเข้าสู่ระบบครับ กดปุ่ม "ติดตามงานซ่อม" มุมขวาบนเพื่อเข้าสู่ระบบ แล้วบอกรุ่นและอาการอีกครั้งได้เลยครับ', None
    model = case_model(route['models'])
    if not model:
        unsupported = [m for m in route['models'] if not case_model([m])]
        if unsupported:
            return 'รุ่นนี้ยังไม่อยู่ในรุ่นที่ร้านรับผ่านระบบเคส (iPhone 11–17 รวม mini / Plus / Pro / Pro Max) ครับ ขอให้ติดต่อร้านเพื่อสอบถามเพิ่มเติมครับ', None
        return 'ยินดีรับเรื่องครับ ขอทราบรุ่น iPhone เต็ม ๆ (เช่น iPhone 13 Pro) เพื่อเปิดเคสซ่อมให้ครับ', None
    issue = symptom_text(text, history)
    if not route['services'] and not nlu.extract_services(issue) and not SYMPTOM.search(issue):
        return f'รับทราบว่าเป็น {model} ครับ รบกวนเล่าอาการที่พบสั้น ๆ (เช่น จอแตก แบตหมดไว ชาร์จไม่เข้า) เพื่อเปิดเคสซ่อมครับ', None
    pending = {'type': 'open_case', 'model': model, 'issue': issue}
    answer = (f'ทางร้านเตรียมเปิดเคสซ่อมให้แล้วครับ กรุณาตรวจรายละเอียด\n- รุ่น: {model}\n- อาการ: {issue}\n'
              'ถ้าถูกต้อง พิมพ์หรือกด "ยืนยัน" เพื่อส่งเคส หรือ "ยกเลิก" ถ้ายังไม่ต้องการ (คำขอซ่อมยังไม่ใช่การยืนยันว่าร้านรับเครื่องแล้ว)')
    return answer, pending

def propose_quote(member, ref, decision):
    if not member:
        return 'กรุณาเข้าสู่ระบบก่อนตอบรับใบเสนอราคาครับ', None
    if not ref:
        return 'ขอเลขเคส (เช่น PLM-00012) ที่ต้องการตอบรับใบเสนอราคาครับ', None
    with membership.db() as c:
        case = c.execute('SELECT * FROM cases WHERE id=? AND user_id=?', (ref, member['id'])).fetchone()
        quote = c.execute('SELECT * FROM case_quotes WHERE case_id=? ORDER BY id DESC LIMIT 1', (ref,)).fetchone() if case else None
    if not case:
        return 'ไม่พบเคสนี้ในบัญชีของคุณครับ กรุณาตรวจเลข PLM อีกครั้ง', None
    if not quote or case['status'] != 'awaiting_approval' or quote['status'] != 'pending':
        return f"เคส PLM-{ref:05d} ตอนนี้ไม่มีใบเสนอราคาที่รอคุณตอบรับครับ สถานะล่าสุดดูได้ด้วยการถามเลขเคส", None
    word = 'อนุมัติ' if decision == 'approve' else 'ปฏิเสธ (ขอให้ร้านประเมินใหม่)'
    pending = {'type': 'quote', 'case_id': ref, 'quote_id': quote['id'], 'decision': decision}
    answer = (f"ยืนยัน{word}ใบเสนอราคา #{quote['id']} ของเคส PLM-{ref:05d} ({case['model']}) จำนวน {quote['amount']:,.2f} บาทไหมครับ\n"
              'พิมพ์หรือกด "ยืนยัน" เพื่อบันทึก หรือ "ยกเลิก" ถ้ายังไม่ตัดสินใจ' +
              ('\nหากตรวจพบค่าใช้จ่ายเพิ่มเติม ทางร้านจะส่งใบเสนอใหม่ให้อนุมัติอีกครั้งครับ' if decision == 'approve' else ''))
    return answer, pending

def execute(member, pending, conversation_id):
    """Run a confirmed proposal. Returns (answer, case id) and never raises for stale state."""
    try:
        if pending['type'] == 'open_case':
            item = membership.open_case(member, pending['model'], pending['issue'], conversation_id, note='สมาชิกส่งคำขอซ่อมผ่านแชท (ยืนยันแล้ว)')
            return (f"ส่งเคสซ่อมแล้วครับ เลขเคส {item['reference']} · {item['model']}\n"
                    'ทางร้านจะตรวจสอบและอัปเดตสถานะ ถามความคืบหน้าได้ด้วยเลขเคสนี้ หรือดูที่ บัญชี → งานซ่อมของฉัน'), item['id']
        if pending['type'] == 'quote':
            membership.quote_decision(member, pending['case_id'], pending['quote_id'], pending['decision'], 'ตอบผ่านแชท (ยืนยันแล้ว)')
            ref = f"PLM-{pending['case_id']:05d}"
            if pending['decision'] == 'approve':
                return f'บันทึกการอนุมัติใบเสนอราคาของเคส {ref} แล้วครับ ทางร้านจะเริ่มซ่อมตามราคาที่อนุมัติ', pending['case_id']
            return f'บันทึกการปฏิเสธใบเสนอราคาของเคส {ref} แล้วครับ ทางร้านจะประเมินและเสนอราคาใหม่', pending['case_id']
    except HTTPException as exc:
        return f'ทำรายการไม่สำเร็จครับ: {exc.detail}', None
    return 'ไม่พบรายการที่รอยืนยันครับ', None

def describe(pending):
    """Short label for the confirm button."""
    if pending['type'] == 'open_case':
        return f"ส่งเคส {pending['model']}"
    return ('อนุมัติ' if pending['decision'] == 'approve' else 'ปฏิเสธ') + f" ใบเสนอ #{pending['quote_id']}"
