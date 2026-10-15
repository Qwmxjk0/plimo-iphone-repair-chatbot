"""Deterministic Thai text helpers: no network and no model calls.

Used for cache keys, case-number parsing, entity hints and sensitive-data
guards. Rules stay conservative: a wrong merge here serves a wrong answer.
"""
import re
import unicodedata

THAI_DIGITS = str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789')
DASHES = str.maketrans({'–': '-', '—': '-', '‐': '-', '‑': '-', '−': '-'})
SUFFIX = re.compile(r"\s*(?:ครับ(?:ผม)?|คับ|ค่ะ[ะ]*|คะ[ะ]*|คร่า[า]*|ค่า[า]*)(?:\s*5{3,})*[!！?？]*$")

def clean(text):
    """NFC, Thai digits to ASCII, one dash style and single spaces."""
    text = unicodedata.normalize('NFC', text or '').translate(THAI_DIGITS).translate(DASHES)
    return ' '.join(text.split())

def fold_suffix(text):
    """Strip polite endings and laughter after them; bare 555 may be a price."""
    folded = text
    while True:
        candidate = SUFFIX.sub('', folded).strip()
        if candidate == folded:
            return folded or text
        folded = candidate

# Order matters: Pro Max before Pro, and aliases before entity extraction.
ALIASES = [
    (r'(?<=\d)(?=[a-z])|(?<=[a-z])(?=\d)', ' '),
    (r'ไอ\s*โฟน|ไอโฟร|ไอโฟฟ|i\s*-?\s*phone|(?<![a-z])ip(?=\s*\d)', 'iphone'),
    (r'pro\s*-?\s*max|promax|โปร\s*แม[็]?[กค](?:ซ์|ส์|ซ)?', 'pro max'),
    (r'\b(1[1-7])\s*pm\b', r'\1 pro max'),
    (r'โปร(?!โม)', 'pro'),
    (r'พลัส', 'plus'),
    (r'มินิ', 'mini'),
    (r'แอร์', 'air'),
]

def canonical(text):
    """Cache-key form: cleaned, lower-case, model aliases unified, suffix folded."""
    text = clean(text).lower()
    for pattern, repl in ALIASES:
        text = re.sub(pattern, repl, text)
    text = re.sub(ALIASES[0][0], ' ', text)
    text = re.sub(r'\b(\d+) e\b', r'\1e', text)
    text = ' '.join(text.split())
    return fold_suffix(re.sub(r'[\s!！?？.。…~]+$', '', text) or text)

# Case references: PLM-00012, PLM12, plm 12, #PLM-12, เคส 12, เคสที่ 12, Thai digits,
# and references written directly against Thai letters (no \b there).
# "เคส 12" alone may mean a phone case for iPhone 12, so that form needs a
# tracking word in the message and must not be followed by a quantity/model word.
CASE_REF = re.compile(r'(?<![a-z0-9])#?plm\s*-?\s*(\d{1,7})(?!\d)|เคส(?:ซ่อม)?\s*(?:ที่|หมายเลข|เลข(?:ที่)?)?\s*#?\s*(\d{1,7})(?!\d)(?!\s*(?:อัน|ชิ้น|ใบ|ตัว|บาท|วัน|เดือน|ปี|ชั่วโมง|ชม|นาที|เครื่อง|รุ่น|pro|plus|mini|โปร))', re.I)
TRACKING = re.compile(r'ถึงไหน|สถานะ|คืบหน้า|เสร็จ|อัปเดต|อัพเดท|ติดตาม|รับเครื่อง|อนุมัติ|ชำระ|จ่าย|ยกเลิก|ใบเสนอ')
CASE_HINT = re.compile(r'เคส(?:ซ่อม)?ของ\s*(?:ฉัน|ผม|หนู|เรา|ดิฉัน)|(?:เคส|งานซ่อม|เครื่อง)(?:ซ่อม)?(?:ของ)?\s*(?:ฉัน|ผม|หนู|เรา|ดิฉัน)\s*.{0,15}(?:ถึงไหน|สถานะ|คืบหน้า|ซ่อมเสร็จ|เสร็จหรือยัง|เสร็จยัง|อัปเดต|รับได้ยัง|รับเครื่องได้)|สถานะ\s*(?:เคส|งานซ่อม|การซ่อม)|(?:เคส|งานซ่อม)\s*.{0,12}(?:ถึงไหน|สถานะ|คืบหน้า)|ซ่อม(?:เสร็จ|ได้)?\s*(?:หรือยัง|ยัง\s*(?:ครับ|คะ|คับ)?$)|รับเครื่อง\s*.{0,10}ได้(?:หรือ)?ยัง')

def parse_case_ref(text):
    text = clean(text)
    for match in CASE_REF.finditer(text):
        if match.group(2) and not TRACKING.search(text):
            continue
        number = int(match.group(1) or match.group(2))
        if 0 < number < 10**7:
            return number
    return None

def is_case_question(text):
    text = clean(text)
    return parse_case_ref(text) is not None or bool(CASE_HINT.search(text))

