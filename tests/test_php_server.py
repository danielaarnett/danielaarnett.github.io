"""Integration checks against the real PHP server and isolated SQLite stores."""
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
PHP = os.environ.get('PHP_BINARY') or shutil.which('php') or str(ROOT / 'local-qa/php-runtime/php.exe')


@pytest.fixture
def server(tmp_path):
    if not Path(PHP).is_file() or not (ROOT / 'php-app/vendor/autoload.php').is_file():
        pytest.fail('Install PHP and run composer install in php-app before testing.')
    private = tmp_path / 'private'
    private.mkdir()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    (private / 'config.php').write_text("<?php return ['production'=>false,'base_url'=>'" + base + "','secret'=>'test-secret-only-not-a-production-secret','subscriptions_enabled'=>true];", encoding='utf-8')
    env = dict(os.environ, ARNETT_PRIVATE_DIR=str(private))
    if os.name != 'nt':
        env['PHP_CLI_SERVER_WORKERS'] = '4'
    subprocess.run([PHP, str(ROOT / 'php-app/bin/console.php'), 'init'], env=env, cwd=ROOT, check=True, capture_output=True)
    subprocess.run([PHP, str(ROOT / 'php-app/bin/console.php'), 'user:add', 'owner', '--admin', '--password-stdin'], env=env, cwd=ROOT, input='test-owner-password-12345', text=True, check=True, capture_output=True)
    subprocess.run([PHP, str(ROOT / 'php-app/bin/console.php'), 'user:add', 'reader', '--password-stdin'], env=env, cwd=ROOT, input='test-reader-password-12345', text=True, check=True, capture_output=True)
    connection = sqlite3.connect(private / 'library.sqlite')
    connection.execute("INSERT INTO works(slug,title,minimum_tier,is_visible,published_at,updated_at) VALUES('closed','PRIVATE TITLE','appreciator',1,1,1)")
    work = connection.execute("SELECT id FROM works WHERE slug='closed'").fetchone()[0]
    connection.execute("INSERT INTO chapters(work_id,slug,title,body,fragment_body,access_type,is_published,published_at) VALUES(?, 'chapter','Chapter','TOP_SECRET_FULL_BODY','ONLY_PUBLIC_FRAGMENT','fragment',1,1)", (work,))
    connection.commit()
    connection.close()
    log = (tmp_path / 'php.log').open('w', encoding='utf-8')
    process = subprocess.Popen([PHP, '-S', f'127.0.0.1:{port}', '-t', str(ROOT), str(ROOT / 'tests/php_router.php')], cwd=ROOT, env=env, stdout=log, stderr=log)
    session = requests.Session()
    try:
        for _ in range(100):
            try:
                if session.get(base + '/', timeout=1).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(.1)
        else:
            pytest.fail('PHP did not start: ' + (tmp_path / 'php.log').read_text(encoding='utf-8'))
        yield base, session, private, env
    finally:
        process.terminate()
        process.wait(timeout=10)
        log.close()


def token(response):
    return re.search(r'name="csrf-token" content="([a-f0-9]+)"', response.text)[1]


def login(base, session, name='owner'):
    csrf = token(session.get(base + '/auth/login'))
    return session.post(base + '/auth/login', data={'username': name, 'password': f'test-{name}-password-12345', 'csrf_token': csrf}, allow_redirects=False)


