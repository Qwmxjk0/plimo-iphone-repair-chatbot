"""Exact catalog prices for the model/service in a question, plus an answer check.

The LLM phrases the answer, but every amount it states must come from here.
"""
import itertools
import json
import os
import re
from pathlib import Path

CATALOG_PATH = os.getenv('CATALOG_PATH', '/app/catalog.json')
SUPPORTED = range(11, 18)
NAMED_VARIANTS = {'pro': 'Pro', 'pro_max': 'Pro Max', 'plus': 'Plus', 'mini': 'mini', 'e': 'e', 'air': 'Air'}
UNCONFIRMED = {'mini', 'plus', 'air', 'e'}
SERVICE_WORDS = [('screen', 'หน้าจอ'), ('battery', 'แบตเตอรี่'), ('port_clean', 'ช่องชาร์จ'), ('speaker', 'ลำโพง'),
                 ('rear_camera', 'กล้องหลัง'), ('film', 'ฟิล์ม'), ('clear_case', 'เคสใส'), ('cable', 'สายชาร์จ')]
SERVICE_NAMES = {'screen': 'เปลี่ยนหน้าจอ', 'battery': 'เปลี่ยนแบตเตอรี่', 'port_clean': 'ทำความสะอาดช่องชาร์จ', 'speaker': 'เปลี่ยนชุดลำโพง',
                 'rear_camera': 'เปลี่ยนชุดกล้องหลัง', 'film': 'ฟิล์มกระจก', 'clear_case': 'เคสใส', 'cable': 'สายชาร์จ', 'water_damage': 'ซ่อมเครื่องตกน้ำ/โดนน้ำ'}
COVERAGE = re.compile(r'iPhone\s*(\d+)(?:\s*[–-]\s*(\d+))?(\s*รวม\s*Pro\s*/\s*Pro Max)?')
_items = None

def model_name(family, variant):
    if variant == 'air':
        return 'iPhone Air'
    if variant == 'e':
        return f'iPhone {family}e'
    return f'iPhone {family}' + (' ' + NAMED_VARIANTS[variant] if variant in NAMED_VARIANTS else '')

def items():
    """Confirmed, non-demo catalog rows with parsed service and coverage."""
    global _items
    if _items is None:
        rows = []
        for item in json.loads(Path(CATALOG_PATH).read_text()):
            if item.get('confirmed') is not True or item.get('demo') is True or not isinstance(item.get('price'), (int, float)):
                continue
            service = next((key for key, word in SERVICE_WORDS if word in item['name']), None)
            families, variants = set(), {'base'}
            for text in item.get('models', []):
                m = COVERAGE.search(text)
                if m:
                    lo = int(m.group(1)); hi = int(m.group(2) or lo)
                    families.update(range(lo, hi + 1))
                    if m.group(3):
                        variants.update({'pro', 'pro_max'})
            rows.append({'name': item['name'], 'price': int(item['price']), 'service': service, 'families': families,
                         'variants': variants, 'coverage': ', '.join(item.get('models', [])), 'kind': item.get('kind')})
        _items = rows
    return _items

def baht(value):
    return f'{value:,} บาท'

def covers(item, family, variant):
    return family in item['families'] and variant in item['variants']