VARIANTS = {'pro max': 'pro_max', 'pro': 'pro', 'plus': 'plus', 'mini': 'mini', 'e': 'e', 'air': 'air'}
MODEL = re.compile(
    r'iphone\s*(?P<f1>\d{1,2})\s*(?:(?P<v1>pro max|pro|plus|mini|e|air)(?![a-z]))?'
    r'|iphone\s*(?P<named>air|se|xs max|xs|xr|x)(?![a-z])'
    r'|(?<![\d,.:/])(?P<f2>1[1-7])\s*(?P<v2>pro max|pro|plus|mini|e)(?![a-z])'
    r'|(?:รุ่น|เครื่อง|หน้าจอ|จอ|แบต(?:เตอรี่)?|กล้อง(?:หลัง)?|ลำโพง|ฟิล์ม|เคส(?:ใส)?|สาย(?:ชาร์จ)?)\s*(?P<f3>1[1-7])(?![\d,.:])\s*(?:(?P<v3>pro max|pro|plus|mini|e)(?![a-z]))?')

def extract_models(text):
    """[(family, variant)] mentioned explicitly in this message, in order."""
    found = []
    for m in MODEL.finditer(canonical(text)):
        if m['f1']:
            family, variant = m['f1'], VARIANTS.get(m['v1'] or '', 'base')
        elif m['named']:
            family, variant = ('17', 'air') if m['named'] == 'air' else (m['named'].replace(' ', ''), 'base')
        elif m['f2']:
            family, variant = m['f2'], VARIANTS[m['v2']]
        else:
            family, variant = m['f3'], VARIANTS.get(m['v3'] or '', 'base')
        if (family, variant) not in found:
            found.append((family, variant))
    return found

SERVICES = [
    ('screen', r'หน้าจอ|จอ|screen|display|lcd|oled|ทัช'),
    ('battery', r'แบต|battery'),
    ('port_clean', r'ช่องชาร์จ|รูชาร์จ|ทำความสะอาด|port'),
    ('speaker', r'ลำโพง|speaker'),
    ('rear_camera', r'กล้อง|camera'),
    ('film', r'ฟิล์ม|กระจกกันรอย|film'),
    ('clear_case', r'เคสใส|เคสกันกระแทก|เคสมือถือ|เคสโทรศัพท์|clear case'),
    ('cable', r'สายชาร์จ|lightning|ไลท์นิ่?ง|usb\s*-?\s*c|type\s*-?\s*c|ไทป์ซี'),
    ('water_damage', r'ตกน้ำ|โดนน้ำ|น้ำเข้า|water'),
]

def extract_services(text):
    text = canonical(text)
    return [key for key, pattern in SERVICES if re.search(pattern, text)]

def luhn(digits):
    total, parity = 0, len(digits) % 2
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == parity:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0

def thai_id(digits):
    if len(digits) != 13 or digits[0] == '0':
        return False
    check = (11 - sum(int(digits[i]) * (13 - i) for i in range(12)) % 11) % 10
    return check == int(digits[12])

def card_scheme(digits):
    """Card brands by prefix and length; IMEI (15 digits, Luhn-valid) is not a card."""
    n, two, four = len(digits), int(digits[:2]), int(digits[:4])
    return ((digits[0] == '4' and n in (13, 16, 19)) or (51 <= two <= 55 and n == 16)
            or (2221 <= four <= 2720 and n == 16) or (two in (34, 37) and n == 15)
            or (3528 <= four <= 3589 and n == 16) or (two == 62 and 16 <= n <= 19)
            or ((four == 6011 or two == 65) and n == 16))

ID_WORDS = re.compile(r'ประชาชน|citizen|national\s*id|id\s*card', re.I)
NUMBER_RUN = re.compile(r'(?<![\d])\d(?:[ -]?\d){11,18}(?![\d])')

def inspect(text):
    """Mask payment cards and Thai national IDs before anything leaves the API."""
    flags, out = [], clean(text)
    def replace(match):
        digits = re.sub(r'\D', '', match.group())
        if card_scheme(digits) and luhn(digits) and not thai_id(digits):
            flags.append('card')
            return '[ซ่อนเลขบัตร]'
        if len(digits) == 13 and (thai_id(digits) or ID_WORDS.search(out)):
            flags.append('national_id')
            return '[ซ่อนเลขประจำตัว]'
        return match.group()
    out = NUMBER_RUN.sub(replace, out)
    if INJECTION.search(out):
        flags.append('injection')
    return out, sorted(set(flags))

# High-precision only: the router handles subtler attempts.
INJECTION = re.compile(r'ignore\s+(?:all\s+|any\s+)?(?:the\s+)?(?:previous|prior|above|earlier)\s+(?:instructions|rules|prompts?)|disregard\s+(?:all\s+|the\s+)?(?:previous|above|prior)|system\s*prompt|developer\s+mode|do\s+anything\s+now|\bDAN\s+mode|reveal\s+(?:your|the)\s+(?:prompt|instructions|context)|openai_api_key|api[\s_-]?key|ลืม(?:คำสั่ง|กฎ)|ไม่ต้อง(?:สนใจ|ทำตาม)(?:คำสั่ง|กฎ)|เพิกเฉย(?:ต่อ)?(?:คำสั่ง|กฎ)|(?:แสดง|บอก|เปิดเผย|พิมพ์)\s*(?:system\s*)?prompt|คำสั่งระบบ', re.I)

TIME_WORDS = re.compile(r'วันนี้|พรุ่งนี้|มะรืน|ตอนนี้|ขณะนี้|เดี๋ยวนี้|คืนนี้|เย็นนี้|พรุ่ง|today|tomorrow|\bnow\b', re.I)

def time_sensitive(text):
    return bool(TIME_WORDS.search(clean(text)))
