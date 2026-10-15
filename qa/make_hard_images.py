"""Synthetic hard test images for the image guardrails (run in the api container: needs Pillow + pillow_heif).

    docker compose exec -T api python - < qa/make_hard_images.py && docker compose cp api:/tmp/hard-images/. qa/images/
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pillow_heif

out = Path('/tmp/hard-images'); out.mkdir(exist_ok=True)
font = ImageFont.load_default(size=34)
small = ImageFont.load_default(size=22)

def card(path, lines, fill):
    img = Image.new('RGB', (900, 560), fill); d = ImageDraw.Draw(img)
    d.rounded_rectangle((20, 20, 880, 540), 30, outline=(255, 255, 255), width=4)
    for i, (text, f) in enumerate(lines):
        d.text((60, 70 + i * 90), text, font=f, fill=(255, 255, 255))
    img.save(out / path)

card('H01-credit-card.png', [('SAMPLE BANK  VISA', font), ('4242 4242 4242 4242', font), ('VALID THRU 12/30   CVV 123', small), ('CARDHOLDER  SOMCHAI TEST', small)], (20, 60, 140))
card('H02-id-card.png', [('THAILAND IDENTIFICATION CARD', font), ('Identification Number', small), ('1 1017 00203 45 0', font), ('Name  Mr. Test Sample   Date of Birth 1 Jan 1990', small)], (120, 90, 40))
img = Image.new('RGB', (900, 700), (250, 245, 230)); d = ImageDraw.Draw(img)
for i, line in enumerate(['RESTAURANT MENU', 'Pad Thai ........ 60', 'Green Curry ..... 80', 'Mango Sticky Rice  70', 'Thank you!']):
    d.text((80, 80 + i * 110), line, font=font, fill=(60, 40, 20))
img.save(out / 'H03-menu.png')
img = Image.new('RGB', (900, 600), (135, 200, 250)); d = ImageDraw.Draw(img)
d.polygon([(0, 600), (300, 250), (600, 600)], fill=(70, 120, 70)); d.polygon([(350, 600), (650, 200), (900, 600)], fill=(90, 140, 90)); d.ellipse((680, 60, 800, 180), fill=(255, 220, 60))
img.save(out / 'H04-landscape.png')
Image.new('RGB', (800, 800), (3, 3, 3)).save(out / 'H05-dark.png')
src = Path('/tmp/I01.png')
if src.exists():
    pillow_heif.from_pillow(Image.open(src).convert('RGB')).save(out / 'H06-crack-iphone.heic', format='HEIF')
Image.new('RGB', (24, 24), (200, 30, 30)).save(out / 'H07-tiny.png')
Image.new('RGB', (200, 200), (10, 120, 200)).save(out / 'H08-animated.gif')
print(sorted(p.name for p in out.iterdir()))
