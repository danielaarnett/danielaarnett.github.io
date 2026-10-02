import hashlib
import hmac
import math
from datetime import timedelta

from flask import Blueprint, current_app, jsonify, request
from flask_wtf.csrf import generate_csrf
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from .extensions import db, limiter
from .models import PublicationInterest, PublicationVote, utcnow

bp = Blueprint('publication', __name__)


def voter_key():
    return hmac.new(current_app.secret_key.encode(),
        ('publication:krampus:' + (request.remote_addr or '')).encode(), hashlib.sha256).hexdigest()


def total():
    return db.session.scalar(select(PublicationInterest.votes).where(PublicationInterest.slug == 'krampus')) or 0


def cooldown(row, now):
    return max(0, math.ceil((row.voted_at + timedelta(hours=1) - now).total_seconds())) if row else 0


@bp.get('/api/publication/krampus')
def status():
    row = db.session.get(PublicationVote, ('krampus', voter_key()))
    return jsonify(votes=total(), retry_after=cooldown(row, utcnow()), csrf_token=generate_csrf())


@bp.post('/api/publication/krampus')
@limiter.limit('120 per hour')
def vote():
    now, key = utcnow(), voter_key()
    # Claim the rolling one-hour slot atomically, before updating the total.
    claimed = db.session.execute(update(PublicationVote).where(
        PublicationVote.book_slug == 'krampus', PublicationVote.ip_hash == key,
        PublicationVote.voted_at <= now - timedelta(hours=1)).values(voted_at=now)).rowcount
    if not claimed:
        row = db.session.get(PublicationVote, ('krampus', key))
        if row:
            retry = cooldown(row, now)
            db.session.rollback()
            response = jsonify(votes=total(), retry_after=retry,
                message='Вы уже проголосовали. Следующий голос можно оставить через час после предыдущего.')
            response.headers['Retry-After'] = str(retry)
            return response, 429
        db.session.add(PublicationVote(book_slug='krampus', ip_hash=key, voted_at=now))
        try:
            db.session.flush()
        except IntegrityError:
            # Two simultaneous first votes from one IP still produce one vote.
            db.session.rollback()
            row = db.session.get(PublicationVote, ('krampus', key))
            return jsonify(votes=total(), retry_after=cooldown(row, now),
                           message='Ваш голос уже учтён. Повторить можно через час.'), 429
    changed = db.session.execute(update(PublicationInterest).where(
        PublicationInterest.slug == 'krampus').values(votes=PublicationInterest.votes + 1)).rowcount
    if not changed:
        db.session.rollback()
        return jsonify(message='Голосование пока недоступно.'), 503
    votes = total()
    db.session.commit()
    return jsonify(votes=votes, retry_after=3600,
        message='Спасибо за ваш голос! Он сохранён и поможет автору определить очередь публикации книги.')
