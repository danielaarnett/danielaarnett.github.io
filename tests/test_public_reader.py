from sqlalchemy import event

from app.extensions import db
from app.models import Work


def test_free_chapter_export_with_shared_assets(app, client, tmp_path):
    result = app.test_cli_runner().invoke(args=['export-free-chapter', 'story', 'free', '--output-root', str(tmp_path)])
    assert result.exit_code == 0, result.output
    page = (tmp_path / 'story/free/index.html').read_text(encoding='utf-8')
    assert 'FULL_PRIVATE_free' in page
    assert 'FULL_PRIVATE_closed' not in page and 'csrf_token' not in page
    for path in ('/css/site.css', '/js/site.js', '/js/reader.js'):
        assert path in page and client.get(path).status_code == 200
    assert client.get('/read/story/free/').status_code == 200


def test_nonpublic_export_refused_before_body_query(app, tmp_path):
    queries = []
    with app.app_context():
        event.listen(db.engine, 'before_cursor_execute', lambda conn, cursor, statement, parameters, context, many: queries.append(statement))
    runner = app.test_cli_runner()
    for slug in ('closed', 'fragment', 'unpublished', 'missing', '../free'):
        result = runner.invoke(args=['export-free-chapter', 'story', slug, '--output-root', str(tmp_path)])
        assert result.exit_code != 0
    with app.app_context():
        db.session.get(Work, 1).access_type = 'subscriber'
        db.session.commit()
    assert runner.invoke(args=['export-free-chapter', 'story', 'free', '--output-root', str(tmp_path)]).exit_code != 0
    assert not list(tmp_path.rglob('*.html'))
    assert not any('chapter.body ' in query or 'chapter.fragment_body ' in query for query in queries)