def lookup(models, services):
    """Facts for the prompt and the set of amounts an answer may state."""
    catalog = items()
    services = [s for s in dict.fromkeys(services or []) if s in SERVICE_NAMES]
    rows, priced, allowed = [], [], {0}
    valid_models = []
    for family, variant in dict.fromkeys(models or []):
        name = model_name(family, variant)
        if not family.isdigit() or int(family) not in SUPPORTED:
            rows.append(f'{name}: อยู่นอกรุ่นที่ร้านรับ (ร้านรับ iPhone 11–17 รวม Pro / Pro Max)')
        elif variant in UNCONFIRMED:
            rows.append(f'{name}: ยังไม่มีข้อมูลยืนยันว่าร้านรับรุ่นนี้หรือมีราคา ห้ามใช้ราคาของ iPhone {family} รุ่นปกติ ต้องสอบถามและตรวจเครื่องก่อน')
        else:
            valid_models.append((int(family), variant, name))
    if 'water_damage' in services:
        rows.append('ซ่อมเครื่องตกน้ำ/โดนน้ำ: ไม่มีรายการและราคาในระบบ ต้องตรวจเครื่องก่อน (ตรวจเช็คฟรีที่ร้าน) ห้ามประเมินราคาเอง')
    price_services = [s for s in services if s != 'water_damage']
    if valid_models and price_services:
        for family, variant, name in valid_models:
            for service in price_services:
                matches = [i for i in catalog if i['service'] == service and covers(i, family, variant)]
                if matches:
                    for item in matches:
                        rows.append(f"{item['name']} สำหรับ {name}: ราคาประเมินเบื้องต้นเริ่มต้น {baht(item['price'])} (รองรับ {item['coverage']})")
                        priced.append((family, variant, service, item['price']))
                elif any(i['service'] == service and family in i['families'] for i in catalog):
                    rows.append(f'{SERVICE_NAMES[service]} {name}: ไม่มีราคาในระบบ ต้องตรวจเครื่องเพื่อประเมินแยก ห้ามใช้ราคาของรุ่นปกติ')
                else:
                    rows.append(f'{SERVICE_NAMES[service]} {name}: ไม่มีรายการนี้สำหรับรุ่นดังกล่าวในระบบ')
            if service_has_alternatives(price_services, family):
                rows.extend(alternatives(family))
    elif price_services and not models:
        for service in price_services:
            for item in [i for i in catalog if i['service'] == service]:
                rows.append(f"{item['name']}: ราคาประเมินเบื้องต้นเริ่มต้น {baht(item['price'])} (รองรับ {item['coverage']})")
                allowed.add(item['price'])
        if any(s in ('screen', 'battery') for s in price_services):
            rows.append('ราคาหน้าจอและแบตเตอรี่ขึ้นกับรุ่น ถ้าลูกค้ายังไม่บอกรุ่น ให้ถามรุ่นเต็มก่อน และห้ามเลือกรุ่นให้เอง')
    elif valid_models:
        for family, variant, name in valid_models:
            for item in [i for i in catalog if covers(i, family, variant)]:
                rows.append(f"{item['name']} สำหรับ {name}: ราคาประเมินเบื้องต้นเริ่มต้น {baht(item['price'])}")
                allowed.add(item['price'])
            if variant in ('pro', 'pro_max'):
                rows.append(f'{name}: หน้าจอและแบตเตอรี่ต้องประเมินแยก ห้ามใช้ราคาของรุ่นปกติ')
    elif not models:
        allowed.update(i['price'] for i in catalog)
    allowed.update(p for *_, p in priced)
    # Totals for several services on one model, differences for one service across models.
    by_model = {}
    for family, variant, service, price in priced:
        by_model.setdefault((family, variant), []).append(price)
    for (family, variant), prices in by_model.items():
        if len(prices) >= 2:
            for r in range(2, len(prices) + 1):
                allowed.update(sum(c) for c in itertools.combinations(prices, r))
            rows.append(f'รวมราคาประเมินเบื้องต้นของ {model_name(str(family), variant)}: {baht(sum(prices))} (รวมราคาเริ่มต้นของแต่ละรายการ ไม่ใช่ราคาเหมา)')
    by_service = {}
    for family, variant, service, price in priced:
        by_service.setdefault(service, []).append((model_name(str(family), variant), price))
    for service, pairs in by_service.items():
        for (a, pa), (b, pb) in itertools.combinations(pairs, 2):
            if pa != pb:
                allowed.add(abs(pa - pb))
                rows.append(f'ส่วนต่างราคา{SERVICE_NAMES[service]} {a} กับ {b}: {baht(abs(pa - pb))}')
    return {'rows': rows, 'allowed': allowed, 'priced': priced}

def service_has_alternatives(services, family):
    return 'cable' in services

def alternatives(family):
    rows = []
    for item in [i for i in items() if i['service'] == 'cable']:
        fits = 'ใช้ได้' if family in item['families'] else 'ใช้ไม่ได้'
        rows.append(f"{item['name']} {fits}กับ iPhone {family} (รองรับ {item['coverage']})")
    return rows

AMOUNT = re.compile(r'(\d[\d,]*(?:\.\d+)?)(?:\s*(?:[-–]|ถึง|จนถึง|to)\s*(\d[\d,]*(?:\.\d+)?))?\s*(?:บาท|฿|thb)|(?:฿|thb)\s*(\d[\d,]*(?:\.\d+)?)', re.I)

def amounts(text):
    found = []
    for m in AMOUNT.finditer(text or ''):
        for g in m.groups():
            if g:
                found.append(float(g.replace(',', '')))
    return found

def unsupported_amounts(text, allowed):
    """Amounts stated in the answer that the catalog does not back."""
    return [a for a in amounts(text) if a not in allowed]

def price_answer(rows):
    """Plain fallback when the model's numbers fail validation."""
    lines = ['ข้อมูลราคาจากรายการของร้านครับ'] + ['- ' + r for r in rows]
    lines.append('ราคาที่แจ้งเป็นการประเมินเบื้องต้น ราคาสุทธิขึ้นกับผลตรวจและอะไหล่ หากมีค่าใช้จ่ายเพิ่ม ทางร้านจะแจ้งราคาใหม่ให้คุณอนุมัติก่อนเริ่มซ่อมครับ')
    return '\n'.join(lines)
