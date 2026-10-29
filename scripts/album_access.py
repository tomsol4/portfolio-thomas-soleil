"""Password-gate album markup while deliberately leaving image files public."""
from pathlib import Path
import base64
import getpass
import hashlib
import json
import os
import re
import sys
import shutil
import subprocess
from html import escape

ROOT = Path(__file__).resolve().parents[1]

PASSWORD_FILE = ROOT / '.tools/album-passwords.json'
ITERATIONS = 600000
PAYLOAD = re.compile(r'<script id="album-encrypted-data" type="application/json">(.*?)</script>', re.S)
LOCK_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/><path d="M12 14v3"/></svg>'


def load_passwords():
    if os.environ.get('ALBUM_PASSWORDS_JSON'):
        return json.loads(os.environ['ALBUM_PASSWORDS_JSON'])
    return json.loads(PASSWORD_FILE.read_text(encoding='utf-8')) if PASSWORD_FILE.exists() else {}


def password_for(album_id):
    password = load_passwords().get(album_id)
    if not isinstance(password, str) or not password:
        raise ValueError(f'Missing local album password for {album_id}. Run: python scripts/album_access.py {album_id}')
    return password


def lock_badge(album):
    return f'<span class="album-lock">{LOCK_ICON}<span class="sr-only">Album avec mot de passe</span></span>' if album.get('password_protected') else ''


def decrypt_markup(payload, password):
    salt = base64.b64decode(payload['salt'], validate=True)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, payload['iterations'], dklen=32)
    return transform('decrypt', key, base64.b64decode(payload['iv'], validate=True),
        base64.b64decode(payload['ciphertext'], validate=True),
        ('album:' + payload['id']).encode('utf-8')).decode('utf-8')


def transform(action, key, iv, data, associated):
    """Use Node's native AES-GCM; Playwright already bundles this runtime for local checks."""
    candidates = [shutil.which('node'), ROOT / '.tools/python/playwright/driver/node.exe',
                  ROOT / '.tools/python/playwright/driver/node']
    node = next((str(candidate) for candidate in candidates if candidate and Path(candidate).is_file()), None)
    if not node:
        raise RuntimeError('Album encryption needs Node.js or the Playwright development dependencies.')
    message = {name: base64.b64encode(value).decode('ascii') for name, value in
               [('key', key), ('iv', iv), ('data', data), ('associated', associated)]}
    message['action'] = action
    result = subprocess.run([node, str(ROOT / 'scripts/album_crypto.cjs')],
        input=json.dumps(message).encode('utf-8'), capture_output=True)
    if result.returncode:
        raise ValueError('Album encryption or password verification failed.')
    return base64.b64decode(result.stdout, validate=True)


def expand_protected_page(page):
    """Let local checks and asset pruning inspect the authenticated album content."""
    match = PAYLOAD.search(page)
    if not match:
        return page
    payload = json.loads(match.group(1))
    markup = decrypt_markup(payload, password_for(payload['id']))
    start = page.index('<main id="contenu"')
    end = page.index('</main>', start) + len('</main>')
    return page[:start] + markup + page[end:]


def protect_page(page, album, cover, previous=''):
    password = password_for(album['id'])
    start = page.index('<main id="contenu"')
    end = page.index('</dialog>', start) + len('</dialog>')
    markup = page[start:end]
    payload = None
    old = PAYLOAD.search(previous)
    if old:
        try:
            candidate = json.loads(old.group(1))
            if candidate['id'] == album['id'] and decrypt_markup(candidate, password) == markup:
                payload = candidate
        except (ValueError, KeyError):
            # Re-encrypt after password or album changes; never fall back to plaintext.
            payload = None
    if payload is None:
        salt, iv = os.urandom(16), os.urandom(12)
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS, dklen=32)
        encrypted = transform('encrypt', key, iv, markup.encode('utf-8'), ('album:' + album['id']).encode('utf-8'))
        payload = {'id': album['id'], 'version': 1, 'iterations': ITERATIONS,
                   'salt': base64.b64encode(salt).decode('ascii'),
                   'iv': base64.b64encode(iv).decode('ascii'),
                   'ciphertext': base64.b64encode(encrypted).decode('ascii')}
    return_href = {'Concerts': '../concerts/index.html#reportages', 'Mariage': '../instants-de-vie/index.html#reportages',
                   'Rugby': '../rugby/index.html#reportages'}.get(album['category'], '../regards/index.html')
    gate = f'''<main id="contenu" class="frame album-access-page">
<header class="collection-gallery-header"><a href="{return_href}">← Les reportages</a><p class="kicker">Album avec mot de passe</p><h1>{escape(album['title'])}</h1></header>
<div class="album-access-cover">{cover}</div>
<div class="album-access-intro"><p>Ce reportage est accessible avec un mot de passe.</p><button type="button" class="button" id="album-access-open">{LOCK_ICON} Ouvrir l’album</button></div>
<noscript><p class="album-access-note">Activez JavaScript dans votre navigateur pour saisir le mot de passe et ouvrir cet album.</p></noscript>
<dialog class="album-access-dialog" id="album-access-dialog" aria-labelledby="album-access-title" open>
<form id="album-access-form" method="post"><p class="kicker">Accès à l’album</p><h2 id="album-access-title">{escape(album['title'])}</h2>
<label for="album-password">Mot de passe</label><input id="album-password" name="album-password" type="password" autocomplete="current-password" maxlength="256" required autofocus aria-describedby="album-access-status">
<p id="album-access-status" role="status" aria-live="polite"></p><button class="button" type="submit" disabled>Ouvrir l’album</button><button class="album-access-cancel" type="button">Annuler</button></form>
</dialog><script id="album-encrypted-data" type="application/json">{json.dumps(payload, separators=(',', ':'))}</script>
</main>'''
    page = page[:start] + gate + page[end:]
    page = page.replace('<script src="../js/masonry.js" defer></script>', '')
    page = page.replace('<script src="../js/gallery.js" defer></script>', '<script src="../js/album-access.js" defer></script>')
    return page.replace('</head>', '<meta name="robots" content="noindex, follow"><link rel="stylesheet" href="../css/album-access.css"></head>', 1)


if __name__ == '__main__':
    album_id = sys.argv[1] if len(sys.argv) == 2 else ''
    albums = json.loads((ROOT / 'data/albums.json').read_text(encoding='utf-8'))
    if album_id not in {album['id'] for album in albums}:
        raise SystemExit('Usage: python scripts/album_access.py ALBUM_ID')
    password = getpass.getpass('Mot de passe réservé à cet album : ')
    if not password or password != getpass.getpass('Confirmer : '):
        raise SystemExit('Les mots de passe sont vides ou ne correspondent pas.')
    passwords = load_passwords()
    passwords[album_id] = password
    PASSWORD_FILE.parent.mkdir(exist_ok=True)
    PASSWORD_FILE.write_text(json.dumps(passwords, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Mot de passe enregistré localement. Régénérez le site avec python scripts/build.py.')
