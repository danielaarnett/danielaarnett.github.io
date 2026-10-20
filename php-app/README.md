# PHP server for AlexHost

PHP 8.2+ with PDO SQLite, DOM and mbstring. Composer dependencies are locked in
`composer.lock`; deploy the generated vendor directory. Python and Redis are not
needed on the hosting account.

## Layout

- `/home/danielar/public_html/`: public assets, `index.php` and routing `.htaccess`.
- `/home/danielar/arnett-app/`: this application, templates and Composer vendor.
- `/home/danielar/arnett-private/`: private `config.php` and SQLite database. Never publish or commit these.
- `/home/danielar/games.danielarnett.com/`: independent games site.

Existing static `read/` and `library/` directories must be moved outside public_html
when switching to PHP. Clean URLs and explicit legacy `index.html` reader URLs
are handled by PHP, so a future access change cannot be bypassed with an old file.
The imported prologue is already explicitly public and remains free.

## Install and upgrade

1. `composer install --no-dev --prefer-dist --optimize-autoloader` in this folder.
2. Copy `config.example.php` to the private folder; generate a random secret.
3. Set `ARNETT_PRIVATE_DIR` for CLI use if the private directory is elsewhere.
4. `php bin/console.php init` creates the schema and imports the public catalog
   and prologue once. Repeated deployments never overwrite edited works.
5. Create an owner: pipe a password of at least 16 characters to
   `php bin/console.php user:add USER --admin --password-stdin`. There are no
   default credentials or public installer. Reader accounts use the same command
   without `--admin`. Log in at `/auth/login`.
6. `php bin/console.php ticket USER` creates a one-use ten-minute login link.
   It requires a CSRF-protected confirmation before consuming the ticket.
7. Run `php bin/console.php prune` daily from cPanel Cron Jobs, after activating
   the relevant PHP version. Back up the private database and config separately.

Build an archive from the repository root:
`python scripts/build_php_release.py`. Only the initial installation uses
`--initial-private PATH`; upgrades must omit that option to preserve the live
database and secret. ZIP file permissions are explicitly 0644 (private files
0600). SQL migrations are additive/idempotent; current schema version is initial.

## Behavior

Routes: `/`, `/library/`, `/works/{slug}`, `/read/{work}/{chapter}/`, `/admin`,
`/auth/login`, `/api/progress`, `/api/publication/{krampus|orden-na-sdachu}`.
The reader keeps the existing CSS and copy restrictions. Catalog queries never
fetch chapter bodies. A reader request checks publication date, work/chapter
access and expiring user tier before selecting either full text or the separate
fragment. HTML Purifier and CommonMark sanitize the output. Private editions
have removable signed receipts, with `php bin/console.php trace FILE` for lookup.

Sessions use strict mode, HttpOnly, SameSite=Lax, Secure in production, and rotate
on login. POST requests require CSRF. Rate limits are shared through SQLite;
raw IP addresses are never stored. Publication votes use an atomic database
transaction and separate one-hour limits per book for both HMAC IP and a signed
HttpOnly voter cookie. Clearing cookies or changing only IP does not bypass the
hour. A successful response returns the real persistent total.

Boosty/Telegram payment or membership integration is not connected. Local user
accounts and expiring manual tiers are ready; `subscriptions_enabled=false`
keeps paid access disabled for readers until the payment connection is built.
The former Python implementation is retained as a migration reference, not run
in production. Its Telegram configuration is not consumed by PHP.

Tests: `python -m pytest tests/test_php_server.py -q` with PHP available on PATH
or via `PHP_BINARY`. Tests run a real PHP server with isolated databases, dummy
accounts and fake protected texts; the test-only IP header is never deployed.
