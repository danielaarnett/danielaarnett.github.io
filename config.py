import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')


def settings():
    production = os.getenv('APP_ENV', 'development') == 'production'
    database = os.getenv('DATABASE_URL', 'sqlite:///library.sqlite')
    for prefix in ('postgres://', 'postgresql://'):
        if database.startswith(prefix):
            database = database.replace(prefix, 'postgresql+psycopg://', 1)
    return dict(
        PRODUCTION=production, DEBUG=False,
        SECRET_KEY=os.getenv('SECRET_KEY'),
        SQLALCHEMY_DATABASE_URI=database,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SECURE=production,
        SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024, MAX_FORM_MEMORY_SIZE=1024 * 1024,
        PUBLIC_BASE_URL=os.getenv('PUBLIC_BASE_URL', 'http://127.0.0.1:5000').rstrip('/'),
        TRUSTED_HOSTS=[h.strip() for h in os.getenv('TRUSTED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()],
        TRUST_PROXY=os.getenv('TRUST_PROXY', '0') == '1',
        RATELIMIT_STORAGE_URI=os.getenv('RATELIMIT_STORAGE_URI', 'memory://'),
        RATELIMIT_HEADERS_ENABLED=True,
        READ_RATE_LIMIT=os.getenv('READ_RATE_LIMIT', '30 per minute;300 per hour'),
        TELEGRAM_CLIENT_ID=os.getenv('TELEGRAM_CLIENT_ID', ''),
        TELEGRAM_CLIENT_SECRET=os.getenv('TELEGRAM_CLIENT_SECRET', ''),
        TELEGRAM_BOT_TOKEN=os.getenv('TELEGRAM_BOT_TOKEN', ''),
        TELEGRAM_SUBSCRIBERS_CHAT_ID=os.getenv('TELEGRAM_SUBSCRIBERS_CHAT_ID', ''),
        SUBSCRIPTIONS_ENABLED=os.getenv('SUBSCRIPTIONS_ENABLED', '0') == '1',
        MEMBERSHIP_CACHE_SECONDS=min(300, max(0, int(os.getenv('MEMBERSHIP_CACHE_SECONDS', '300')))),
        BOOSTY_URL=os.getenv('BOOSTY_URL', ''),
        FINGERPRINT_ENABLED=os.getenv('FINGERPRINT_ENABLED', '1') == '1',
        AUDIT_RETENTION_DAYS=int(os.getenv('AUDIT_RETENTION_DAYS', '7')),
    )