def test_php_reads_prologue_and_protects_closed_bodies(server):
    base, session, private, _ = server
    home = session.get(base + '/')
    assert home.status_code == 200
    assert 'https://games.danielarnett.com/' in home.text
    page = session.get(base + '/read/moya-slabost-moya-bol/prolog/')
    assert page.status_code == 200 and 'Широким ртом' in page.text
    assert 'data-save-url=""' in page.text
    assert 'private, no-store' == page.headers['Cache-Control']
    for path in ['/read/closed/chapter/', '/read/closed/chapter/index.html']:
        denied = session.get(base + path)
        assert denied.status_code == 403
        assert 'TOP_SECRET' not in denied.text
    assert 'TOP_SECRET' not in session.get(base + '/library/').text
    assert session.get(base + '/admin').status_code == 403
    assert session.get(base + '/arnett-private/library.sqlite').status_code == 404
    assert session.post(base + '/api/progress', json={'chapter_id': 1}).status_code == 400
    assert login(base, session).status_code == 303
    protected = session.get(base + '/read/closed/chapter/')
    assert protected.status_code == 200 and 'TOP_SECRET_FULL_BODY' in protected.text
    assert 'data-receipt=' in protected.text
    assert 'data-save-url="/api/progress"' in protected.text
    assert 'Истории и главы' in session.get(base + '/admin').text
    with sqlite3.connect(private / 'library.sqlite') as connection:
        connection.execute("UPDATE works SET minimum_tier='free' WHERE slug='closed'")
    anonymous = requests.get(base + '/read/closed/chapter/')
    assert anonymous.status_code == 200 and 'ONLY_PUBLIC_FRAGMENT' in anonymous.text and 'TOP_SECRET_FULL_BODY' not in anonymous.text


def test_php_votes_ip_cookie_hourly_limits_and_csrf(server):
    base, session, private, _ = server
    api = base + '/api/publication/krampus'
    status = session.get(api).json()
    assert status['votes'] == 0 and status['retry_after'] == 0
    assert session.post(api).status_code == 400
    assert session.post(api, headers={'X-CSRFToken': status['csrf_token']}).json()['votes'] == 1
    assert session.post(api, headers={'X-CSRFToken': status['csrf_token']}).status_code == 429
    # Keeping the browser cookie while changing IP does not bypass the hour.
    assert session.post(api, headers={'X-CSRFToken': status['csrf_token'], 'X-Test-Remote-Addr': '192.0.2.10'}).status_code == 429
    # Clearing all cookies while keeping the IP does not bypass the hour either.
    fresh = requests.Session()
    fresh_token = fresh.get(api).json()['csrf_token']
    assert fresh.post(api, headers={'X-CSRFToken': fresh_token}).status_code == 429
    other = requests.Session()
    other.headers['X-Test-Remote-Addr'] = '192.0.2.20'
    other_token = other.get(api).json()['csrf_token']
    assert other.post(api, headers={'X-CSRFToken': other_token}).json()['votes'] == 2
    assert other.post(api, headers={'X-CSRFToken': other_token, 'X-Forwarded-For': '8.8.8.8'}).status_code == 429
    second = base + '/api/publication/orden-na-sdachu'
    second_token = session.get(second).json()['csrf_token']
    assert session.post(second, headers={'X-CSRFToken': second_token}).json()['votes'] == 1
    with sqlite3.connect(private / 'library.sqlite') as connection:
        connection.execute("UPDATE publication_vote SET voted_at=voted_at-3601 WHERE book_slug='krampus'")
    assert session.post(api, headers={'X-CSRFToken': second_token}).json()['votes'] == 3
    assert session.get(api).json()['votes'] == 3


def test_php_reader_progress_validation_and_editor_sanitization(server):
    base, session, private, _ = server
    assert login(base, session).status_code == 303
    page = session.get(base + '/read/moya-slabost-moya-bol/prolog/')
    csrf = token(page)
    assert session.post(base + '/api/progress', json={'chapter_id': 1, 'paragraph_id': 'p-5', 'scroll_position': .2}, headers={'X-CSRFToken': csrf}).json()['saved'] is True
    assert session.post(base + '/api/progress', json={'chapter_id': 1, 'paragraph_id': '<script>', 'scroll_position': 100}, headers={'X-CSRFToken': csrf}).status_code == 400
    with sqlite3.connect(private / 'library.sqlite') as connection:
        connection.execute("UPDATE chapters SET body='<p>Hello <script>alert(1)</script><a href=\"javascript:alert(2)\">link</a></p>' WHERE slug='chapter'")
    html = session.get(base + '/read/closed/chapter/').text
    assert '<script>alert' not in html and 'javascript:' not in html
    assert session.get(base + '/api/publication/unknown').status_code == 404


