"""Generate the static portfolio. Originals and the explicit photo selection are preserved."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/python'))
import json
from html import escape
from collections import OrderedDict
from PIL import Image, ImageOps

BASE = 'https://www.tsoleil.fr'
ALBUMS = json.loads((ROOT / 'data/albums.json').read_text(encoding='utf-8'))
ASSETS = ROOT / 'images/optimized'
ASSETS.mkdir(parents=True, exist_ok=True)
CACHE = {}

def e(value):
    return escape(str(value), quote=True)

def write(path, content):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')

def asset(src):
    if src in CACHE:
        return CACHE[src]
    path = ROOT / src
    if not path.is_file():
        raise ValueError(f'Missing selected image: {src}')
    with Image.open(path) as original:
        im = ImageOps.exif_transpose(original).convert('RGB')
        width, height = im.size
        variants = []
        key = '_'.join(Path(src).with_suffix('').parts[1:])
        sizes = (480, 960, 1600) if src == ALBUMS[0]['cover'] else (480, 960)
        for size in sorted(set(min(n, width) for n in sizes)):
            target = ASSETS / f'{key}-{size}.webp'
            if not target.exists() or target.stat().st_size == 0 or target.stat().st_mtime < path.stat().st_mtime:
                resized = im.resize((size, max(1, round(height * size / width))), Image.Resampling.LANCZOS, reducing_gap=3.0)
                resized.save(target, 'WEBP', quality=80, method=4)
            variants.append((target.relative_to(ROOT).as_posix(), size))
    result = {'width': width, 'height': height, 'variants': variants}
    CACHE[src] = result
    return result

def picture(src, alt, prefix='', loading='lazy', sizes='(max-width: 760px) 45vw, 30vw', css='', hero=False):
    a = asset(src)
    variants = a['variants'] if hero else [v for v in a['variants'] if v[1] <= 960] or a['variants'][:1]
    srcset = ', '.join(f'{prefix}{p} {w}w' for p, w in variants)
    return (f'<img src="{prefix}{variants[0][0]}" srcset="{srcset}" sizes="{e(sizes)}" '
            f'width="{a["width"]}" height="{a["height"]}" alt="{e(alt)}" '
            f'loading="{loading}" decoding="async"' + (' fetchpriority="high"' if hero else '') +
            (f' class="{css}"' if css else '') + '>')

def social_image(src, name):
    target = ASSETS / f'og-{name}.jpg'
    source = ROOT / src
    # A cover can change to an older file, so mtime alone cannot validate it.
    with Image.open(source) as im:
        ImageOps.fit(ImageOps.exif_transpose(im).convert('RGB'), (1200, 630)).save(target, quality=85, optimize=True)
    return target.relative_to(ROOT).as_posix()

def layout(body, title, description, path, active='', prefix='', scripts=(), cover=None, noindex=False, schema=None):
    url = BASE + ('/' if path == 'index.html' else '/' + path)
    cover = cover or 'images/optimized/og-home.jpg'
    nav = ''
    for file, label in [('index.html', 'Albums'), ('prestations.html', 'Prestations'), ('a-propos.html', 'À propos'), ('contact.html', 'Contact')]:
        current = ' aria-current="page"' if file == active else ''
        css = ' class="nav-contact"' if file == 'contact.html' else ''
        href = '#albums' if file == 'index.html' and path == 'index.html' else prefix + file + ('#albums' if file == 'index.html' else '')
        nav += f'<a href="{href}"{current}{css}>{label}</a>\n'
    schema_tag = ''
    if schema:
        schema_tag = '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c') + '</script>'
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
{'<link rel="preload" as="image" href="images/hero-photo-accueil_2.webp">' if path == 'index.html' else ''}
{'<meta name="robots" content="noindex, follow">' if noindex else ''}
<link rel="canonical" href="{e(url)}">
<link rel="icon" type="image/png" sizes="32x32" href="{prefix}images/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="{prefix}images/apple-touch-icon.png">
<link rel="preload" href="{prefix}fonts/Rosehot.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{prefix}fonts/montserrat.css">
<link rel="stylesheet" href="{prefix}css/style.css">
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
<body{' class="home"' if path == 'index.html' else ''}>
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
    return f'''<section class="contact-banner" aria-labelledby="contact-title"><p class="eyebrow">Et si on en parlait ?</p><h2 id="contact-title">Votre prochain moment à raconter.</h2><p>Mariage, match, concert ou portrait : racontez-moi votre projet, je vous réponds sous 24 h.</p><a class="button" href="{prefix}contact.html">Discuter de mon projet</a></section>'''

def card(a, prefix=''):
    photo = picture(a['cover'], a['title'], prefix)
    details = ' · '.join(filter(None, [a.get('date'), f'{len(a["photos"])} photos']))
    return f'<a class="album-card" href="{prefix}albums/{a["id"]}.html"><div class="album-image">{photo}</div><div class="album-info"><h3>{e(a["title"])}</h3><p>{details}</p></div></a>'

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
    groups = OrderedDict()
    for a in ALBUMS:
        groups.setdefault(a['category'], []).append(a)
    group_ids = {'Rugby': 'rugby', 'Mariage': 'mariage', 'Concerts': 'concerts', 'Argentique': 'argentique', 'Autres regards': 'autres-regards'}
    categories = ''.join(f'<a href="#{group_ids[name]}">{e(name)}</a>' for name in groups)
    cards = ''.join(f'<section class="album-group" id="{group_ids[name]}" aria-labelledby="title-{group_ids[name]}"><h3 class="group-title" id="title-{group_ids[name]}">{e(name)}</h3><div class="albums-grid">' + ''.join(card(a).replace('<h3>', '<h4>').replace('</h3>', '</h4>') for a in albums) + '</div></section>' for name, albums in groups.items())
    home = f'''<main id="contenu">
<header class="hero hero-original"><div class="hero-copy"><h1>Thomas Soleil</h1><p class="hero-tagline">Photographe événementiel &amp; sportif</p><p class="hero-location">Toulouse &amp; Castres</p></div></header>
<section class="container section" id="albums" aria-labelledby="albums-title"><div class="section-heading"><div><p class="eyebrow">Le portfolio</p><h2 id="albums-title">Au plus près de l’instant.</h2></div><a class="text-link" href="prestations.html">Prestations &amp; tarifs →</a></div><p class="section-intro">Des terrains de rugby aux scènes de concert, des célébrations aux escapades : découvrez mes reportages.</p><nav class="category-links" aria-label="Catégories de reportages">{categories}</nav>{cards}</section>
<section class="about-preview section" aria-labelledby="about-title"><div class="container split">{picture('images/portrait.webp', 'Thomas Soleil, photographe à Toulouse et Castres', sizes='(max-width:760px) 90vw, 45vw', css='portrait')}<div class="about-copy"><p class="eyebrow">Derrière l’objectif</p><h2 id="about-title">Un regard qui vient du terrain.</h2><p>Je photographie ce qui bouge : rugby, mariages, concerts. Je chante et je joue au rugby moi-même ; ces deux passions nourrissent ma manière de raconter les moments que je photographie.</p><p>Entre Toulouse et Castres, je travaille en numérique et en argentique, selon le projet.</p><a class="text-link" href="a-propos.html">Faire connaissance →</a></div></div></section>
<section class="container values" aria-label="Mon approche"><div><h2>Un échange direct</h2><p>Une réponse personnalisée sous 24 h pour parler de votre projet.</p></div><div><h2>Numérique &amp; argentique</h2><p>Le format se choisit ensemble, selon les images que vous souhaitez.</p></div><div><h2>Des photos à partager</h2><p>Une livraison en haute définition, avec les modalités précisées dans votre devis.</p></div></section>{banner()}</main>'''
    schema = {'@context': 'https://schema.org', '@type': 'Person', 'name': 'Thomas Soleil', 'jobTitle': 'Photographe', 'url': BASE + '/', 'image': BASE + '/images/portrait.webp', 'sameAs': ['https://www.instagram.com/tomsol_photo/'], 'knowsAbout': ['Photographie sportive', 'Photographie de mariage', 'Photographie de concert', 'Photographie argentique']}
    write('index.html', layout(home, 'Thomas Soleil | Photographe à Toulouse & Castres', 'Photographe à Toulouse et Castres : mariages, rugby, concerts et portraits. Découvrez mes reportages en numérique et en argentique.', 'index.html', 'index.html', cover=home_og, schema=schema))

    pages = [
        ('prestations', 'Prestations & tarifs | Thomas Soleil, photographe', 'Portrait dès 70 €, mariage sur devis dès 600 €, sport et concerts sur devis. Photographe à Toulouse et Castres : parlons de votre projet.'),
        ('a-propos', 'À propos | Thomas Soleil, photographe à Toulouse', 'Rugby, chant et photographie argentique : découvrez le parcours et le regard de Thomas Soleil, photographe entre Toulouse et Castres.'),
        ('contact', 'Contact | Votre projet photo avec Thomas Soleil', 'Mariage, portrait, sport ou concert : contactez Thomas Soleil, photographe à Toulouse et Castres. Réponse personnalisée sous 24 h.'),
        ('mentions', 'Mentions légales & confidentialité | Thomas Soleil', 'Informations sur l’éditeur, l’hébergement, les photographies et l’utilisation des données du formulaire de contact de Thomas Soleil.')]
    for name, title, desc in pages:
        body = (ROOT / 'templates' / f'{name}.html').read_text(encoding='utf-8')
        body = body.replace('{{PORTRAIT}}', picture('images/portrait.webp', 'Thomas Soleil', loading='eager', sizes='(max-width:760px) 90vw, 45vw', css='portrait'))
        body = body.replace('{{BANNER}}', banner())
        write(f'{name}.html', layout(body, title, desc, f'{name}.html', f'{name}.html', scripts=('contact.js',) if name == 'contact' else (), cover=social_image('images/portrait.webp', 'about') if name == 'a-propos' else home_og))

    dialog = '''<dialog class="lightbox" id="lightbox" aria-label="Visionneuse de photographies"><div class="lightbox-top"><p id="photo-counter" aria-live="polite" aria-atomic="true"></p><button type="button" class="lightbox-close" aria-label="Fermer la photo" autofocus>×</button></div><div class="lightbox-stage"><button type="button" class="lightbox-prev" aria-label="Photo précédente">‹</button><img alt="" hidden><p class="photo-status" id="photo-status" role="status"></p><button type="button" class="lightbox-next" aria-label="Photo suivante">›</button></div><div class="lightbox-bottom"><span class="lightbox-hint">← → pour naviguer · Échap pour fermer</span><a id="photo-original" target="_blank" rel="noopener">Ouvrir la photo<span class="sr-only"> (nouvel onglet)</span></a></div></dialog>'''
    for a in ALBUMS:
        print(f'Building {a["id"]}: {len(a["photos"])} photos', flush=True)
        items = []
        for i, src in enumerate(a['photos']):
            alt = f'{a["title"]} — photographie {i + 1}'
            img = picture(src, alt, '../', loading='eager' if i < 3 else 'lazy')
            items.append(f'<li><a class="photo-link" href="../{e(src)}" aria-label="Agrandir : {e(alt)}">{img}</a></li>')
        path = f'albums/{a["id"]}.html'
        description = a['description']
        date_prefix = e(a['date']) + ' · ' if a.get('date') else ''
        body = f'''<main id="contenu"><div class="container"><header class="gallery-header"><a class="back-link" href="../index.html#albums">← Tous les reportages</a><h1>{e(a['title'])}</h1><p>{e(description)}</p><p class="gallery-meta">{date_prefix}{len(a['photos'])} photographies</p></header><ul class="photo-grid" aria-label="Photographies du reportage">{''.join(items)}</ul><div class="gallery-end"><a class="text-link" href="../index.html#albums">← Choisir un autre reportage</a><a class="button secondary" href="../contact.html?projet={a['project']}">Un projet similaire ?</a><a class="text-link" href="#contenu">Retour en haut ↑</a></div></div>{banner('../')}</main>{dialog}'''
        og = social_image(a['cover'], a['id'])
        schema = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': a['title'], 'description': description, 'url': BASE + '/' + path, 'image': BASE + '/' + og, 'author': {'@type': 'Person', 'name': 'Thomas Soleil'}}
        write(path, layout(body, a['title'] + ' | Thomas Soleil', description, path, 'index.html', '../', ('gallery.js',), cover=og, schema=schema))
    fallback = '<main id="contenu" class="container"><header class="page-header"><p class="eyebrow">Le portfolio</p><h1 id="gallery-heading">Choisissez un reportage</h1><p id="gallery-message">Retrouvez toutes les galeries de Thomas Soleil.</p></header><div class="albums-grid section">' + ''.join(card(a) for a in ALBUMS) + '</div></main>'
    write('galerie.html', layout(fallback, 'Les galeries | Thomas Soleil', 'Tous les reportages photographiques de Thomas Soleil.', 'galerie.html', 'index.html', scripts=('config.js',), noindex=True))
    routes = {a['id']: f'albums/{a["id"]}.html' for a in ALBUMS}
    write('js/config.js', "// Generated by scripts/build.py: compatibility with previously shared album URLs.\n(() => {\nconst routes = " + json.dumps(routes) + ";\nconst id = new URLSearchParams(location.search).get('id');\nif (id && Object.prototype.hasOwnProperty.call(routes, id)) location.replace(routes[id]);\nelse if (id) { document.getElementById('gallery-heading').textContent = 'Album introuvable'; document.getElementById('gallery-message').textContent = 'Cette adresse ne correspond à aucun album. Choisissez un reportage ci-dessous.'; }\n})();\n")
    missing = '<main id="contenu" class="container section"><p class="eyebrow">Erreur 404</p><h1>Cette page a changé de chemin.</h1><p>Retrouvez les reportages ou contactez-moi pour trouver ce que vous cherchez.</p><div class="actions"><a class="button" href="/index.html">Voir les reportages</a><a class="text-link" href="/contact.html">Me contacter</a></div></main>'
    write('404.html', layout(missing, 'Page introuvable | Thomas Soleil', 'Retrouvez les reportages de Thomas Soleil.', '404.html', prefix='/', noindex=True))
    urls = [''] + [name + '.html' for name, _, _ in pages] + [f'albums/{a["id"]}.html' for a in ALBUMS]
    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(f'<url><loc>{BASE}/{url}</loc></url>' for url in urls) + '\n</urlset>\n')
    write('robots.txt', 'User-agent: *\nAllow: /\nDisallow: /audit-site/\nDisallow: /test-results/\nSitemap: ' + BASE + '/sitemap.xml\n')
    print(f'Complete: {len(ALBUMS)} albums, {sum(len(a["photos"]) for a in ALBUMS)} photos.')

if __name__ == '__main__':
    build()
