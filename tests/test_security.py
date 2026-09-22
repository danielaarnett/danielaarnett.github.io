import hashlib
import re
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from app import create_app
from app.auth import safe_next
from app.extensions import db
from app.models import Chapter, FingerprintReceipt, LocalLoginTicket, ReadAudit, User, utcnow
from app.services.content import count_words, render_content
from app.services.fingerprint import apply, identify


def test_forged_session_cookie(client):
    client.set_cookie('session', 'eyJfdXNlcl9pZCI6IjMiLCJpc19hZG1pbiI6dHJ1ZX0.fake.fake')
    assert client.get('/admin').status_code == 403
    assert client.get('/read/story/closed').status_code == 403


def test_admin_requires_owner_not_post_fields(client, login):
    assert client.get('/admin').status_code == 403
    login(1)
    assert client.get('/admin').status_code == 403
    assert client.post('/admin/works/new', data={'is_admin': 'true'}).status_code == 403


def test_admin_csrf_and_mutations(app, client, login):
    login(3)
    assert 'value="0"' in client.get('/admin/works/new').text
    assert 'value="1"' in client.get('/admin/works/1/chapters/new').text
    app.config['WTF_CSRF_ENABLED'] = True
    before = client.get('/admin/works/1/edit')
    assert before.status_code == 200
    assert client.post('/admin/works/1/edit', data={'title': 'CSRF ATTACK'}).status_code == 400
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', before.text)[1]
    r = client.post('/admin/works/1/edit', data={'csrf_token': token, 'title': 'Edited title',
        'slug': 'story', 'subtitle': 'Novel', 'description': 'Description', 'cover_path': '/images/art1.png',
        'cover_hover_path': '/images/art2.png', 'status': 'draft', 'access_type': 'free', 'sort_order': '0',
        'completion_percent': '50', 'is_visible': 'y'})
    assert r.status_code == 302
    with app.app_context():
        from app.models import Work
        assert db.session.get(Work, 1).title == 'Edited title'


def test_admin_chapter_parent_id_and_save(app, client, login):
    login(3)
    assert client.get('/admin/works/2/chapters/1/edit').status_code == 404
    assert client.get('/admin/works/1/chapters/1/edit').status_code == 200
    data = {'title': 'New chapter', 'slug': 'new-chapter', 'number': 8, 'sort_order': 8,
            'body_format': 'markdown', 'body': 'Open paragraph.\n\nSecret paragraph.',
            'access_type': 'fragment', 'fragment_blocks': 1, 'is_published': 'y'}
    r = client.post('/admin/works/1/chapters/new', data=data)
    assert r.status_code == 302
    page = client.get('/read/story/new-chapter')
    # Owner gets the whole text. Anonymous only gets the chosen first paragraph.
    assert 'Secret paragraph' in page.text
    with app.test_client() as anonymous:
        page = anonymous.get('/read/story/new-chapter')
        assert 'Open paragraph' in page.text and 'Secret paragraph' not in page.text


def test_xss_sanitized_on_read(app, client):
    with app.app_context():
        chapter = db.session.get(Chapter, 1)
        chapter.body_format = 'html'
        chapter.body = '<p onclick="alert(1)">Safe <em>text</em></p><script>alert(2)</script><img src=x onerror=alert(3)><a href="javascript:alert(4)">link</a><svg onload=alert(5)></svg>'
        db.session.commit()
    r = client.get('/read/story/free')
    for value in ('onclick=', 'javascript:', 'onerror=', 'onload=', 'alert('):
        assert value not in r.text
    assert '<em>text</em>' in r.text


def test_metadata_pages_do_not_expose_any_body(client):
    for path in ('/', '/library', '/works/story'):
        page = client.get(path)
        assert page.status_code == 200
        assert b'FULL_PRIVATE_' not in page.data
        assert b'PUBLIC_FRAGMENT' not in page.data
        assert b'unpublished' not in page.data


