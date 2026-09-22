import pytest

from app import create_app
from app.extensions import db
from app.models import Chapter, User, Work, utcnow


@pytest.fixture
def app(tmp_path):
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only-secret-not-used-for-deployment',
        'PRODUCTION': False, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'test.sqlite'),
        'SESSION_COOKIE_SECURE': False, 'SESSION_PROTECTION': None,
        'WTF_CSRF_ENABLED': False, 'RATELIMIT_ENABLED': False,
        'SUBSCRIPTIONS_ENABLED': True, 'TELEGRAM_BOT_TOKEN': 'test-token',
        'TELEGRAM_SUBSCRIBERS_CHAT_ID': '-100123',
        'TELEGRAM_CLIENT_ID': '123', 'TELEGRAM_CLIENT_SECRET': 'test-client-secret',
        'PUBLIC_BASE_URL': 'http://localhost', 'TRUSTED_HOSTS': ['localhost', '127.0.0.1'],
        'FINGERPRINT_ENABLED': True})
    with app.app_context():
        db.create_all()
        db.session.add_all([User(id=1, telegram_id=111, display_name='Reader'),
                            User(id=2, telegram_id=222, display_name='Member'),
                            User(id=3, telegram_id=333, display_name='Owner', is_admin=True)])
        work = Work(id=1, title='Test story', slug='story', is_visible=True, published_at=utcnow(), access_type='free')
        other = Work(id=2, title='Other story', slug='other', is_visible=True, published_at=utcnow(), access_type='free')
        db.session.add_all([work, other])
        for number, (slug, access, published) in enumerate([
            ('free', 'free', True), ('closed', 'subscriber', True),
            ('fragment', 'fragment', True), ('unpublished', 'free', False)
        ], 1):
            db.session.add(Chapter(id=number, work_id=1, number=number, slug=slug, title=slug,
                body='FULL_PRIVATE_' + slug, fragment_body='PUBLIC_FRAGMENT',
                is_published=published, published_at=utcnow() if published else None, access_type=access))
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login(client):
    def do_login(user_id):
        with client.session_transaction() as session:
            session['_user_id'] = str(user_id)
            session['_fresh'] = True
    return do_login


@pytest.fixture
def telegram_api(monkeypatch):
    state = {'status': 'member', 'calls': 0, 'error': None, 'wrong_id': False}
    def get(url, params, timeout):
        state['calls'] += 1
        if state['error']:
            raise state['error']
        class Response:
            def raise_for_status(self):
                pass
            def json(self):
                return {'ok': True, 'result': {'status': state['status'],
                    'user': {'id': -1 if state['wrong_id'] else params['user_id']}}}
        return Response()
    monkeypatch.setattr('app.services.access.requests.get', get)
    return state
