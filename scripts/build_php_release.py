"""Build a cPanel archive with application and secrets outside public_html."""
import argparse
from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(output, initial_private=None):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not (ROOT / 'php-app/vendor/autoload.php').is_file():
        raise SystemExit('Run composer install --no-dev in php-app first.')
    files = {}
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    public_names = {name for name in tracked if name.startswith(('css/', 'js/', 'fonts/', 'images/')) and not name.endswith(('.psd', '.prompt.md'))}
    public_names.update(str(path.relative_to(ROOT)).replace('\\', '/') for path in (ROOT / 'images').glob('shelf-*.png'))
    public_names.update(['images/author-imagination-hero.png', 'reading.css', 'static-texture.webp'])
    for name in public_names:
        path = ROOT / name
        files['public_html/' + name] = path.read_bytes() if path.is_file() else subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT)
    files['public_html/index.php'] = (ROOT / 'php-public/index.php').read_bytes()
    files['public_html/.htaccess'] = (ROOT / 'php-public/.htaccess').read_bytes()
    # Keep the versioned PHP homepage synced with the static preview.
    home = (ROOT / 'index.html').read_text(encoding='utf-8').replace('data-vote-api=""', 'data-vote-api="/api/publication/krampus"').replace('href="./', 'href="/').replace('src="./', 'src="/')
    (ROOT / 'php-app/views/home.html').write_text(home, encoding='utf-8')
    for path in (ROOT / 'php-app').rglob('*'):
        if not path.is_file() or path.name in ('router.php', 'config.local.php'):
            continue
        name = path.relative_to(ROOT / 'php-app').as_posix()
        if name.startswith('vendor/composer/tmp-') or name.endswith('probe.txt'):
            continue
        files['arnett-app/' + name] = path.read_bytes()
    for path in (ROOT / 'games-placeholder').rglob('*'):
        if path.is_file():
            files['games.danielarnett.com/' + path.relative_to(ROOT / 'games-placeholder').as_posix()] = path.read_bytes()
    if initial_private:
        private = Path(initial_private)
        files['arnett-private/config.php'] = (private / 'config.php').read_bytes()
        # SQLite's backup API captures a consistent image, including committed WAL data.
        with tempfile.TemporaryDirectory() as temp:
            snapshot = Path(temp) / 'library.sqlite'
            with closing(sqlite3.connect(private / 'library.sqlite')) as source, closing(sqlite3.connect(snapshot)) as target:
                source.backup(target)
            files['arnett-private/library.sqlite'] = snapshot.read_bytes()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        timestamp = datetime.now().timetuple()[:6]
        directories = {str(parent).replace('\\', '/') for name in files for parent in Path(name).parents if str(parent) != '.'}
        for name in sorted(directories):
            item = zipfile.ZipInfo(name + '/', timestamp)
            item.create_system = 3
            item.external_attr = ((0o40700 if name.startswith('arnett-private') else 0o40755) << 16) | 0x10
            archive.writestr(item, b'')
        for name, content in sorted(files.items()):
            item = zipfile.ZipInfo(name, timestamp)
            item.create_system = 3
            item.external_attr = (0o100600 if name.startswith('arnett-private/') else 0o100644) << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item, content)
    print(f'{output.resolve()} ({output.stat().st_size / 1048576:.1f} MB)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(ROOT / 'local-qa/deployment/arnett-php-release.zip'))
    parser.add_argument('--initial-private', help='First installation only: include this private config and database. Omit on upgrades.')
    args = parser.parse_args()
    build(args.output, args.initial_private)