@pytest.mark.parametrize('value', ['https://evil.invalid', '//evil.invalid', '/\\evil.invalid', '\n//evil.invalid', 'javascript:alert(1)', '//[invalid'])
def test_open_redirect_rejected(value):
    assert safe_next(value) == '/library'


def test_valid_next_kept():
    assert safe_next('/read/story/free') == '/read/story/free'


def test_opaque_unique_fingerprint_with_trace(app):
    with app.app_context():
        first = apply('<p>A story</p>', 1, 1)
        second = apply('<p>A story</p>', 2, 1)
        assert first != second
        assert identify(first).user_id == 1
        assert identify(second).user_id == 2
        invisible = re.search('\u2063[\u200b\u200c]+\u2063', first)[0]
        assert identify(invisible).user_id == 1
        token = re.search(r'data-receipt="([^"]+)"', first)[1]
        tampered = token[:-1] + ('0' if token[-1] != '0' else '1')
        assert identify(f'<span data-receipt="{tampered}"></span>') is None
        assert identify('<p>No marker</p>') is None


def test_owner_invalidates_membership_cache(app, client, login):
    login(3)
    with app.app_context():
        user = db.session.get(User, 2)
        user.membership_status, user.membership_checked_at = 'member', utcnow()
        db.session.commit()
    assert client.post('/admin/users/2/invalidate').status_code == 302
    with app.app_context():
        assert db.session.get(User, 2).membership_checked_at is None


def test_local_owner_link_once_and_no_production(app, client):
    token = 'test-ticket'
    with app.app_context():
        db.session.add(LocalLoginTicket(id=hashlib.sha256(token.encode()).hexdigest(), user_id=3,
                                       expires_at=utcnow()+timedelta(minutes=10)))
        db.session.commit()
    assert client.post('/auth/local', data={'ticket': token}).status_code == 302
    assert client.post('/auth/local', data={'ticket': token}).status_code == 403
    app.config['PRODUCTION'] = True
    assert client.get('/auth/local?token=whatever', base_url='https://localhost').status_code == 404


def test_security_headers_and_content_not_public(client):
    r = client.get('/read/story/free')
    assert "frame-ancestors 'none'" in r.headers['Content-Security-Policy']
    assert "form-action 'self' https://oauth.telegram.org" in r.headers['Content-Security-Policy']
    assert r.headers['X-Content-Type-Options'] == 'nosniff'
    assert r.headers['Referrer-Policy'] == 'no-referrer'


def test_rate_limit_shared_across_chapter_slugs(tmp_path):
    a = create_app({'TESTING': True, 'PRODUCTION': False, 'SECRET_KEY': 'test-limits-key-12345678901234567890',
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'limits.sqlite'),
        'RATELIMIT_ENABLED': True, 'READ_RATE_LIMIT': '3 per minute', 'RATELIMIT_STORAGE_URI': 'memory://',
        'WTF_CSRF_ENABLED': False, 'TRUSTED_HOSTS': ['localhost']})
    with a.app_context():
        db.create_all()
        from app.models import Work
        db.session.add(Work(id=1, slug='story', title='Story', is_visible=True, published_at=utcnow()))
        db.session.commit()
    c = a.test_client()
    statuses = [c.get('/read/story/guess-' + str(i)).status_code for i in range(5)]
    assert statuses[:3] == [404] * 3
    assert statuses[3:] == [429] * 2
    with a.app_context():
        audit = list(db.session.scalars(select(ReadAudit)))
        assert len(audit) == 5 and audit[-1].status_code == 429
        assert audit[-1].ip_hash != '127.0.0.1'


def test_production_refuses_insecure_defaults():
    with pytest.raises(RuntimeError):
        create_app({'PRODUCTION': True, 'SECRET_KEY': ''})


def test_word_count_preserves_inline_words():
    assert count_words('<p>Од<em>но</em> слово.</p><p>Ещё два.</p>', 'html') == 4
