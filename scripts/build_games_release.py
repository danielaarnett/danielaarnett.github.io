"""Package only the public games site for the existing cPanel document root."""
import argparse
from datetime import datetime
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'games-site/public'
PUBLIC_FILES = ('.htaccess', 'index.html', 'style.css', 'app.js')


def build(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in PUBLIC_FILES:
            info = zipfile.ZipInfo('games.danielarnett.com/' + name, datetime.now().timetuple()[:6])
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (PUBLIC / name).read_bytes())
    print(f'{output.resolve()} ({output.stat().st_size / 1024:.1f} KB)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(ROOT / 'local-qa/deployment/games-release.zip'))
    build(parser.parse_args().output)
