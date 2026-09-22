from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy.orm import deferred

from .extensions import db


def utcnow():
    # UTC without tzinfo is consistent across SQLite and PostgreSQL columns.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=True)
    oidc_subject = db.Column(db.String(128), unique=True, nullable=True)
    username = db.Column(db.String(128), default='', nullable=False)
    display_name = db.Column(db.String(160), default='', nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    first_login_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    membership_status = db.Column(db.String(32), default='unknown', nullable=False)
    membership_checked_at = db.Column(db.DateTime, nullable=True)
    membership_scope = db.Column(db.String(64), nullable=True)


class Work(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(240), nullable=False)
    subtitle = db.Column(db.String(240), default='', nullable=False)
    description = db.Column(db.Text, default='', nullable=False)
    cover_path = db.Column(db.String(240), default='', nullable=False)
    cover_hover_path = db.Column(db.String(240), default='', server_default='', nullable=False)
    status = db.Column(db.String(16), default='draft', nullable=False)
    access_type = db.Column(db.String(16), default='free', nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    published_at = db.Column(db.DateTime, nullable=True)
    is_visible = db.Column(db.Boolean, default=False, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    completion_percent = db.Column(db.Integer, nullable=True)
    __table_args__ = (
        db.CheckConstraint('completion_percent IS NULL OR (completion_percent >= 0 AND completion_percent <= 100)', name='work_completion'),
        db.CheckConstraint("status IN ('draft','ongoing','completed')", name='work_status'),
        db.CheckConstraint("access_type IN ('free','fragment','subscriber')", name='work_access'),
    )


class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    work_id = db.Column(db.Integer, db.ForeignKey('work.id'), nullable=False, index=True)
    number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(240), nullable=False)
    slug = db.Column(db.String(120), nullable=False)
    # Metadata queries cannot accidentally load prose. Routes explicitly select
    # ONE of these columns only after the central access check has succeeded.
    body = deferred(db.Column(db.Text, default='', nullable=False), raiseload=True)
    fragment_body = deferred(db.Column(db.Text, default='', nullable=False), raiseload=True)
    body_format = db.Column(db.String(16), default='markdown', nullable=False)
    word_count = db.Column(db.Integer, default=0, nullable=False)
    access_type = db.Column(db.String(16), default='free', nullable=False)
    is_published = db.Column(db.Boolean, default=False, nullable=False)
    published_at = db.Column(db.DateTime, nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    work = db.relationship(Work)
    __table_args__ = (
        db.UniqueConstraint('work_id', 'slug'),
        db.UniqueConstraint('work_id', 'number'),
        db.CheckConstraint("access_type IN ('free','fragment','subscriber')", name='chapter_access'),
        db.CheckConstraint("body_format IN ('markdown','html')", name='chapter_format'),
        db.CheckConstraint('number >= 0', name='chapter_number'),
    )


class ReadingProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    paragraph_id = db.Column(db.String(24), default='', nullable=False)
    scroll_position = db.Column(db.Float, default=0, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'chapter_id'),)


class ReadAudit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=True)
    ip_hash = db.Column(db.String(64), nullable=False)
    user_agent = db.Column(db.String(180), nullable=False)
    route = db.Column(db.String(260), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)


class FingerprintReceipt(db.Model):
    id = db.Column(db.String(32), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class LocalLoginTicket(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
