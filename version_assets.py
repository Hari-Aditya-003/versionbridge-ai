"""Content-version local UI assets so browsers receive the matching release."""
import hashlib
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent
PATTERN=re.compile(r'((?:src|href)="(?:/|\./))([a-z-]+\.(?:js|css))(?:\?v=[^"\s]+)?(")')


def versioned(text):
    def replace(match):
        asset=ROOT/'web'/match[2]
        if not asset.is_file():return match[0]
        revision=hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
        return match[1]+match[2]+'?v='+revision+match[3]
    return PATTERN.sub(replace,text)


def main():
    changed=[]
    for page in [ROOT/'web/index.html',ROOT/'web/demo.html']:
        original=page.read_text();updated=versioned(original)
        if updated!=original:
            changed.append(page.relative_to(ROOT).as_posix())
            if '--check' not in sys.argv:page.write_text(updated)
    if '--check' in sys.argv and changed:raise SystemExit('Stale UI asset versions: '+', '.join(changed))
    print('UI asset versions verified' if '--check' in sys.argv else 'UI asset versions updated')

if __name__=='__main__':main()