def test_php_one_use_owner_ticket(server):
    base, session, _, env = server
    result = subprocess.run([PHP, str(ROOT / 'php-app/bin/console.php'), 'ticket', 'owner'], env=env, cwd=ROOT, check=True, capture_output=True, text=True)
    url = result.stdout.strip()
    response = session.get(url)
    ticket = re.search(r'name="ticket" value="([a-f0-9]+)"', response.text)[1]
    data = {'ticket': ticket, 'csrf_token': token(response)}
    assert session.post(base + '/auth/ticket', data=data, allow_redirects=False).status_code == 303
    assert session.get(url).status_code == 403


def test_php_author_can_publish_and_reader_cannot_edit(server):
    base, session, private, _ = server
    assert login(base, session).status_code == 303
    csrf = token(session.get(base + '/admin/works/new'))
    work = {'title': 'Editor test', 'slug': 'editor-test', 'subtitle': '', 'cover_path': '', 'description': '', 'shelf': 'novellas', 'minimum_tier': 'free', 'access_type': 'free', 'status': 'draft', 'sort_order': '0', 'completion_percent': '', 'is_visible': '1', 'csrf_token': csrf}
    response = session.post(base + '/admin/works/new', data=work, allow_redirects=False)
    assert response.status_code == 303
    work_id = re.search(r'/works/(\d+)/edit', response.headers['Location'])[1]
    chapter_path = f'/admin/works/{work_id}/chapters/new'
    chapter = {'title': 'Chapter', 'slug': 'chapter', 'number': '1', 'sort_order': '0', 'body_format': 'html', 'body': '<p>EDITOR_PRIVATE_BODY<script>alert(42)</script></p>', 'fragment_body': '<p>EDITOR_PUBLIC_FRAGMENT</p>', 'fragment_blocks': '', 'access_type': 'fragment', 'is_published': '1', 'csrf_token': csrf}
    saved = session.post(base + chapter_path, data=chapter, allow_redirects=False)
    assert saved.status_code == 303
    url = base + '/read/editor-test/chapter/'
    public = requests.get(url)
    assert public.status_code == 200 and 'EDITOR_PUBLIC_FRAGMENT' in public.text and 'EDITOR_PRIVATE_BODY' not in public.text
    owner_page = session.get(url)
    assert 'EDITOR_PRIVATE_BODY' in owner_page.text and '<script>alert' not in owner_page.text
    reader = requests.Session()
    assert login(base, reader, 'reader').status_code == 303
    reader_csrf = token(reader.get(base + '/auth/login'))
    assert reader.post(base + '/admin/works/new', data={**work, 'csrf_token': reader_csrf}).status_code == 403
    with sqlite3.connect(private / 'library.sqlite') as connection:
        connection.execute("UPDATE users SET tier='witness',tier_expires_at=? WHERE username='reader'", (int(time.time()) + 3600,))
    assert 'EDITOR_PRIVATE_BODY' in reader.get(url).text
    with sqlite3.connect(private / 'library.sqlite') as connection:
        connection.execute("UPDATE users SET tier_expires_at=1 WHERE username='reader'")
    assert 'EDITOR_PRIVATE_BODY' not in reader.get(url + 'index.html').text


def test_php_simultaneous_votes_do_not_double_count(server):
    base, _, _, _ = server
    api = base + '/api/publication/krampus'
    clients = [requests.Session(), requests.Session()]
    tokens = [client.get(api).json()['csrf_token'] for client in clients]
    def vote(i):
        return clients[i].post(api, headers={'X-CSRFToken': tokens[i]}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(vote, range(2))) == [200, 429]
    assert clients[0].get(api).json()['votes'] == 1
