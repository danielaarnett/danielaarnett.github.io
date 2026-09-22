import time
from urllib.parse import parse_qs, urlsplit

import pytest
from joserfc import jwt
from joserfc.jwk import RSAKey
from sqlalchemy import select

from app.extensions import db
from app.models import User


@pytest.fixture
def oidc(app, monkeypatch):
    with app.app_context():
        remote = app.extensions['telegram_oauth'].telegram
    key = RSAKey.generate_key(2048, parameters={'kid': 'known'})
    metadata = {'issuer': 'https://oauth.telegram.org',
        'authorization_endpoint': 'https://oauth.telegram.org/auth',
        'token_endpoint': 'https://oauth.telegram.org/token',
        'id_token_signing_alg_values_supported': ['RS256'],
        'jwks': {'keys': [key.as_dict(private=False)]}}
    monkeypatch.setattr(remote, 'load_server_metadata', lambda: metadata)
    monkeypatch.setattr(remote, 'fetch_jwk_set', lambda **kwargs: metadata['jwks'])
    return remote, key


@pytest.mark.parametrize('failure', [None, 'signature', 'issuer', 'audience', 'expiry', 'nonce', 'missing-id'])
def test_oidc_callback_verifies_signed_identity(app, client, oidc, monkeypatch, telegram_api, failure):
    remote, key = oidc
    auth = client.post('/auth/telegram', data={'next': '/library'})
    assert auth.status_code == 302
    params = parse_qs(urlsplit(auth.location).query)
    assert params['code_challenge_method'] == ['S256']
    assert 'code_challenge' in params and 'nonce' in params and 'state' in params
    now = int(time.time())
    claims = {'iss': 'https://oauth.telegram.org', 'aud': '123', 'sub': 'distinct-oidc-subject',
              'id': 777, 'name': 'Verified reader', 'iat': now, 'exp': now + 600, 'nonce': params['nonce'][0]}
    if failure == 'issuer': claims['iss'] = 'https://evil.invalid'
    if failure == 'audience': claims['aud'] = 'wrong-app'
    if failure == 'expiry': claims['exp'] = now - 1000
    if failure == 'nonce': claims['nonce'] = 'wrong'
    if failure == 'missing-id': del claims['id']
    signing_key = RSAKey.generate_key(2048, parameters={'kid': 'known'}) if failure == 'signature' else key
    encoded = jwt.encode({'alg': 'RS256', 'kid': 'known'}, claims, signing_key)
    captured = {}
    def fetch(**kwargs):
        captured.update(kwargs)
        return {'access_token': 'unused-token', 'id_token': encoded, 'token_type': 'Bearer'}
    monkeypatch.setattr(remote, 'fetch_access_token', fetch)
    r = client.get('/auth/callback', query_string={'state': params['state'][0], 'code': 'test-code', 'telegram_id': 333})
    assert captured.get('code_verifier')
    assert r.status_code == (401 if failure else 302)
    with app.app_context():
        user = db.session.scalar(select(User).where(User.telegram_id == 777))
        if failure:
            assert user is None
        else:
            assert user.oidc_subject == 'distinct-oidc-subject' and not user.is_admin
    # State is one-use, so a replay is rejected even with a valid ID token.
    assert client.get('/auth/callback', query_string={'state': params['state'][0], 'code': 'test-code'}).status_code == 401


def test_unsigned_telegram_id_and_unknown_state_rejected(client):
    r = client.get('/auth/callback?telegram_id=333&username=owner&state=forged&code=fake')
    assert r.status_code == 401
