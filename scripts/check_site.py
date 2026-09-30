"""Check generated pages and all published local references without network requests."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json
import sys
ROOT = Path(__file__).resolve().parents[1]

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
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a: self.ids.append(a['id'])
        if tag == 'h1': self.h1 += 1
        if tag == 'main': self.main += 1
        if tag == 'label': self.labels.append(a.get('for'))
        if tag in ('input', 'select', 'textarea'): self.fields.append(a)
        if tag == 'img': self.images.append(a)
        if tag == 'link' and a.get('rel') == 'canonical': self.canonical.append(a.get('href'))
        for attr in ('src', 'href'):
            if a.get(attr): self.refs.append(a[attr])
        for part in a.get('srcset', '').split(','):
            if part.strip(): self.refs.append(part.strip().split()[0])

def check():
    pages = {}
    errors = []
    files = sorted(ROOT.glob('*.html')) + sorted((ROOT / 'albums').glob('*.html'))
    for f in files:
        p = Page(f);p.feed(f.read_text(encoding='utf-8'));pages[f.resolve()] = p
        if p.h1 != 1 or p.main != 1: errors.append(f'{f.name}: expected one h1 and one main')
        if len(p.ids) != len(set(p.ids)): errors.append(f'{f.name}: duplicate ids')
        if len(p.canonical) != 1: errors.append(f'{f.name}: canonical missing or duplicated')
        for field in p.fields:
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
            elif u.fragment and target in pages and unquote(u.fragment) not in pages[target].ids:
                errors.append(f'{f.name}: missing fragment {ref}')
    albums = json.loads((ROOT / 'data/albums.json').read_text(encoding='utf-8'))
    actual_images = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'images').rglob('*') if p.is_file()}
    for a in albums:
        for src in [a['cover'], *a['photos']]:
            if src not in actual_images: errors.append(f'{a["id"]}: exact filename case does not match: {src}')
        content = (ROOT / 'albums' / (a['id'] + '.html')).read_text(encoding='utf-8')
        if content.count('class="photo-link"') != len(a['photos']): errors.append(f'{a["id"]}: wrong photo count')
    if errors:
        print('\n'.join(errors));raise SystemExit(1)
    print(f'PASS: {len(pages)} pages, {len(albums)} albums, {sum(len(a["photos"]) for a in albums)} photo links, {total_refs} local references; headings, labels and fragments valid.')

if __name__ == '__main__': check()
