import hashlib
import hmac
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from authlib.integrations.flask_client import OAuth
from flask import Flask, abort, g, redirect, render_template, request, send_from_directory
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix

from config import ROOT, settings
from .extensions import csrf, db, limiter, login_manager, migrate


def create_app(test_config=None):
    app = Flask(__name__, instance_path=str(ROOT / 'instance'))
    app.config.update(settings())
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(exist_ok=True)
    if not app.config['SECRET_KEY']:
        if app.config['PRODUCTION']:
            raise RuntimeError('Set a random SECRET_KEY before production startup')
        key_path = Path(app.instance_path) / 'development-secret'
        if not key_path.exists():
            key_path.write_text(secrets.token_hex(32), encoding='ascii')
        app.config['SECRET_KEY'] = key_path.read_text(encoding='ascii').strip()
    if app.config['PRODUCTION']:
        if len(app.secret_key) < 32:
            raise RuntimeError('SECRET_KEY must contain at least 32 random characters')
        if not app.config['PUBLIC_BASE_URL'].startswith('https://'):
            raise RuntimeError('Production PUBLIC_BASE_URL must use HTTPS')
        if app.config['RATELIMIT_STORAGE_URI'] == 'memory://':
            raise RuntimeError('Configure shared Redis rate limit storage for production')
        if app.debug or not app.config['SESSION_COOKIE_SECURE']:
            raise RuntimeError('Production requires DEBUG=False and Secure cookies')
    if app.config['TRUST_PROXY']:
        # Enable only behind one trusted proxy; bind WSGI to loopback/private socket.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=0)
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.session_protection = 'strong'
    limiter.init_app(app)
    oauth = OAuth(app)
    oauth.register('telegram', client_id=app.config['TELEGRAM_CLIENT_ID'],
                   client_secret=app.config['TELEGRAM_CLIENT_SECRET'],
                   server_metadata_url='https://oauth.telegram.org/.well-known/openid-configuration',
                   client_kwargs={'scope': 'openid profile', 'code_challenge_method': 'S256',
                                  'token_endpoint_auth_method': 'client_secret_basic', 'timeout': 8})
    app.extensions['telegram_oauth'] = oauth

    from .models import ReadAudit, User
    from .auth import bp as auth_bp
    from .library import bp as library_bp
    from .admin import bp as admin_bp
    from .cli import register_commands
    app.register_blueprint(auth_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(admin_bp)
    register_commands(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
            return None

    @app.before_request
    def require_https():
        if app.config['PRODUCTION'] and not request.is_secure:
            if request.method not in {'GET', 'HEAD'}:
                abort(400)
            return redirect(app.config['PUBLIC_BASE_URL'] + request.full_path.rstrip('?'), code=308)

    @app.after_request
    def security_headers(response):
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; "
            "form-action 'self' https://oauth.telegram.org; frame-ancestors 'none'"
        )
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if app.config['PRODUCTION']:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        if request.endpoint != 'static' and not request.path.startswith(('/css/', '/fonts/', '/images/', '/js/')):
            response.headers['Cache-Control'] = 'private, no-store'
            response.vary.add('Cookie')
        if request.path.startswith('/read/'):
            ip_hash = hmac.new(app.secret_key.encode(), ('audit:' + (request.remote_addr or '')).encode(), hashlib.sha256).hexdigest()
            try:
                db.session.add(ReadAudit(user_id=current_user.id if current_user.is_authenticated else None,
                    chapter_id=getattr(g, 'chapter_id', None), ip_hash=ip_hash,
                    user_agent=request.user_agent.string[:180], route=request.path[:260], status_code=response.status_code))
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                app.logger.warning('Read audit write failed')
        return response

    @app.context_processor
    def site_context():
        boosty = app.config['BOOSTY_URL']
        parsed = urlsplit(boosty)
        boosty = boosty if parsed.scheme == 'https' and parsed.hostname == 'boosty.to' else ''
        return dict(telegram_enabled=bool(app.config['TELEGRAM_CLIENT_ID'] and app.config['TELEGRAM_CLIENT_SECRET']),
                    subscriptions_enabled=app.config['SUBSCRIPTIONS_ENABLED'], boosty_url=boosty,
                    access_labels={'free': 'Бесплатно', 'fragment': 'Ознакомительный фрагмент', 'subscriber': 'Для читательского круга'},
                    status_labels={'draft': 'Черновик', 'ongoing': 'В работе', 'completed': 'Завершено'})

    # Only these public asset directories are mounted. Never expose the repo,
    # instance/, private_content/, templates/, a database or arbitrary files.
    @app.get('/<any(css,fonts,images,js):folder>/<path:filename>')
    @limiter.exempt
    def legacy_assets(folder, filename):
        allowed = {'css': {'.css'}, 'fonts': {'.woff2'}, 'js': {'.js'},
                   'images': {'.png', '.jpg', '.jpeg', '.svg', '.webp'}}
        if Path(filename).suffix.lower() not in allowed[folder]:
            abort(404)
        return send_from_directory(ROOT / folder, filename)

    @app.get('/reading.css')
    @app.get('/static-texture.webp')
    @limiter.exempt
    def reader_assets():
        return send_from_directory(ROOT, request.path.lstrip('/'))

    @app.get('/index.html')
    def old_home():
        return redirect('/', code=302)

    @app.get('/plans.html')
    def old_plans():
        return redirect('/library', code=302)

    @app.get('/health')
    @limiter.exempt
    def health():
        return {'status': 'ok'}

    @app.errorhandler(400)
    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def error_page(error):
        messages = {400: 'Запрос не принят. Обновите страницу и попробуйте ещё раз.',
                    401: 'Для этой страницы требуется вход.', 403: 'Эта страница пока недоступна.',
                    404: 'Страница не найдена или ещё не опубликована.',
                    413: 'Текст слишком большой. Разделите его на главы.',
                    429: 'Слишком много запросов. Немного подождите и продолжите чтение.'}
        return render_template('error.html', code=error.code, message=messages[error.code]), error.code

    return app
