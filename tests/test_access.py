import re
from datetime import timedelta

import pytest
import requests
from sqlalchemy import event, select

from app.extensions import db
from app.models import Chapter, ReadingProgress, User, Work, utcnow


def test_anonymous_free_chapter(client):
    r = client.get('/read/story/free')
    assert r.status_code == 200
    assert b'FULL_PRIVATE_free' in r.data
    assert r.headers['Cache-Control'] == 'private, no-store'
    assert 'Cookie' in r.headers['Vary']


def test_anonymous_closed_never_loads_full_body(app, client):
    statements = []
    with app.app_context():
        engine = db.engine
        def capture(conn, cursor, statement, parameters, context, many):
            statements.append(statement)
        event.listen(engine, 'before_cursor_execute', capture)
    r = client.get('/read/story/closed')
    event.remove(engine, 'before_cursor_execute', capture)
    assert r.status_code == 403
    assert b'FULL_PRIVATE' not in r.data
    assert not any(re.search(r'chapter\.body\b', sql) for sql in statements)


def test_fragment_selects_only_public_fragment(app, client):
    statements = []
    with app.app_context():
        engine = db.engine
        def capture(conn, cursor, statement, parameters, context, many):
            statements.append(statement)
        event.listen(engine, 'before_cursor_execute', capture)
    r = client.get('/read/story/fragment')
    event.remove(engine, 'before_cursor_execute', capture)
    assert r.status_code == 200 and b'PUBLIC_FRAGMENT' in r.data
    assert b'FULL_PRIVATE' not in r.data
    assert any('chapter.fragment_body' in sql for sql in statements)
    assert not any(re.search(r'chapter\.body\b', sql) for sql in statements)


@pytest.mark.parametrize('status', ['left', 'kicked', 'restricted', 'unknown'])
def test_logged_in_non_member_denied(client, login, telegram_api, status):
    login(1)
    telegram_api['status'] = status
    r = client.get('/read/story/closed')
    assert r.status_code == 403 and b'FULL_PRIVATE' not in r.data


@pytest.mark.parametrize('status', ['creator', 'administrator', 'member'])
def test_subscriber_reads_closed_and_fragment(client, login, telegram_api, status):
    login(2)
    telegram_api['status'] = status
    r = client.get('/read/story/closed')
    assert r.status_code == 200 and b'FULL_PRIVATE_closed' in r.data
    assert b'data-receipt=' in r.data and b'data-protected="true"' in r.data
    assert b'FULL_PRIVATE_fragment' in client.get('/read/story/fragment').data
    assert telegram_api['calls'] == 1


def test_expired_membership_rechecked_and_revoked(app, client, login, telegram_api):
    login(2)
    assert client.get('/read/story/closed').status_code == 200
    with app.app_context():
        db.session.get(User, 2).membership_checked_at = utcnow() - timedelta(seconds=301)
        db.session.commit()
    telegram_api['status'] = 'left'
    r = client.get('/read/story/closed')
    assert r.status_code == 403 and b'FULL_PRIVATE' not in r.data
    assert telegram_api['calls'] == 2


def test_outage_fails_closed_after_cache_expiry(app, client, login, telegram_api):
    login(2)
    assert client.get('/read/story/closed').status_code == 200
    with app.app_context():
        db.session.get(User, 2).membership_checked_at = utcnow() - timedelta(minutes=6)
        db.session.commit()
    telegram_api['error'] = requests.Timeout()
    r = client.get('/read/story/closed')
    assert r.status_code == 403 and b'FULL_PRIVATE' not in r.data
    assert b'FULL_PRIVATE' not in client.get('/read/story/fragment').data


def test_wrong_membership_identity_denied(client, login, telegram_api):
    login(2)
    telegram_api['wrong_id'] = True
    assert client.get('/read/story/closed').status_code == 403


def test_disabled_boosty_never_calls_provider(app, client, login, telegram_api):
    app.config['SUBSCRIPTIONS_ENABLED'] = False
    login(2)
    assert client.get('/read/story/closed').status_code == 403
    assert telegram_api['calls'] == 0


@pytest.mark.parametrize('path', ['/read/story/unpublished', '/read/other/closed', '/read/story/2',
    '/read/1/2', '/api/chapters/2', '/api/works/1/chapters', '/api/chapters',
    '/static/private/book.txt', '/private_content/book.txt', '/instance/library.sqlite',
    '/app/templates/home.html', '/css/../instance/library.sqlite'])
def test_hidden_guessed_numeric_and_bulk_urls(client, path):
    r = client.get(path)
    assert r.status_code == 404 and b'FULL_PRIVATE' not in r.data


def test_hidden_work_and_future_chapter(app, client):
    with app.app_context():
        db.session.get(Work, 1).is_visible = False
        db.session.commit()
    assert client.get('/read/story/free').status_code == 404
    with app.app_context():
        db.session.get(Work, 1).is_visible = True
        db.session.get(Chapter, 1).published_at = utcnow() + timedelta(days=1)
        db.session.commit()
    assert client.get('/read/story/free').status_code == 404


def test_wholly_closed_work_overrides_chapter_free(app, client):
    with app.app_context():
        db.session.get(Work, 1).access_type = 'subscriber'
        db.session.commit()
    assert client.get('/read/story/free').status_code == 403


def test_query_id_or_subscription_flag_cannot_grant_access(client):
    r = client.get('/read/story/closed?telegram_id=222&user_id=2&is_subscriber=true&is_admin=true')
    assert r.status_code == 403 and b'FULL_PRIVATE' not in r.data


def test_progress_uses_logged_in_owner_and_checks_chapter(app, client, login, telegram_api):
    login(1)
    for malformed in ([1], 'invalid', True):
        assert client.post('/api/progress', json=malformed).status_code == 400
    telegram_api['status'] = 'left'
    data = {'chapter_id': 1, 'paragraph_id': 'p-1', 'scroll_position': 0.5, 'user_id': 2}
    assert client.post('/api/progress', json=data).status_code == 200
    with app.app_context():
        rows = list(db.session.scalars(select(ReadingProgress)))
        assert len(rows) == 1 and rows[0].user_id == 1
    data['chapter_id'] = 2
    assert client.post('/api/progress', json=data).status_code == 403
    data['chapter_id'] = 4
    assert client.post('/api/progress', json=data).status_code == 404


@pytest.mark.parametrize('position', [-1, 2, '0.5', True, float('nan')])
def test_invalid_progress(client, login, position):
    login(1)
    assert client.post('/api/progress', json={'chapter_id': 1, 'paragraph_id': 'p-1', 'scroll_position': position}).status_code == 400
