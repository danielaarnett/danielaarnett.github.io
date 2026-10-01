import hashlib
from dataclasses import dataclass
from datetime import timedelta

import requests
from flask import current_app

from ..extensions import db
from ..models import utcnow

MEMBER_STATES = {'creator', 'administrator', 'member'}
TIERS = {'free': 0, 'witness': 1, 'appreciator': 2}
TIER_LABELS = {'free': 'Бесплатно', 'witness': 'Свидетель', 'appreciator': 'Ценитель'}
SHELVES = {'novellas': 'Новеллы', 'short_novels': 'Повести', 'novels': 'Романы', 'scripts': 'Сценарии', 'unfinished': 'Незаконченные', 'poetry': 'Стихотворения', 'songs': 'Песни'}


def assigned_tier(user):
    """Only trusted server grants with an expiry can raise a reader's tier."""
    if not current_app.config['SUBSCRIPTIONS_ENABLED'] or not user.is_authenticated:
        return 'free'
    expires = getattr(user, 'subscription_expires_at', None)
    tier = getattr(user, 'subscription_tier', 'free')
    return tier if tier in TIERS and expires and expires > utcnow() else 'free'


def reader_tier(user):
    if user.is_authenticated and user.is_admin:
        return 'appreciator'
    tier = assigned_tier(user)
    if tier != 'free':
        return tier
    # The existing single Telegram group grants only the first paid level.
    return 'witness' if membership(user) in MEMBER_STATES else 'free'


def required_tier(work):
    tier = work.minimum_tier or 'free'
    return 'witness' if tier == 'free' and work.access_type == 'subscriber' else tier


def membership(user):
    config = current_app.config
    if not config['SUBSCRIPTIONS_ENABLED']:
        return 'disabled'
    if not user.is_authenticated or not user.telegram_id:
        return 'anonymous'
    token, chat = config['TELEGRAM_BOT_TOKEN'], config['TELEGRAM_SUBSCRIBERS_CHAT_ID']
    if not token or not chat:
        return 'unavailable'
    scope = hashlib.sha256(f'{chat}:{token}'.encode()).hexdigest()
    now = utcnow()
    if (user.membership_scope == scope and user.membership_checked_at
            and now - timedelta(seconds=config['MEMBERSHIP_CACHE_SECONDS']) < user.membership_checked_at <= now):
        return user.membership_status
    try:
        response = requests.get(f'https://api.telegram.org/bot{token}/getChatMember',
                                params={'chat_id': chat, 'user_id': user.telegram_id}, timeout=(3, 5))
        response.raise_for_status()
        data = response.json()
        result = data.get('result', {})
        if data.get('ok') is not True or result.get('user', {}).get('id') != user.telegram_id:
            raise ValueError('Invalid membership response')
        status = result.get('status', 'unknown')
        if status not in MEMBER_STATES | {'left', 'kicked', 'restricted'}:
            status = 'unknown'
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        # No stale positive result during outages, and no token/URL in logs.
        current_app.logger.warning('Membership verification unavailable')
        status = 'unavailable'
    user.membership_status, user.membership_checked_at, user.membership_scope = status, now, scope
    if status == 'unavailable':
        user.membership_checked_at = None
    db.session.commit()
    return status


@dataclass(frozen=True)
class ReadAccess:
    mode: str  # full, fragment, deny
    reason: str


def can_read(user, work, chapter):
    now = utcnow()
    if (not work.is_visible or not work.published_at or work.published_at > now
            or not chapter.is_published or not chapter.published_at or chapter.published_at > now):
        return ReadAccess('deny', 'unpublished')
    access = 'subscriber' if work.access_type == 'subscriber' else chapter.access_type
    if user.is_authenticated and user.is_admin:
        return ReadAccess('full', 'owner')
    required = required_tier(work)
    if required != 'free':
        if TIERS[reader_tier(user)] < TIERS[required]:
            return ReadAccess('deny', 'tier')
        return ReadAccess('full', 'subscriber')
    if access == 'free':
        return ReadAccess('full', 'free')
    if assigned_tier(user) != 'free':
        return ReadAccess('full', 'subscriber')
    state = membership(user)
    if state in MEMBER_STATES:
        return ReadAccess('full', 'subscriber')
    return ReadAccess('fragment' if access == 'fragment' else 'deny', state)
