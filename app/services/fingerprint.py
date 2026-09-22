import hashlib
import hmac
import re
import secrets

from flask import current_app

from ..extensions import db
from ..models import FingerprintReceipt


def signature(receipt_id):
    return hmac.new(current_app.secret_key.encode(), ('receipt:' + receipt_id).encode(), hashlib.sha256).hexdigest()


def apply(html, user_id, chapter_id):
    """Opaque, removable receipt. It is attribution assistance, never access control."""
    receipt_id = secrets.token_hex(16)
    token = receipt_id + signature(receipt_id)
    db.session.add(FingerprintReceipt(id=receipt_id, user_id=user_id, chapter_id=chapter_id))
    db.session.commit()
    bits = ''.join(f'{byte:08b}' for byte in bytes.fromhex(token))
    invisible = '\u2063' + bits.translate(str.maketrans('01', '\u200b\u200c')) + '\u2063'
    marker = f'<span aria-hidden="true" class="receipt" data-receipt="{token}">{invisible}</span>'
    return html.replace('</p>', marker + '</p>', 1) if '</p>' in html else html + marker


def identify(text):
    match = re.search(r'data-receipt="([0-9a-f]{96})"', text)
    if match:
        token = match[1]
    else:
        match = re.search('\u2063([\u200b\u200c]{384})\u2063', text)
        if not match:
            return None
        bits = match[1].translate(str.maketrans('\u200b\u200c', '01'))
        token = bytes(int(bits[i:i+8], 2) for i in range(0, 384, 8)).hex()
    receipt_id = token[:32]
    if not hmac.compare_digest(token[32:], signature(receipt_id)):
        return None
    return db.session.get(FingerprintReceipt, receipt_id)
