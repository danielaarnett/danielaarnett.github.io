import hashlib
import secrets
from datetime import timedelta
from pathlib import Path

import click
from flask import current_app
from sqlalchemy import delete, select

from .extensions import db
from .models import Chapter, LocalLoginTicket, ReadAudit, User, Work, utcnow
from .services.docx_import import import_prologue
from .services.content import count_words
from .services import fingerprint


def register_commands(app):
    @app.cli.command('seed-catalog')
    def seed_catalog():
        """Add metadata only; never ship manuscript bodies in Git."""
        entries = [
            ('moya-slabost-moya-bol', 'Моя слабость, моя боль', 'Роман', '/images/fin1.png'),
            ('goryachee-solntse', 'Горячее солнце', 'Черновик', '/images/art1.png'),
            ('melki', 'Мелки', 'Черновик', ''),
            ('deti-krampusa', 'Дети Крампуса: Тени Йоля', 'Роман', '/images/Book01.png'),
            ('orden-na-sdachu', 'Орден на сдачу', 'Роман', '/images/Book02.png'),
            ('iam-sero-est', 'Iam sero est', 'Сборник', '/images/Book06.png'),
        ]
        for order, (slug, title, subtitle, cover) in enumerate(entries):
            if not db.session.scalar(select(Work).where(Work.slug == slug)):
                db.session.add(Work(slug=slug, title=title, subtitle=subtitle, cover_path=cover,
                                    status='draft', access_type='free', is_visible=True, published_at=utcnow(), sort_order=order,
                                    completion_percent=50 if order < 3 else None,
                                    cover_hover_path='/images/art2.png' if slug == 'goryachee-solntse' else ''))
        db.session.commit()
        click.echo('Каталог подготовлен. Существующие записи не изменены.')

    @app.cli.command('import-docx')
    @click.argument('path', type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option('--work-slug', default='moya-slabost-moya-bol', show_default=True)
    @click.option('--publish', is_flag=True, help='Publish the imported prologue for free reading.')
    @click.option('--replace', is_flag=True, help='Explicitly replace an already imported prologue.')
    def import_docx(path, work_slug, publish, replace):
        work = db.session.scalar(select(Work).where(Work.slug == work_slug))
        if not work:
            raise click.ClickException('Сначала создайте произведение или выполните seed-catalog.')
        try:
            data = import_prologue(path)
        except (ValueError, KeyError) as exc:
            raise click.ClickException(str(exc)) from exc
        if data['title'].casefold() != work.title.casefold():
            raise click.ClickException('Название документа не совпадает с выбранным произведением.')
        chapter = db.session.scalar(select(Chapter).where(Chapter.work_id == work.id, Chapter.slug == 'prolog'))
        if chapter and not replace:
            raise click.ClickException('Пролог уже существует. Для замены укажите --replace.')
        if not chapter:
            chapter = Chapter(work_id=work.id, slug='prolog', number=0, sort_order=0)
        chapter.title, chapter.body = data['chapter_title'], data['body']
        chapter.body_format, chapter.access_type = 'html', 'free'
        chapter.word_count = count_words(chapter.body, 'html')
        chapter.is_published, chapter.published_at = publish, utcnow() if publish else None
        if publish:
            work.is_visible, work.published_at = True, work.published_at or utcnow()
        db.session.add(chapter)
        db.session.commit()
        click.echo(f"Импортировано: {data['source_paragraphs']} непустых абзацев; проза — {data['prose_paragraphs']} абзаца. Посвящение и выделения сохранены.")

    @app.cli.command('create-admin')
    @click.option('--telegram-id', type=click.IntRange(min=1, max=2**63-1))
    @click.option('--local', is_flag=True, help='One-use localhost login; never enabled in production.')
    def create_admin(telegram_id, local):
        if bool(telegram_id) == bool(local):
            raise click.ClickException('Укажите только --telegram-id ID или --local.')
        if local and current_app.config['PRODUCTION']:
            raise click.ClickException('Локальный вход отключён в production.')
        statement = select(User).where(User.telegram_id == telegram_id) if telegram_id else select(User).where(User.telegram_id.is_(None), User.is_admin.is_(True))
        user = db.session.scalar(statement)
        if not user:
            user = User(telegram_id=telegram_id, display_name='Автор')
            db.session.add(user)
        user.is_admin = True
        db.session.flush()
        if local:
            token = secrets.token_urlsafe(32)
            db.session.execute(delete(LocalLoginTicket).where(LocalLoginTicket.user_id == user.id))
            db.session.add(LocalLoginTicket(id=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id,
                                            expires_at=utcnow()+timedelta(minutes=10)))
        db.session.commit()
        if local:
            click.echo('Одноразовый вход, действует 10 минут:')
            click.echo(f'http://127.0.0.1:5000/auth/local?token={token}')
        else:
            click.echo('Права владельца назначены. Вход — только через проверенную учётную запись Telegram.')

    @app.cli.command('prune-audit')
    def prune_audit():
        cutoff = utcnow() - timedelta(days=current_app.config['AUDIT_RETENTION_DAYS'])
        result = db.session.execute(delete(ReadAudit).where(ReadAudit.created_at < cutoff))
        db.session.execute(delete(LocalLoginTicket).where(LocalLoginTicket.expires_at < utcnow()))
        db.session.commit()
        click.echo(f'Удалено устаревших записей журнала: {result.rowcount}')

    @app.cli.command('trace-receipt')
    @click.argument('path', type=click.Path(exists=True, dir_okay=False, path_type=Path))
    def trace_receipt(path):
        receipt = fingerprint.identify(path.read_text(encoding='utf-8'))
        if receipt:
            click.echo(f'Выдача {receipt.id}: пользователь {receipt.user_id}, глава {receipt.chapter_id}, {receipt.created_at} UTC')
        else:
            click.echo('Проверяемая метка выдачи не найдена.')
