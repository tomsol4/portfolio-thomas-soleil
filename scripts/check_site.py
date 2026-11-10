"""Check generated pages and all published local references without network requests."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json
import re
import sys
import xml.etree.ElementTree as ET
from album_access import expand_protected_page, has_password, PAYLOAD
ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_IMAGES = {'images/logo.png', 'images/favicon-32.png', 'images/apple-touch-icon.png', 'images/hero-photo-accueil_2.webp'}


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
        if 'id' in a: self.ids.append(a['id'])
        if tag == 'h1': self.h1 += 1
        if tag == 'main': self.main += 1
        if tag == 'label': self.labels.append(a.get('for'))
        if tag in ('input', 'select', 'textarea'): self.fields.append(a)
        if tag == 'img': self.images.append(a)
        if tag == 'link' and a.get('rel') == 'canonical': self.canonical.append(a.get('href'))
        if tag == 'meta' and a.get('name') == 'robots': self.noindex = 'noindex' in a.get('content', '').lower()
        for attr in ('src', 'href'):
            if a.get(attr): self.refs.append(a[attr])
        for part in (a.get('srcset', '') + ',' + a.get('data-viewer-srcset', '')).split(','):
            if part.strip(): self.refs.append(part.strip().split()[0])
        if a.get('data-viewer-src'): self.refs.append(a['data-viewer-src'])

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
        p = Page(f);p.feed(content);pages[f.resolve()] = p
        if p.h1 != 1 or p.main != 1: errors.append(f'{f.name}: expected one h1 and one main')
        if len(p.ids) != len(set(p.ids)): errors.append(f'{f.name}: duplicate ids')
        if len(p.canonical) != 1: errors.append(f'{f.name}: canonical missing or duplicated')
        for field in p.fields:
            if field.get('type') == 'hidden': continue
            if field.get('id') not in p.labels: errors.append(f'{f.name}: unlabelled field {field.get("name")}')
        for img in p.images:
            if 'alt' not in img: errors.append(f'{f.name}: missing alt')
            if img.get('src') and ('width' not in img or 'height' not in img): errors.append(f'{f.name}: missing image dimensions')
    total_refs = 0
    for f, p in pages.items():
        for ref in p.refs:
            u = urlsplit(ref)
            if u.scheme or u.netloc: continue
            target = (ROOT / unquote(u.path.lstrip('/')) if u.path.startswith('/') else f.parent / unquote(u.path)).resolve() if u.path else f
            total_refs += 1
            if not target.is_file(): errors.append(f'{f.name}: missing {ref}')
            elif (ROOT / 'images') in target.parents:
                published = target.relative_to(ROOT).as_posix()
                if not published.startswith('images/optimized/') and published not in PUBLISHED_IMAGES:
                    errors.append(f'{f.name}: référence un original non publié : {ref}')
            elif u.fragment and target in pages and unquote(u.fragment) not in pages[target].ids:
                errors.append(f'{f.name}: missing fragment {ref}')
    albums = json.loads((ROOT / 'data/albums.json').read_text(encoding='utf-8'))
    actual_images = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'images').rglob('*') if p.is_file()}
    manifest_path = ROOT / 'data/image-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    selected = {src for a in albums for src in [a['cover'], *a['photos']]}
    originals_here = selected <= actual_images
    for a in albums:
        if any(src not in a['photos'] or not alt.strip() for src,alt in a.get('photo_alts',{}).items()):
            errors.append(f'{a["id"]}: image descriptions must refer to selected photographs')
        content = readable((ROOT / 'albums' / (a['id'] + '.html')).read_text(encoding='utf-8'))
        if content is None:
            print(f'Album protégé non vérifié (mot de passe absent sur cette machine) : {a["id"]}')
            continue
        for src in [a['cover'], *a['photos']]:
            if src not in actual_images and src not in manifest: errors.append(f'{a["id"]}: exact filename case does not match: {src}')
        if content.count('class="photo-link"') != len(a['photos']): errors.append(f'{a["id"]}: wrong photo count')
    descriptions = json.loads((ROOT / 'data/photo-descriptions.json').read_text(encoding='utf-8'))
    for album in albums:
        for src in album['photos']:
            if not (album.get('photo_alts', {}).get(src) or descriptions.get(src)):
                errors.append(f'{album["id"]}: missing descriptive alternative for {src}')
    for src,alt in descriptions.items():
        if not alt.strip() or (originals_here and src not in actual_images): errors.append(f'Invalid photo description: {src}')
    for file in files:
        content = file.read_text(encoding='utf-8')
        if file.name != '404.html':
            snippets = re.findall(r'<script type="application/ld\+json">(.*?)</script>',content,re.S)
            if not snippets: errors.append(f'{file.name}: missing structured data')
            for snippet in snippets:
                try: json.loads(snippet)
                except json.JSONDecodeError: errors.append(f'{file.name}: invalid structured data')
    for css in (ROOT / 'css').glob('*.css'):
        for ref in re.findall(r'url\([\'\"]?([^\)\'\"]+)',css.read_text(encoding='utf-8')):
            if not urlsplit(ref).scheme and not (css.parent / ref).is_file(): errors.append(f'{css.name}: missing {ref}')
    for location in ET.parse(ROOT / 'sitemap.xml').findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
        target = (ROOT / unquote(urlsplit(location.text).path.lstrip('/'))).resolve()
        if target.is_dir(): target = target / 'index.html'
        if target not in pages: errors.append(f'Sitemap: missing page {location.text}')
        elif pages[target].noindex: errors.append(f'Sitemap: noindex page {location.text}')
    if errors:
        print('\n'.join(errors));raise SystemExit(1)
    print(f'PASS: {len(pages)} pages, {len(albums)} albums, {sum(len(a["photos"]) for a in albums)} photo links, {total_refs} local references; headings, labels and fragments valid.')

if __name__ == '__main__': check()
