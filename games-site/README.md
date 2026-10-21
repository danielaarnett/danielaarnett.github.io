# games.danielarnett.com

The current static games/applications website. `public/` is the complete document
root; it needs neither Node.js nor PHP on the hosting account.

Imported from `.games/package-stage-v2/dist`, the latest local version with Russian
navigation and copy, PocketDraft and Codexia. The equivalent CSS and JavaScript
also exist in `.games/studio/dist`; its HTML predates the personalized edits.
Original drafts, reference captures, archives, nested Git and Sites metadata are
left in `.games/` and are not published.

The layout and interactions are preserved, including the project switcher,
project/about/privacy dialogs, mobile menu and demonstration form. Names and art
placeholders remain where no final assets were supplied. The form sends and saves
no data; application downloads are not supplied in the source either.

Changes for the existing domain: Russian document language, page title and
description, a link back to the author website, versioned assets, and HTTPS routing.

Build only this subdomain: `python scripts/build_games_release.py`.
Upload the resulting archive to `/home/danielar` and extract there. The archive
contains only `games.danielarnett.com/`; it cannot replace the author site or its
private database. Back up the existing subdomain directory before extraction.
The main PHP release builder also uses `public/`, so it will preserve this site.

For a local preview: `python -m http.server 4173 --bind 127.0.0.1 --directory games-site/public`.
