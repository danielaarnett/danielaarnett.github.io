from datetime import timedelta
import re

import pytest
from sqlalchemy import event

from app.extensions import db
from app.models import Chapter, User, Work, utcnow


@pytest.fixture
def tier_books(app):
    with app.app_context():
        for number, tier in enumerate(('witness', 'appreciator'), 10):
            book = Work(id=number, title=f'{tier}-exclusive', slug=tier, shelf='novellas',
                        minimum_tier=tier, is_visible=True, published_at=utcnow())
            db.session.add(book)
            db.session.add(Chapter(work_id=number, number=1, slug='chapter', title='Chapter',
                body=f'SECRET_{tier}', access_type='free', is_published=True, published_at=utcnow()))
        db.session.commit()


@pytest.mark.parametrize('tier,visible', [('free', []), ('witness', ['witness']),
                                        ('appreciator', ['witness', 'appreciator'])])
def test_profile_controls_shelves_and_direct_read(app, client, login, telegram_api, tier_books, tier, visible):
    telegram_api['status'] = 'left'
    with app.app_context():
        user = db.session.get(User, 1)
        user.subscription_tier = tier
        user.subscription_expires_at = utcnow() + timedelta(days=1)
        db.session.commit()
    login(1)
    result = client.get('/library?subscription_tier=appreciator')
    assert result.status_code == 200
    assert b'Test story' in result.data
    for level in ('witness', 'appreciator'):
        assert (f'{level}-exclusive'.encode() in result.data) == (level in visible)
        page = client.get(f'/read/{level}/chapter?tier=appreciator')
        assert page.status_code == (200 if level in visible else 403)
        assert (f'SECRET_{level}'.encode() in page.data) == (level in visible)
        assert client.get(f'/works/{level}').status_code == (200 if level in visible else 403)


@pytest.mark.parametrize('expired,enabled', [(True, True), (False, False)])
def test_expiry_and_disabled_subscriptions_revoke_grants(app, client, login, telegram_api, tier_books, expired, enabled):
    app.config['SUBSCRIPTIONS_ENABLED'] = enabled
    telegram_api['status'] = 'left'
    with app.app_context():
        user = db.session.get(User, 1)
        user.subscription_tier = 'appreciator'
        user.subscription_expires_at = utcnow() + timedelta(days=-1 if expired else 1)
        db.session.commit()
    login(1)
    assert b'appreciator-exclusive' not in client.get('/library/').data
    assert client.get('/read/appreciator/chapter').status_code == 403


def test_telegram_membership_does_not_grant_higher_tier(client, login, telegram_api, tier_books):
    login(2)
    assert client.get('/read/witness/chapter').status_code == 200
    assert client.get('/read/appreciator/chapter').status_code == 403


def test_anonymous_cannot_load_tier_body_even_with_free_chapter(app, client, tier_books):
    queries = []
    with app.app_context():
        engine = db.engine
        def capture(conn, cursor, statement, parameters, context, many):
            queries.append(statement)
        event.listen(engine, 'before_cursor_execute', capture)
    try:
        assert client.get('/read/appreciator/chapter?is_admin=true&tier=appreciator').status_code == 403
    finally:
        event.remove(engine, 'before_cursor_execute', capture)
    assert not any(re.search(r'chapter\.body\b', statement) for statement in queries)


def test_book_without_open_chapter_is_not_on_free_shelf(app, client):
    with app.app_context():
        for chapter in db.session.query(Chapter).all():
            chapter.access_type = 'subscriber'
        db.session.commit()
    assert b'Test story' not in client.get('/library').data
