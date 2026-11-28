"""Vérifie les pages générées et tous les liens internes publiés, sans rien demander à Internet."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json
import re
import xml.etree.ElementTree as ET
from album_access import expand_protected_page, has_password, PAYLOAD
from album_list import load_albums, page_photos, public_photos
from site_metadata import photo_descriptions

ROOT = Path(__file__).resolve().parents[1]
# Seules images publiées hors des exports web (images/optimized/).
PUBLISHED_IMAGES = {'images/logo-small.webp', 'images/favicon-32.png', 'images/apple-touch-icon.png', 'images/hero-photo-accueil_2.webp'}
REDIRECT = re.compile(r'<meta http-equiv="refresh"', re.I)


def readable(text):
    """Contenu vérifiable d'une page ; None pour un album chiffré dont le mot de passe est absent ici."""
    match = PAYLOAD.search(text)
    if match and not has_password(json.loads(match.group(1))['id']):
        return None
    return expand_protected_page(text)


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.refs = []
        self.ids = []
        self.h1 = 0
        self.main = 0
        self.labels = []
        self.fields = []
        self.images = []
        self.canonical = []
        self.noindex = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'h1':
            self.h1 += 1
        if tag == 'main':
            self.main += 1
        if tag == 'label':
            self.labels.append(a.get('for'))
        if tag in ('input', 'select', 'textarea'):
            self.fields.append(a)
        if tag == 'img':
            self.images.append(a)
        if tag == 'link' and a.get('rel') == 'canonical':
            self.canonical.append(a.get('href'))
        if tag == 'meta' and a.get('name') == 'robots':
            self.noindex = 'noindex' in a.get('content', '').lower()
        if tag == 'meta' and a.get('http-equiv', '').lower() == 'refresh':
            self.refs.append(a.get('content', '').split('url=', 1)[-1])
        for attr in ('src', 'href'):
            if a.get(attr):
                self.refs.append(a[attr])
        for part in (a.get('srcset', '') + ',' + a.get('data-srcset', '') + ',' + a.get('data-viewer-srcset', '')).split(','):
            if part.strip():
                self.refs.append(part.strip().split()[0])
        for attr in ('data-src', 'data-viewer-src'):
            if a.get(attr):
                self.refs.append(a[attr])


def check():
    pages = {}
    errors = []
    files = sorted(ROOT.glob('*.html'))
    for folder in ('albums', 'rugby', 'instants-de-vie', 'concerts', 'regards'):
        files += sorted((ROOT / folder).glob('*.html'))
    for f in files:
        text = f.read_text(encoding='utf-8')
        content = readable(text)
        if content is None:
            content = text
        p = Page(f)
        p.feed(content)
        pages[f.resolve()] = p
        if p.h1 != 1 or p.main != 1:
            errors.append(f'{f.name} : il faut exactement un titre h1 et une zone main')
        if len(p.ids) != len(set(p.ids)):
            errors.append(f'{f.name} : identifiants (id) en double')
        if len(p.canonical) != 1:
            errors.append(f'{f.name} : adresse canonique absente ou en double')
        for field in p.fields:
            if field.get('type') == 'hidden':
                continue
            if field.get('id') not in p.labels:
                errors.append(f'{f.name} : champ sans étiquette ({field.get("name")})')
        for img in p.images:
            if 'alt' not in img:
                errors.append(f'{f.name} : image sans texte alternatif')
            if img.get('src') and ('width' not in img or 'height' not in img):
                errors.append(f'{f.name} : image sans dimensions')
    total_refs = 0
    for f, p in pages.items():
        for ref in p.refs:
            u = urlsplit(ref)
            if u.scheme or u.netloc:
                continue
            target = (ROOT / unquote(u.path.lstrip('/')) if u.path.startswith('/') else f.parent / unquote(u.path)).resolve() if u.path else f
            total_refs += 1
            if not target.is_file():
                errors.append(f'{f.name} : lien cassé vers {ref}')
            elif (ROOT / 'images') in target.parents:
                published = target.relative_to(ROOT).as_posix()
                if not published.startswith('images/optimized/') and published not in PUBLISHED_IMAGES:
                    errors.append(f'{f.name} : référence un original non publié : {ref}')
            elif u.fragment and target in pages and unquote(u.fragment) not in pages[target].ids:
                errors.append(f'{f.name} : ancre introuvable {ref}')
    albums = load_albums(ROOT)
    actual_images = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'images').rglob('*') if p.is_file()}
    manifest_path = ROOT / 'data/image-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    for a in albums:
        if any(src not in a['photos'] or not alt.strip() for src, alt in a.get('photo_alts', {}).items()):
            errors.append(f'{a["id"]} : les descriptions de photos doivent concerner des photos de l’album')
        content = readable((ROOT / 'albums' / (a['id'] + '.html')).read_text(encoding='utf-8'))
        if content is None:
            print(f'Album protégé non vérifié (mot de passe absent sur cette machine) : {a["id"]}')
            continue
        for src in [a['cover'], *a['photos']]:
            if src not in actual_images and src not in manifest:
                errors.append(f'{a["id"]} : nom de fichier introuvable (attention aux majuscules) : {src}')
        if content.count('class="photo-link"') != len(a['photos']):
            errors.append(f'{a["id"]} : la page ne montre pas le bon nombre de photos')
    # Les descriptions sont facultatives ; celles qui existent doivent être valables, et aucune ne doit dire ce que
    # cache un album protégé (data/ est visible sur GitHub).
    descriptions = photo_descriptions(ROOT)
    public = public_photos(albums, page_photos(ROOT))
    for src in descriptions:
        if src not in public and any(src in a['photos'] for a in albums if a.get('password_protected')):
            errors.append(f'Description publiée d’une photo d’album protégé (elle dirait ce que l’album cache) : {src}')
    # Une description dont la photo a été supprimée n'apparaît nulle part : on l'ignore.
    for src, alt in descriptions.items():
        if not alt.strip():
            errors.append(f'Description de photo vide : {src}')
    for file in files:
        content = file.read_text(encoding='utf-8')
        if file.name == '404.html' or REDIRECT.search(content):
            continue  # page introuvable et anciennes adresses : rien à décrire pour Google
        snippets = re.findall(r'<script type="application/ld\+json">(.*?)</script>', content, re.S)
        if not snippets:
            errors.append(f'{file.name} : informations pour Google absentes')
        for snippet in snippets:
            try:
                json.loads(snippet)
            except json.JSONDecodeError:
                errors.append(f'{file.name} : informations pour Google illisibles')
    for css in (ROOT / 'css').glob('*.css'):
        for ref in re.findall(r'url\([\'\"]?([^\)\'\"]+)', css.read_text(encoding='utf-8')):
            if not urlsplit(ref).scheme and not (css.parent / ref).is_file():
                errors.append(f'{css.name} : fichier introuvable {ref}')
    for location in ET.parse(ROOT / 'sitemap.xml').findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
        target = (ROOT / unquote(urlsplit(location.text).path.lstrip('/'))).resolve()
        if target.is_dir():
            target = target / 'index.html'
        if target not in pages:
            errors.append(f'Plan du site : page absente {location.text}')
        elif pages[target].noindex:
            errors.append(f'Plan du site : page exclue de Google {location.text}')
    if errors:
        print('\n'.join(errors))
        raise SystemExit(1)
    print(f'OK : {len(pages)} pages, {len(albums)} albums, {sum(len(a["photos"]) for a in albums)} photos, '
          f'{total_refs} liens internes ; titres, étiquettes et ancres valides.')


if __name__ == '__main__':
    check()
