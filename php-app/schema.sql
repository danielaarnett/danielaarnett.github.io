CREATE TABLE IF NOT EXISTS works (
 id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
 subtitle TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '', cover_path TEXT NOT NULL DEFAULT '',
 shelf TEXT NOT NULL DEFAULT 'unfinished', minimum_tier TEXT NOT NULL DEFAULT 'free' CHECK(minimum_tier IN ('free','witness','appreciator')),
 access_type TEXT NOT NULL DEFAULT 'free' CHECK(access_type IN ('free','fragment','subscriber')),
 status TEXT NOT NULL DEFAULT 'draft', sort_order INTEGER NOT NULL DEFAULT 0, completion_percent INTEGER,
 is_visible INTEGER NOT NULL DEFAULT 0, published_at INTEGER, updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS chapters (
 id INTEGER PRIMARY KEY, work_id INTEGER NOT NULL REFERENCES works(id), slug TEXT NOT NULL, title TEXT NOT NULL,
 number INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0,
 body TEXT NOT NULL DEFAULT '', fragment_body TEXT NOT NULL DEFAULT '', body_format TEXT NOT NULL DEFAULT 'html',
 access_type TEXT NOT NULL DEFAULT 'free' CHECK(access_type IN ('free','fragment','subscriber')),
 is_published INTEGER NOT NULL DEFAULT 0, published_at INTEGER, word_count INTEGER NOT NULL DEFAULT 0,
 UNIQUE(work_id,slug), UNIQUE(work_id,number)
);
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL DEFAULT '', password_hash TEXT NOT NULL,
 is_admin INTEGER NOT NULL DEFAULT 0, tier TEXT NOT NULL DEFAULT 'free' CHECK(tier IN ('free','witness','appreciator')),
 tier_expires_at INTEGER, session_version INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS reading_progress (
 user_id INTEGER NOT NULL REFERENCES users(id), chapter_id INTEGER NOT NULL REFERENCES chapters(id),
 paragraph_id TEXT NOT NULL, scroll_position REAL NOT NULL, updated_at INTEGER NOT NULL,
 PRIMARY KEY(user_id,chapter_id)
);
CREATE TABLE IF NOT EXISTS publication_interest (slug TEXT PRIMARY KEY, votes INTEGER NOT NULL DEFAULT 0 CHECK(votes >= 0));
CREATE TABLE IF NOT EXISTS publication_vote (
 book_slug TEXT NOT NULL REFERENCES publication_interest(slug), ip_hash TEXT NOT NULL, voted_at INTEGER NOT NULL,
 PRIMARY KEY(book_slug,ip_hash)
);
CREATE TABLE IF NOT EXISTS rate_limits (
 bucket TEXT NOT NULL, subject TEXT NOT NULL, window INTEGER NOT NULL, count INTEGER NOT NULL,
 PRIMARY KEY(bucket,subject,window)
);
CREATE TABLE IF NOT EXISTS read_audit (id INTEGER PRIMARY KEY, user_id INTEGER, chapter_id INTEGER, ip_hash TEXT NOT NULL, status INTEGER NOT NULL, created_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS audit_date ON read_audit(created_at);
CREATE TABLE IF NOT EXISTS fingerprint_receipts (id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, chapter_id INTEGER NOT NULL, created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS login_tickets (digest TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT NOT NULL);
