"""Stripe Checkout (test mode only) for repair quotes the member has approved.

The amount always comes from SQLite, card data never touches this server, and a
payment counts only after Stripe confirms it: by retrieving the session on
return, or by a webhook whose signature and timestamp verify.
"""
import hashlib
import hmac
import json
import logging
import os
import re
import time

from fastapi import APIRouter, HTTPException, Request

import membership
import net

router = APIRouter(prefix='/api')
logger = logging.getLogger('plimo.payments')
STRIPE_API = 'https://api.stripe.com/v1'
MIN_SATANG = 1000  # Stripe's minimum charge for THB is 10 baht.
SESSION_ID = re.compile(r'^cs_test_[A-Za-z0-9]{10,200}$')
WEBHOOK_TOLERANCE = 300
enabled = membership.payments_enabled

def base_url(request):
    configured = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')
    return configured or f"{request.url.scheme}://{request.headers.get('host', 'localhost')}"

async def stripe(method, path, **kwargs):
    response = await net.client().request(method, STRIPE_API + path, auth=(os.getenv('STRIPE_SECRET_KEY', ''), ''), **kwargs)
    if response.status_code >= 400:
        error = (response.json().get('error') or {}) if response.headers.get('content-type', '').startswith('application/json') else {}
        logger.warning('stripe_error status=%s type=%s code=%s', response.status_code, error.get('type'), error.get('code'))
        raise HTTPException(502, 'เชื่อมต่อระบบชำระเงินไม่สำเร็จ กรุณาลองใหม่อีกครั้ง')
    return response.json()

