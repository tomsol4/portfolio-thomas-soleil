"""Generate the static portfolio. Originals and the explicit photo selection are preserved."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/python'))
import json
import hashlib
import re
from html import escape
from urllib.parse import quote
from PIL import Image, ImageOps
from universes import build_universes, shell as universe_shell
from site_metadata import structured_data, PHOTO_DESCRIPTIONS
from gallery_markup import lightbox_markup
from album_access import protect_page, expand_protected_page
from navigation_icons import render_navigation_arrows

BASE = 'https://www.tsoleil.fr'
ALBUMS = json.loads((ROOT / 'data/albums.json').read_text(encoding='utf-8'))
ASSETS = ROOT / 'images/optimized'
ASSETS.mkdir(parents=True, exist_ok=True)
CACHE = {}
GENERATED_PAGES = set()
HIGH_RES_SOURCE_PREFIXES = ('images/rugby/', 'images/concert/concertsinfonia/')

def e(value):
    return escape(str(value), quote=True)

def write(path, content):
    target = ROOT / path
    if target.suffix == '.html':
        content = render_navigation_arrows(content)
    album = next((a for a in ALBUMS if path == f'albums/{a["id"]}.html' and a.get('password_protected')), None)
    if album:
        cover = picture(album['cover'], album['title'], '../', loading='eager', sizes='(max-width:760px) 90vw, 520px')
        content = render_navigation_arrows(protect_page(
            content, album, cover, target.read_text(encoding='utf-8') if target.exists() else ''))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    if target.suffix == '.html':
        GENERATED_PAGES.add(target)

def asset(src, large=False):
    high_resolution = src.startswith(HIGH_RES_SOURCE_PREFIXES)
    cache_key = (src, large)
    if cache_key in CACHE:
        return CACHE[cache_key]
    path = ROOT / src
    if not path.is_file():
        raise ValueError(f'Missing selected image: {src}')
    with Image.open(path) as original:
        # Reading dimensions is cheap; decode pixels only when a variant needs updating.
        width, height = original.size
        if original.getexif().get(274) in (5, 6, 7, 8):
            width, height = height, width
        im = None
        variants = []
        key = '_'.join(Path(src).with_suffix('').parts[1:])
        if re.search(r'[^A-Za-z0-9_.-]', key):
            # Keep generated filenames URL-safe without renaming the owner's originals.
            key = re.sub(r'[^A-Za-z0-9_.-]+', '-', key) + '-' + hashlib.sha256(src.encode()).hexdigest()[:8]
        if src == 'images/portrait.jpg':
            # Replaced portraits may keep an older file date; use their content for cache identity.
            key += '-' + hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        sizes = (480, 960, 1600) if large else (480, 960)
        if large and high_resolution:
            sizes = (480, 960, 1600, 2560)
        if large and src == 'images/hero-photo-accueil_2.webp':
            sizes = (480, 960, 1920)
        for size in sorted(set(min(n, width) for n in sizes)):
            if large and size == width and not high_resolution:
                variants.append((src, width))
                continue
            target = ASSETS / f'{key}-{size}.webp'
            if not target.exists() or target.stat().st_size == 0 or target.stat().st_mtime < path.stat().st_mtime:
                if im is None:
                    im = ImageOps.exif_transpose(original).convert('RGB')
                resized = im.resize((size, max(1, round(height * size / width))), Image.Resampling.LANCZOS, reducing_gap=3.0)
                quality = 88 if high_resolution and (size >= 1600 or (large and size == width)) else 80
                resized.save(target, 'WEBP', quality=quality, method=4)
            variants.append((target.relative_to(ROOT).as_posix(), size))
    result = {'width': width, 'height': height, 'variants': variants}
    CACHE[cache_key] = result
    return result

def picture(src, alt, prefix='', loading='lazy', sizes='(max-width: 760px) 45vw, 30vw', css='', hero=False, large=False):
    alt = PHOTO_DESCRIPTIONS.get(src, alt)
    a = asset(src, large=hero or large)
    variants = a['variants'] if hero or large else [v for v in a['variants'] if v[1] <= 960] or a['variants'][:1]
    if (hero or large) and not (src.startswith(HIGH_RES_SOURCE_PREFIXES) and variants[-1][1] == a['width']):
        # Keep the source itself as the best candidate for large displays.
        # This also avoids recompressing files that are already small exports.
        variants = [v for v in variants if v[1] < a['width']] + [(src, a['width'])]
    srcset = ', '.join(f'{prefix}{quote(p, safe="/")} {w}w' for p, w in variants)
    return (f'<img src="{prefix}{quote(variants[0][0], safe="/")}" srcset="{srcset}" sizes="{e(sizes)}" '
            f'width="{a["width"]}" height="{a["height"]}" alt="{e(alt)}" '
            f'loading="{loading}" decoding="async"' + (' fetchpriority="high"' if hero else '') +
            (f' style="--source-width:{a["width"]}px"' if hero else '') +
            (f' class="{css}"' if css else '') + '>')

def concert_viewer_asset(src):
    """Keep full source resolution available, with dedicated high-quality web exports."""
    normal = asset(src, large=not src.startswith('images/concert/concertsinfonia/'))
    if not src.startswith('images/concert/concertsinfonia/'):
        # The other concert already uses compact WebP masters; keep them intact.
        return {**normal, 'variants': [v for v in normal['variants'] if v[1] < normal['width']] + [(src, normal['width'])]}
    cache_key = (src, 'concert-viewer')
    if cache_key in CACHE:
        return CACHE[cache_key]
    source = ROOT / src
    base = Path(normal['variants'][0][0]).stem.removesuffix('-480')
    variants = [v for v in normal['variants'] if v[1] <= 480]
    with Image.open(source) as original:
        image = None
        for width in (size for size in (960, 1600, 2560, 3840) if size < normal['width']):
            target = ASSETS / f'{base}-viewer-hq-{width}.webp'
            if not target.exists() or target.stat().st_size == 0 or target.stat().st_mtime < source.stat().st_mtime:
                if image is None:
                    image = ImageOps.exif_transpose(original).convert('RGB')
                export = image.resize(
                    (width, max(1, round(normal['height'] * width / normal['width']))), Image.Resampling.LANCZOS)
                export.save(target, 'WEBP', quality=95, method=4)
            variants.append((target.relative_to(ROOT).as_posix(), width))
    # Exceptional very large displays can still choose the untouched master.
    variants.append((src, normal['width']))
    result = {**normal, 'variants': variants}
    CACHE[cache_key] = result
    return result


def social_image(src, name):
    target = ASSETS / f'og-{name}.jpg'
    source = ROOT / src
    # A cover can change to an older file, so mtime alone cannot validate it.
    with Image.open(source) as im:
        ImageOps.fit(ImageOps.exif_transpose(im).convert('RGB'), (1200, 630)).save(target, quality=85, optimize=True)
    return target.relative_to(ROOT).as_posix()

def layout(body, title, description, path, active='', prefix='', scripts=(), cover=None, noindex=False, schema=None):
    url = BASE + ('/' if path == 'index.html' else '/' + path)
    cover = cover or 'images/optimized/og-home-cover.jpg'
    nav = ''
    for file, label in [('index.html', 'Tous les univers'), ('a-propos.html', 'À propos'), ('contact.html', 'Contact')]:
        current = ' aria-current="page"' if file == active else ''
        css = ' class="nav-contact"' if file == 'contact.html' else ''
        href = prefix + file + ('#univers' if file == 'index.html' else '')
        nav += f'<a href="{href}"{current}{css}>{label}</a>\n'
    page_type = 'ContactPage' if path == 'contact.html' else 'AboutPage' if path == 'a-propos.html' else 'CollectionPage' if path.startswith('albums/') else 'WebPage'
    schema_tag = '' if noindex else structured_data(title, description, url, cover, page_type)
    extra_styles = ''.join(f'<link rel="stylesheet" href="{prefix}css/{name}.css">\n' for name in
                           (['gallery'] if path.startswith('albums/') else ['contact'] if path == 'contact.html' else []))
    script_tags = '\n'.join(f'<script src="{prefix}js/{s}" defer></script>' for s in ('main.js', *scripts))
    return f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta name="author" content="Thomas Soleil">
<meta name="theme-color" content="#f7f5f0">
<meta name="referrer" content="strict-origin-when-cross-origin">
{'<meta name="robots" content="noindex, follow">' if noindex else ''}
<link rel="canonical" href="{e(url)}">
<link rel="icon" type="image/png" sizes="32x32" href="{prefix}images/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="{prefix}images/apple-touch-icon.png">
<link rel="preload" href="{prefix}fonts/CormorantGaramond-normal-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{prefix}fonts/cormorant-garamond.css">
<link rel="stylesheet" href="{prefix}fonts/montserrat.css">
<link rel="stylesheet" href="{prefix}css/style.css">
<link rel="stylesheet" href="{prefix}css/navigation-icons.css">
{extra_styles}
<meta property="og:type" content="website">
<meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="Thomas Soleil — Photographe">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{BASE}/{cover}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(title)}">
<meta name="twitter:card" content="summary_large_image">
{schema_tag}
{script_tags}
</head>
<body>
<a class="skip-link" href="#contenu">Aller au contenu</a>
<nav class="site-nav" aria-label="Navigation principale">
<a href="{prefix}index.html" class="logo" aria-label="Thomas Soleil — Accueil"><img src="{prefix}images/logo.png" width="46" height="58" alt=""><span>Thomas Soleil<br>Photographe</span></a>
<button class="menu-toggle" type="button" aria-expanded="false" aria-controls="navigation" aria-label="Ouvrir le menu"><span aria-hidden="true"></span><span aria-hidden="true"></span></button>
<div class="nav-links" id="navigation">{nav}</div>
</nav>
{body}
<footer class="site-footer"><div class="container footer-inner">
<p>© <span id="footer-year">2026</span> Thomas Soleil · Toulouse &amp; Castres</p>
<div class="footer-links"><a href="{prefix}mentions.html">Mentions légales &amp; confidentialité</a><a href="{prefix}contact.html">Contact</a><a href="https://www.instagram.com/tomsol_photo/" target="_blank" rel="noopener noreferrer">Instagram<span class="sr-only"> (nouvel onglet)</span></a></div>
</div></footer>
</body></html>'''

def banner(prefix=''):
    return f'''<section class="contact-banner" aria-labelledby="contact-title"><p class="eyebrow">Et si on en parlait ?</p><h2 id="contact-title">Votre prochain moment à raconter.</h2><p>Mariage, match, concert ou portrait : racontez-moi votre projet, préparons ensemble votre reportage.</p><a class="button" href="{prefix}contact.html">Discuter de mon projet</a></section>'''


def prune_optimized_images():
    """Remove only derived images that the current site no longer references."""
    references = set()
    sources = GENERATED_PAGES | set((ROOT / 'css').glob('*.css')) | set((ROOT / 'js').glob('*.js'))
    sources.add(ROOT / 'data/albums.json')
    for source in sources:
        references.update(re.findall(r'images/optimized/([A-Za-z0-9_.-]+)', expand_protected_page(source.read_text(encoding='utf-8'))))
    missing = [name for name in references if not (ASSETS / name).is_file()]
    if missing:
        raise ValueError(f'Missing optimized images: {missing}')
    removed, size = 0, 0
    for path in ASSETS.iterdir():
        if path.is_symlink() or not path.is_file() or path.suffix not in ('.jpg', '.webp'):
            continue
        if path.resolve().parent != ASSETS.resolve():
            raise ValueError(f'Image outside the generated directory: {path}')
        if path.name not in references:
            size += path.stat().st_size
            path.unlink()
            removed += 1
    print(f'Optimized image cleanup: {removed} unused files, {size / 1048576:.1f} MiB removed.')

def build():
    ids = [a['id'] for a in ALBUMS]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate album id')
    for a in ALBUMS:
        if not a['photos'] or len(a['photos']) != len(set(a['photos'])):
            raise ValueError(f'Empty or duplicate photo selection: {a["id"]}')
        for src in [a['cover'], *a['photos']]:
            if not (ROOT / src).is_file():
                raise ValueError(f'Missing image: {src}')
    with Image.open(ROOT / 'images/favicon1.png') as icon:
        for size, name in [(32, 'favicon-32.png'), (180, 'apple-touch-icon.png')]:
            ImageOps.contain(icon.convert('RGBA'), (size, size)).save(ROOT / 'images' / name, optimize=True)
    hero_src = 'images/hero-photo-accueil_2.webp'
    home_og = social_image(hero_src, 'home-cover')
    print_references = build_universes(ALBUMS, picture, write, home_og, asset)

    pages = [
        ('a-propos', 'À propos | Thomas Soleil, photographe à Toulouse', 'Rugby, chant et photographie argentique : découvrez le parcours et le regard de Thomas Soleil, photographe entre Toulouse et Castres.'),
        ('contact', 'Contact | Votre projet photo avec Thomas Soleil', 'Sport, mariage, événement ou concert : contactez Thomas Soleil, photographe à Toulouse et Castres. Échange personnalisé autour de votre projet.'),
        ('mentions', 'Mentions légales & confidentialité | Thomas Soleil', 'Informations sur l’éditeur, l’hébergement, les photographies et l’utilisation des données du formulaire de contact de Thomas Soleil.')]
    for name, title, desc in pages:
        body = (ROOT / 'templates' / f'{name}.html').read_text(encoding='utf-8')
        body = body.replace('{{PORTRAIT}}', picture('images/portrait.jpg', 'Thomas Soleil', loading='eager', sizes='(max-width:760px) 90vw, 45vw', css='portrait'))
        body = body.replace('{{BANNER}}', banner())
        write(f'{name}.html', layout(body, title, desc, f'{name}.html', f'{name}.html', scripts=('contact.js',) if name == 'contact' else (), cover=social_image('images/portrait.jpg', 'about') if name == 'a-propos' else home_og))

    dialog = lightbox_markup()
    for a in ALBUMS:
        print(f'Building {a["id"]}: {len(a["photos"])} photos', flush=True)
        items = []
        for i, src in enumerate(a['photos']):
            alt = a.get('photo_alts', {}).get(src, PHOTO_DESCRIPTIONS.get(src, f'{a["title"]} — photographie {i + 1}'))
            viewer = concert_viewer_asset(src) if a['category'] == 'Concerts' else asset(src, large=True)
            img = picture(src, alt, '../', loading='eager' if i < 3 else 'lazy')
            candidates = viewer['variants']
            if a['category'] == 'Mariage':
                # Offer the replacement master for large/dense screens and the original-file link.
                candidates = [v for v in candidates if v[1] < viewer['width']] + [(src, viewer['width'])]
            elif a['category'] != 'Concerts' and src.startswith(HIGH_RES_SOURCE_PREFIXES) and candidates[-1][1] < viewer['width']:
                candidates = [*candidates, (src, viewer['width'])]
            viewer_srcset = ', '.join(f'../{quote(p, safe="/")} {w}w' for p, w in candidates)
            ratio = viewer['width'] / viewer['height']
            print_attribute = f' data-print-reference="{print_references[src]}"' if src in print_references else ''
            items.append(f'<li style="--photo-ratio:{ratio:.6f}"><a class="photo-link" href="../{e(quote(src, safe="/"))}" data-viewer-src="../{e(quote(candidates[-1][0], safe="/"))}" data-viewer-srcset="{e(viewer_srcset)}"{print_attribute} aria-label="Agrandir : {e(alt)}">{img}</a></li>')
        path = f'albums/{a["id"]}.html'
        description = a['description']
        date_prefix = e(a['date']) + ' · ' if a.get('date') else ''
        context = f'<p class="gallery-description">{e(description)}</p><p class="gallery-meta">{date_prefix}{len(a["photos"])} photographies</p>'
        top_link = '<a class="back-to-top" href="#contenu" hidden>Retour en haut <span aria-hidden="true">↑</span></a>'
        body = f'''<main id="contenu"><div class="container"><header class="gallery-header"><a class="back-link" href="../index.html#univers">← Tous les univers</a><h1>{e(a['title'])}</h1><p>{e(description)}</p><p class="gallery-meta">{date_prefix}{len(a['photos'])} photographies</p></header><ul class="photo-grid" aria-label="Photographies du reportage">{''.join(items)}</ul><div class="gallery-end"><a class="text-link" href="../index.html#univers">← Choisir un univers</a><a class="button secondary" href="../contact.html?projet={a['project']}">Un projet similaire ?</a><a class="text-link" href="#contenu">Retour en haut ↑</a></div></div>{banner('../')}</main>{dialog}'''
        og = social_image(a['cover'], a['id'])
        schema = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': a['title'], 'description': description, 'url': BASE + '/' + path, 'image': BASE + '/' + og, 'author': {'@type': 'Person', 'name': 'Thomas Soleil'}}
        if a['category'] == 'Rugby':
            body = f'''<main id="contenu"><div class="frame"><header class="rugby-gallery-header"><a href="../rugby/index.html#reportages">← Les reportages rugby</a><h1>{e(a['title'].removeprefix('Rugby — '))}</h1><p class="gallery-description">{e(description)}</p></header><ul class="photo-grid" aria-label="Photographies du reportage">{''.join(items)}</ul><div class="gallery-end"><a href="../rugby/index.html#reportages">← Les reportages</a><a class="button outline" href="../rugby/contact.html">Demander un reportage sport ↗</a></div></div>{top_link}</main>{dialog}'''
            write(path, universe_shell(body, a['title'] + ' | Thomas Soleil Rugby', description, path, 'rugby', '../', og, ('masonry.js', 'gallery.js')))
        elif a['category'] in ('Argentique', 'Autres regards'):
            gallery_label = 'Photographies individuelles' if a.get('presentation') == 'individual' else 'Photographies de la série'
            body = f'''<main id="contenu" class="frame art-gallery"><header class="art-gallery-header"><h1>{e(a['title'])}</h1>{context}</header><ul class="photo-grid" aria-label="{gallery_label}">{''.join(items)}</ul><div class="gallery-end"><a href="../regards/index.html">← Les projets personnels</a></div>{top_link}</main>{dialog}'''
            write(path, universe_shell(body, a['title'] + ' | Thomas Soleil', description, path, 'regards', '../', og, ('masonry.js', 'gallery.js')))
        elif a['category'] in ('Mariage', 'Concerts'):
            universe = 'instants-de-vie' if a['category'] == 'Mariage' else 'concerts'
            contact_href = f'../{universe}/contact.html'
            return_href = f'../{universe}/index.html' + ('#reportages' if a['category'] == 'Concerts' else '')
            body = f'''<main id="contenu" class="frame"><header class="collection-gallery-header"><a href="{return_href}">← Les reportages</a><h1>{e(a['title'])}</h1>{context}</header><ul class="photo-grid" aria-label="Photographies du reportage">{''.join(items)}</ul><div class="gallery-end"><a href="{return_href}">← Les reportages</a><a href="{contact_href}">Contact ↗</a></div>{top_link}</main>{dialog}'''
            write(path, universe_shell(body, a['title'] + ' | Thomas Soleil', description, path, universe, '../', og, ('masonry.js', 'gallery.js')))
        else:
            write(path, layout(body, a['title'] + ' | Thomas Soleil', description, path, '', '../', ('masonry.js', 'gallery.js'), cover=og, schema=schema))
    missing = '<main id="contenu" class="container section"><p class="eyebrow">Erreur 404</p><h1>Cette page a changé de chemin.</h1><p>Retrouvez les reportages ou contactez-moi pour trouver ce que vous cherchez.</p><div class="actions"><a class="button" href="/index.html#univers">Découvrir les univers</a><a class="text-link" href="/contact.html">Me contacter</a></div></main>'
    write('404.html', layout(missing, 'Page introuvable | Thomas Soleil', 'Retrouvez les reportages de Thomas Soleil.', '404.html', prefix='/', noindex=True))
    urls = ['', 'rugby/index.html', 'rugby/contact.html', 'rugby/tarifs.html', 'instants-de-vie/index.html', 'instants-de-vie/prestations.html', 'instants-de-vie/contact.html', 'concerts/index.html', 'concerts/tarifs.html', 'concerts/contact.html', 'regards/index.html', 'regards/tirages.html'] + [name + '.html' for name, _, _ in pages] + [f'albums/{a["id"]}.html' for a in ALBUMS]
    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(f'<url><loc>{BASE}/{url}</loc></url>' for url in urls) + '\n</urlset>\n')
    write('robots.txt', 'User-agent: *\nAllow: /\nDisallow: /test-results/\nSitemap: ' + BASE + '/sitemap.xml\n')
    prune_optimized_images()
    print(f'Complete: {len(ALBUMS)} albums, {sum(len(a["photos"]) for a in ALBUMS)} photos.')

if __name__ == '__main__':
    build()
