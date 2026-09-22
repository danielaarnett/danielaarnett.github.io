from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from lxml import html as html_parser
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import undefer
from wtforms import BooleanField, IntegerField, SelectField, StringField, TextAreaField
from wtforms.validators import InputRequired, Length, NumberRange, Optional, ValidationError

from ..extensions import db, limiter
from ..models import Chapter, User, Work, utcnow
from ..services.content import count_words, render_content, valid_cover, valid_slug

bp = Blueprint('admin', __name__, url_prefix='/admin')
ACCESS_CHOICES = [('free', 'Бесплатно'), ('fragment', 'Фрагмент + закрытое продолжение'), ('subscriber', 'Только читательский круг')]


def owner_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def slug_validator(form, field):
    if not valid_slug(field.data):
        raise ValidationError('Используйте латинские буквы a–z, цифры и одиночные дефисы.')


def cover_validator(form, field):
    if not valid_cover(field.data):
        raise ValidationError('Укажите путь вида /images/cover.png или оставьте поле пустым.')


class WorkForm(FlaskForm):
    title = StringField('Название', validators=[InputRequired(), Length(max=240)])
    slug = StringField('Адрес произведения', validators=[InputRequired(), slug_validator])
    subtitle = StringField('Подзаголовок / вид произведения', validators=[Length(max=240)])
    description = TextAreaField('Описание', validators=[Length(max=10000)])
    cover_path = StringField('Обложка', validators=[Length(max=240), cover_validator])
    cover_hover_path = StringField('Арт при наведении (необязательно)', validators=[Length(max=240), cover_validator])
    status = SelectField('Состояние', choices=[('draft', 'Черновик'), ('ongoing', 'В работе'), ('completed', 'Завершено')])
    access_type = SelectField('Доступ к произведению', choices=ACCESS_CHOICES)
    sort_order = IntegerField('Порядок в библиотеке', default=0, validators=[InputRequired(), NumberRange(min=0, max=100000)])
    completion_percent = IntegerField('Готовность, %', validators=[Optional(), NumberRange(min=0, max=100)])
    is_visible = BooleanField('Показывать произведение читателям')


class ChapterForm(FlaskForm):
    title = StringField('Название главы', validators=[InputRequired(), Length(max=240)])
    slug = StringField('Адрес главы', validators=[InputRequired(), slug_validator])
    number = IntegerField('Номер главы (0 — пролог)', default=1, validators=[InputRequired(), NumberRange(min=0, max=100000)])
    sort_order = IntegerField('Порядок в оглавлении', default=0, validators=[InputRequired(), NumberRange(min=0, max=100000)])
    body_format = SelectField('Формат текста', choices=[('markdown', 'Markdown'), ('html', 'HTML из импорта')])
    body = TextAreaField('Полный текст', validators=[InputRequired(), Length(max=700000)])
    access_type = SelectField('Доступ к главе', choices=ACCESS_CHOICES)
    fragment_body = TextAreaField('Бесплатный фрагмент (в том же формате)', validators=[Length(max=700000)])
    fragment_blocks = IntegerField('Или взять первые N блоков полного текста', validators=[Optional(), NumberRange(min=1, max=10000)])
    is_published = BooleanField('Опубликовать главу')


@bp.get('')
@bp.get('/')
@owner_required
def dashboard():
    return render_template('admin/dashboard.html', works=db.session.scalars(select(Work).order_by(Work.sort_order, Work.id)))


@bp.route('/works/new', methods=['GET', 'POST'])
@bp.route('/works/<int:work_id>/edit', methods=['GET', 'POST'])
@owner_required
def edit_work(work_id=None):
    work = db.get_or_404(Work, work_id) if work_id is not None else Work()
    form = WorkForm(obj=work if work.id is not None else None)
    if form.validate_on_submit():
        for name in ('title', 'slug', 'subtitle', 'description', 'cover_path', 'cover_hover_path', 'status', 'access_type', 'sort_order', 'completion_percent', 'is_visible'):
            setattr(work, name, getattr(form, name).data)
        work.published_at = work.published_at or utcnow() if work.is_visible else None
        db.session.add(work)
        try:
            db.session.commit()
            flash('Произведение сохранено.')
            return redirect(url_for('admin.edit_work', work_id=work.id))
        except IntegrityError:
            db.session.rollback()
            form.slug.errors.append('Этот адрес уже занят.')
    chapters = db.session.scalars(select(Chapter).where(Chapter.work_id == work.id).order_by(Chapter.sort_order, Chapter.number)) if work.id else []
    return render_template('admin/work.html', form=form, work=work, chapters=chapters)


@bp.route('/works/<int:work_id>/chapters/new', methods=['GET', 'POST'])
@bp.route('/works/<int:work_id>/chapters/<int:chapter_id>/edit', methods=['GET', 'POST'])
@owner_required
def edit_chapter(work_id, chapter_id=None):
    work = db.get_or_404(Work, work_id)
    chapter = db.first_or_404(select(Chapter).where(Chapter.id == chapter_id, Chapter.work_id == work_id)
                              .options(undefer(Chapter.body), undefer(Chapter.fragment_body))) if chapter_id is not None else Chapter(work_id=work_id)
    form = ChapterForm(obj=chapter if chapter.id is not None else None)
    if form.validate_on_submit():
        for name in ('title', 'slug', 'number', 'sort_order', 'body_format', 'body', 'access_type', 'fragment_body', 'is_published'):
            setattr(chapter, name, getattr(form, name).data)
        if form.fragment_blocks.data:
            safe_body = render_content(chapter.body, chapter.body_format)
            wrapper = html_parser.fragment_fromstring(safe_body, create_parent='div')
            chapter.body = safe_body
            chapter.fragment_body = ''.join(html_parser.tostring(node, encoding='unicode') for node in list(wrapper)[:form.fragment_blocks.data])
            chapter.body_format = 'html'
        if chapter.access_type == 'fragment' and not chapter.fragment_body.strip():
            form.fragment_body.errors.append('Укажите открытый фрагмент или число блоков.')
        else:
            chapter.word_count = count_words(chapter.body, chapter.body_format)
            chapter.published_at = chapter.published_at or utcnow() if chapter.is_published else None
            db.session.add(chapter)
            try:
                db.session.commit()
                flash('Глава сохранена.')
                return redirect(url_for('admin.edit_chapter', work_id=work.id, chapter_id=chapter.id))
            except IntegrityError:
                db.session.rollback()
                form.slug.errors.append('Адрес или номер главы уже используется в этом произведении.')
    return render_template('admin/chapter.html', form=form, work=work, chapter=chapter)


@bp.get('/users')
@owner_required
def users():
    page = db.paginate(select(User).order_by(User.id.desc()), per_page=30, max_per_page=30, error_out=False)
    return render_template('admin/users.html', page=page)


@bp.post('/users/<int:user_id>/invalidate')
@owner_required
def invalidate(user_id):
    user = db.get_or_404(User, user_id)
    user.membership_checked_at = None
    user.membership_status = 'unknown'
    user.membership_scope = None
    db.session.commit()
    flash('Состояние доступа будет проверено заново при следующем обращении.')
    return redirect(url_for('admin.users'))