@router.post('/member/cases/{cid}/checkout')
async def checkout(cid: int, request: Request):
    u = membership.user(request)
    if not enabled():
        raise HTTPException(503, 'ร้านยังไม่เปิดชำระเงินออนไลน์')
    with membership.db() as c:
        case = c.execute('SELECT * FROM cases WHERE id=? AND user_id=?', (cid, u['id'])).fetchone()
        if not case:
            raise HTTPException(404, 'ไม่พบเคส')
        quote = c.execute('SELECT * FROM case_quotes WHERE case_id=? ORDER BY id DESC LIMIT 1', (cid,)).fetchone()
        if not quote or quote['status'] != 'approved' or case['status'] in ('cancelled', 'closed'):
            raise HTTPException(409, 'ชำระได้เฉพาะใบเสนอราคาล่าสุดที่คุณอนุมัติแล้ว')
        if c.execute("SELECT 1 FROM payments WHERE quote_id=? AND status='paid'", (quote['id'],)).fetchone():
            raise HTTPException(409, 'ใบเสนอราคานี้ชำระเงินแล้ว')
        pending = c.execute("SELECT checkout_url FROM payments WHERE quote_id=? AND user_id=? AND status='pending' AND created>? ORDER BY id DESC LIMIT 1",
                            (quote['id'], u['id'], time.time() - 1500)).fetchone()
    if pending and pending['checkout_url']:
        return {'url': pending['checkout_url']}
    amount = int(round(quote['amount'] * 100))
    if amount < MIN_SATANG:
        raise HTTPException(409, 'ยอดชำระต่ำกว่าขั้นต่ำของระบบชำระเงิน (10 บาท)')
    reference = f'PLM-{cid:05d}'
    window = int(time.time() // 600) * 600
    base = base_url(request)
    session = await stripe('POST', '/checkout/sessions', headers={'Idempotency-Key': f"plimo-checkout-{quote['id']}-{window}"}, data={
        'mode': 'payment', 'locale': 'th', 'line_items[0][quantity]': '1',
        'line_items[0][price_data][currency]': 'thb', 'line_items[0][price_data][unit_amount]': str(amount),
        'line_items[0][price_data][product_data][name]': f"ค่าซ่อม {reference} · {case['model']}",
        'line_items[0][price_data][product_data][description]': f"ใบเสนอราคา #{quote['id']} (โหมดทดสอบ ไม่มีการตัดเงินจริง)",
        'success_url': base + '/?payment=success&session_id={CHECKOUT_SESSION_ID}', 'cancel_url': base + '/?payment=cancelled',
        'client_reference_id': f"{cid}:{quote['id']}", 'expires_at': str(window + 2400),
        'metadata[case_id]': str(cid), 'metadata[quote_id]': str(quote['id']), 'metadata[user_id]': u['id'],
        'payment_intent_data[metadata][case_id]': str(cid), 'payment_intent_data[metadata][quote_id]': str(quote['id']),
    })
    url = session.get('url', '')
    if session.get('livemode') or not url.startswith('https://checkout.stripe.com/') or not SESSION_ID.match(session.get('id', '')):
        logger.error('stripe_session_rejected livemode=%s', session.get('livemode'))
        raise HTTPException(502, 'ระบบชำระเงินตอบกลับไม่ถูกต้อง')
    now = time.time()
    with membership.db() as c:
        c.execute("INSERT OR IGNORE INTO payments(case_id,quote_id,user_id,amount_satang,currency,session_id,checkout_url,status,created,updated) VALUES(?,?,?,?,?,?,?,'pending',?,?)",
                  (cid, quote['id'], u['id'], amount, 'thb', session['id'], url, now, now))
    logger.info('checkout_created case=%s quote=%s', cid, quote['id'])
    return {'url': url}

def apply_session(session):
    """Mark a payment paid only when every field matches what we created. Idempotent."""
    metadata = session.get('metadata') or {}
    with membership.db() as c:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute('SELECT * FROM payments WHERE session_id=?', (session.get('id'),)).fetchone()
        if not row:
            return None
        if row['status'] == 'paid':
            return row
        matches = (session.get('livemode') is False and session.get('status') == 'complete' and session.get('payment_status') == 'paid'
                   and session.get('amount_total') == row['amount_satang'] and str(session.get('currency', '')).lower() == row['currency']
                   and metadata.get('case_id') == str(row['case_id']) and metadata.get('quote_id') == str(row['quote_id'])
                   and metadata.get('user_id') == row['user_id'])
        now = time.time()
        if matches:
            case = c.execute('SELECT status FROM cases WHERE id=?', (row['case_id'],)).fetchone()
            c.execute("UPDATE payments SET status='paid',paid_at=?,updated=? WHERE id=?", (now, now, row['id']))
            c.execute('INSERT INTO case_events(case_id,actor,status,note,created) VALUES(?,?,?,?,?)',
                      (row['case_id'], row['user_id'], case['status'], f"ชำระเงินแล้ว {row['amount_satang'] / 100:,.2f} บาท (Stripe โหมดทดสอบ · ใบเสนอ #{row['quote_id']})", now))
            c.execute('UPDATE cases SET updated=? WHERE id=?', (now, row['case_id']))
            logger.info('payment_paid case=%s quote=%s', row['case_id'], row['quote_id'])
        elif session.get('status') == 'expired':
            c.execute("UPDATE payments SET status='expired',updated=? WHERE id=? AND status='pending'", (now, row['id']))
        elif session.get('payment_status') == 'paid':
            logger.error('payment_mismatch payment=%s', row['id'])
            c.execute("UPDATE payments SET status='failed',updated=? WHERE id=?", (now, row['id']))
        return c.execute('SELECT * FROM payments WHERE id=?', (row['id'],)).fetchone()

@router.get('/member/payments/confirm')
async def confirm(session_id: str, request: Request):
    u = membership.user(request)
    if not SESSION_ID.match(session_id):
        raise HTTPException(422, 'รหัสการชำระเงินไม่ถูกต้อง')
    with membership.db() as c:
        row = c.execute('SELECT * FROM payments WHERE session_id=? AND user_id=?', (session_id, u['id'])).fetchone()
    if not row:
        raise HTTPException(404, 'ไม่พบรายการชำระเงิน')
    if row['status'] != 'paid':
        # Never trust the redirect itself: ask Stripe what actually happened.
        row = apply_session(await stripe('GET', '/checkout/sessions/' + session_id)) or row
    return {'status': row['status'], 'case_id': row['case_id'], 'reference': f"PLM-{row['case_id']:05d}", 'amount': row['amount_satang'] / 100}

def verify_signature(payload, header, secret, now=None):
    parts = [p.split('=', 1) for p in header.split(',') if '=' in p]
    stamp = next((v for k, v in parts if k == 't'), '')
    if not stamp.isdigit() or abs((now or time.time()) - int(stamp)) > WEBHOOK_TOLERANCE:
        return False
    expected = hmac.new(secret.encode(), stamp.encode() + b'.' + payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, v) for k, v in parts if k == 'v1')

@router.post('/stripe/webhook')
async def webhook(request: Request):
    secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    if not secret:
        raise HTTPException(503, 'webhook is not configured')
    payload = await request.body()
    if len(payload) > 512_000 or not verify_signature(payload, request.headers.get('stripe-signature', ''), secret):
        logger.warning('webhook_rejected')
        raise HTTPException(400, 'invalid signature')
    event = json.loads(payload)
    if event.get('livemode'):
        return {'ignored': 'livemode'}
    with membership.db() as c:
        if c.execute('INSERT OR IGNORE INTO stripe_events(id,type,received) VALUES(?,?,?)', (event.get('id'), event.get('type', ''), time.time())).rowcount == 0:
            return {'duplicate': True}
    if event.get('type') in ('checkout.session.completed', 'checkout.session.async_payment_succeeded', 'checkout.session.expired'):
        apply_session((event.get('data') or {}).get('object') or {})
    return {'received': True}
