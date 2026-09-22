import hashlib
from urllib.parse import urlsplit

from authlib.integrations.base_client.errors import OAuthError
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user
from requests import RequestException
from joserfc.errors import JoseError
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from ..extensions import db, limiter
from ..models import LocalLoginTicket, User, utcnow
from ..services.access import membership

bp = Blueprint('auth', __name__, url_prefix='/auth')


def safe_next(value):
    if not value or '\\' in value or any(ord(c) < 32 for c in value):
        return '/library'
    try:
        parsed = urlsplit(value)
    except ValueError:
        return '/library'
    if parsed.scheme or parsed.netloc or not value.startswith('/') or value.startswith('//'):
        return '/library'
    return value


def enabled():
    return bool(current_app.config['TELEGRAM_CLIENT_ID'] and current_app.config['TELEGRAM_CLIENT_SECRET'])


@bp.get('/login')
def login():
    return render_template('auth/login.html', next_url=safe_next(request.args.get('next')))


@bp.post('/telegram')
@limiter.limit('10 per minute')
def telegram():
    if not enabled():
        abort(404)
    session['after_login'] = safe_next(request.form.get('next'))
    callback = current_app.config['PUBLIC_BASE_URL'] + url_for('auth.callback')
    return current_app.extensions['telegram_oauth'].telegram.authorize_redirect(callback)


@bp.get('/callback')
@limiter.limit('10 per minute')
def callback():
    if not enabled():
        abort(404)
    try:
        # Authlib checks state, PKCE, signature, issuer, audience, nonce and exp.
        token = current_app.extensions['telegram_oauth'].telegram.authorize_access_token()
        info = token['userinfo']
        telegram_id = info.get('id')  # profile.id, NOT the distinct OIDC sub!
        subject = info.get('sub')
        if type(telegram_id) is not int or not 0 < telegram_id < 2**63:
            raise ValueError('Invalid Telegram ID')
        if not isinstance(subject, str) or not 0 < len(subject) <= 128:
            raise ValueError('Invalid OIDC subject')
        user = db.session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user and user.oidc_subject and user.oidc_subject != subject:
            raise ValueError('Identity mismatch')
        if not user:
            user = User(telegram_id=telegram_id)
            db.session.add(user)
        user.oidc_subject = subject
        user.username = str(info.get('preferred_username', ''))[:128]
        user.display_name = str(info.get('name', 'Читатель'))[:160]
        user.last_login_at = utcnow()
        user.membership_checked_at = None
        db.session.commit()
    except (OAuthError, JoseError, RequestException, ValueError, KeyError, TypeError, IntegrityError):
        db.session.rollback()
        # Avoid echoing tokens, provider URLs or callback query strings.
        abort(401)
    next_url = safe_next(session.get('after_login'))
    session.clear()
    login_user(user)
    session.permanent = True
    membership(user)
    return redirect(next_url)


@bp.post('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect('/')


@bp.route('/local', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def local_login():
    # CLI-issued, one-use owner login for localhost development only.
    if current_app.config['PRODUCTION'] or request.remote_addr not in {'127.0.0.1', '::1'}:
        abort(404)
    if urlsplit(request.host_url).hostname not in {'127.0.0.1', 'localhost', '::1'}:
        abort(404)
    token = request.args.get('token', '') if request.method == 'GET' else request.form.get('ticket', '')
    if not token or len(token) > 200:
        abort(403)
    digest = hashlib.sha256(token.encode()).hexdigest()
    ticket = db.session.get(LocalLoginTicket, digest)
    if not ticket or ticket.expires_at <= utcnow():
        abort(403)
    if request.method == 'POST':
        user = db.session.get(User, ticket.user_id)
        if not user or not user.is_admin:
            abort(403)
        result = db.session.execute(delete(LocalLoginTicket).where(LocalLoginTicket.id == digest,
                                                                  LocalLoginTicket.expires_at > utcnow()))
        if result.rowcount != 1:
            abort(403)
        db.session.commit()
        session.clear()
        login_user(user)
        session.permanent = True
        return redirect(url_for('admin.dashboard'))
    return render_template('auth/local.html', ticket=token)
