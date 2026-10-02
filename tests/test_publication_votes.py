from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import PublicationInterest, PublicationVote, utcnow


@pytest.fixture
def voting(app):
    with app.app_context():
        db.session.add(PublicationInterest(slug='krampus', votes=0))
        db.session.commit()


def test_persistent_total_and_hourly_ip_limit(app, client, voting, monkeypatch):
    now = utcnow()
    monkeypatch.setattr('app.publication.utcnow', lambda: now)
    assert client.post('/api/publication/krampus').json['votes'] == 1
    assert client.post('/api/publication/krampus').status_code == 429
    # Spoofing a header does not change the IP when no trusted proxy is configured.
    assert client.post('/api/publication/krampus', headers={'X-Forwarded-For': '8.8.8.8'}).status_code == 429
    assert client.get('/api/publication/krampus').json['votes'] == 1
    assert client.post('/api/publication/krampus', environ_overrides={'REMOTE_ADDR': '192.0.2.8'}).json['votes'] == 2
    monkeypatch.setattr('app.publication.utcnow', lambda: now + timedelta(seconds=3599))
    assert client.post('/api/publication/krampus').status_code == 429
    monkeypatch.setattr('app.publication.utcnow', lambda: now + timedelta(hours=1))
    assert client.post('/api/publication/krampus').json['votes'] == 3
    with app.app_context():
        rows = list(db.session.scalars(select(PublicationVote)))
        assert len(rows) == 2 and all(len(row.ip_hash) == 64 for row in rows)


def test_parallel_first_votes_are_counted_once(app, voting):
    def submit(_):
        with app.test_client() as client:
            return client.post('/api/publication/krampus').status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, range(2))) == [200, 429]
    with app.app_context():
        assert db.session.get(PublicationInterest, 'krampus').votes == 1


def test_vote_requires_csrf(app, client, voting):
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.post('/api/publication/krampus').status_code == 400
    token = client.get('/api/publication/krampus').json['csrf_token']
    assert client.post('/api/publication/krampus', headers={'X-CSRFToken': token}).status_code == 200
