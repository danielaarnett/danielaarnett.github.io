import math
import re

from flask import Blueprint, abort, current_app, g, jsonify, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from ..extensions import db, limiter
from ..models import Chapter, ReadingProgress, Work, utcnow
from ..services import fingerprint
from ..services.access import can_read
from ..services.content import render_content, valid_slug

bp = Blueprint('library', __name__)


def visible_works():
    return select(Work).where(Work.is_visible.is_(True), Work.published_at <= utcnow())


def published_chapters(work_id):
    return select(Chapter).where(Chapter.work_id == work_id, Chapter.is_published.is_(True),
                                 Chapter.published_at <= utcnow()).order_by(Chapter.sort_order, Chapter.number, Chapter.id)


def get_work(slug):
    if not valid_slug(slug):
        abort(404)
    return db.first_or_404(visible_works().where(Work.slug == slug))


@bp.get('/')
def home():
    works = {w.slug: w for w in db.session.scalars(visible_works())}
    first_chapters = {}
    for slug in ('moya-slabost-moya-bol', 'goryachee-solntse', 'melki'):
        if slug in works:
            chapter = db.session.scalar(published_chapters(works[slug].id).limit(1))
            if chapter:
                first_chapters[slug] = chapter.slug
    return render_template('home.html', works=works, first_chapters=first_chapters)


@bp.get('/library')
def catalog():
    statement = visible_works().where(Work.id.in_(
        select(Chapter.work_id).where(Chapter.is_published.is_(True), Chapter.published_at <= utcnow())
    )).order_by(Work.sort_order, Work.title)
    page = db.paginate(statement, per_page=12, max_per_page=12, error_out=False)
    return render_template('library/catalog.html', page=page)


@bp.get('/works/<slug>')
def work(slug):
    item = get_work(slug)
    chapters = list(db.session.scalars(published_chapters(item.id)))
    return render_template('library/work.html', work=item, chapters=chapters)


def reader_key():
    return f'user:{current_user.id}' if current_user.is_authenticated else f'ip:{request.remote_addr}'


@bp.get('/read/<work_slug>/<chapter_slug>')
@limiter.limit(lambda: current_app.config['READ_RATE_LIMIT'], key_func=reader_key)
@limiter.limit('120 per minute')
def read(work_slug, chapter_slug):
    work = get_work(work_slug)
    if not valid_slug(chapter_slug):
        abort(404)
    chapter = db.first_or_404(published_chapters(work.id).where(Chapter.slug == chapter_slug))
    g.chapter_id = chapter.id
    access = can_read(current_user, work, chapter)
    if access.mode == 'deny':
        return render_template('library/paywall.html', work=work, chapter=chapter, reason=access.reason), 403
    # This is the first and only body fetch; a fragment query never selects body.
    column = Chapter.body if access.mode == 'full' else Chapter.fragment_body
    body = db.session.scalar(select(column).where(Chapter.id == chapter.id))
    html = render_content(body or '', chapter.body_format)
    protected = access.mode == 'full' and access.reason in {'subscriber', 'owner'}
    if protected and current_app.config['FINGERPRINT_ENABLED']:
        html = fingerprint.apply(html, current_user.id, chapter.id)
    chapters = list(db.session.scalars(published_chapters(work.id)))
    index = next(i for i, c in enumerate(chapters) if c.id == chapter.id)
    progress = None
    if current_user.is_authenticated:
        progress = db.session.scalar(select(ReadingProgress).where(ReadingProgress.user_id == current_user.id,
                                                                  ReadingProgress.chapter_id == chapter.id))
    return render_template('library/read.html', work=work, chapter=chapter, content=html,
                           access=access, protected=protected, progress=progress,
                           previous=chapters[index-1] if index else None,
                           following=chapters[index+1] if index+1 < len(chapters) else None,
                           chapter_index=index, chapter_count=len(chapters))


@bp.post('/api/progress')
@login_required
@limiter.limit('12 per minute', key_func=reader_key)
def save_progress():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        abort(400)
    if type(data.get('chapter_id')) is not int:
        abort(400)
    chapter = db.session.get(Chapter, data['chapter_id'])
    if not chapter:
        abort(404)
    work = db.session.get(Work, chapter.work_id)
    access = can_read(current_user, work, chapter)
    if access.reason == 'unpublished':
        abort(404)
    if access.mode == 'deny':
        abort(403)
    position = data.get('scroll_position')
    paragraph = data.get('paragraph_id', '')
    if (type(position) not in (int, float) or not math.isfinite(position) or not 0 <= position <= 1
            or not isinstance(paragraph, str) or not re.fullmatch(r'p-[1-9][0-9]{0,5}', paragraph)):
        abort(400)
    row = db.session.scalar(select(ReadingProgress).where(ReadingProgress.user_id == current_user.id,
                                                         ReadingProgress.chapter_id == chapter.id))
    if not row:
        row = ReadingProgress(user_id=current_user.id, chapter_id=chapter.id)
        db.session.add(row)
    row.paragraph_id, row.scroll_position, row.updated_at = paragraph, position, utcnow()
    db.session.commit()
    return jsonify(saved=True)
