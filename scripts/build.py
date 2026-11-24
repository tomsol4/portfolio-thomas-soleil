"""Génère le site statique.

Les originaux (tout ce qui se trouve dans images/ hors images/optimized/) ne sont jamais
publiés : les pages ne référencent que des exports web de images/optimized/, limités à
MAX_WIDTH pixels de large. Les dimensions des originaux sont mémorisées dans
data/image-manifest.json, ce qui permet de régénérer les pages sur une machine où les
originaux sont absents (tant que les exports existent déjà).
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/python'))
import json
import hashlib
import re
import shutil
from datetime import date
from html import escape
from urllib.parse import quote
from PIL import Image, ImageOps
from universes import build_universes, shell, PAGE_PHOTOS, LOGO
from site_metadata import public_url, PHOTO_DESCRIPTIONS, BASE, INSTAGRAM
from gallery_markup import lightbox_markup
from album_access import protect_page, expand_protected_page, has_password, PRIVATE_EXPORTS
from navigation_icons import render_navigation_arrows
from prices import price_tokens
from album_list import load_albums, page_photos, public_photos

ALBUMS = load_albums()
ASSETS = ROOT / 'images/optimized'
ASSETS.mkdir(parents=True, exist_ok=True)
CACHE = {}
GENERATED_PAGES = set()
# Originaux en haute définition : leurs exports montent jusqu'à MAX_WIDTH pixels de large.
HIGH_RES_SOURCE_PREFIXES = ('images/rugby/', 'images/concert/concertsinfonia/', 'images/concert/repetition_bougie_sinfonia/')
MAX_WIDTH = 2560
FULL_WIDTH_PREFIXES = ('images/mariage/',)
# Qualité des exports web, sur 100 : les grandes versions (visionneuse) et les autres. Il suffit de changer un nombre :
# à la génération suivante, les exports concernés sont refaits, car la qualité de chaque export est notée dans
# data/image-manifest.json (« qualites »). Les exports faits avant cette notation (novembre 2026) étaient en 80.
QUALITY = 80
QUALITY_LARGE = 82
LEGACY_QUALITY = 80
MANIFEST_PATH = ROOT / 'data/image-manifest.json'
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding='utf-8')) if MANIFEST_PATH.exists() else {}
SITEMAP_DATES_PATH = ROOT / 'data/sitemap-dates.json'
FROZEN = set()
# Photos réservées aux albums protégés : leurs exports lisibles vont dans PRIVATE_EXPORTS, jamais dans ASSETS.
PRIVATE_SOURCES = set()
# Jetons utilisables dans tous les modèles de pages : les prix ({{PRIX_…}}) et l'adresse Instagram.
TOKENS = {**price_tokens(), '{{INSTAGRAM}}': INSTAGRAM}
LEFTOVER_TOKEN = re.compile(r'\{\{[A-Z0-9_]+\}\}')
# Logo des pages : une copie de images/logo.png assez grande pour un écran très dense (56 px affichés × 3, et plus).
LOGO_SOURCE = ROOT / 'images/logo.png'
LOGO_SIZE = 210
# Anciennes adresses, remplacées par une section d'une autre page.
REDIRECTS = {'rugby/a-propos.html': ('index.html#presentation', 'À propos'),
             'instants-de-vie/a-propos.html': ('index.html#presentation', 'À propos'),
             'concerts/tarifs.html': ('contact.html#questions', 'Questions fréquentes')}


def export_path(src, name):
    """Emplacement d'un export web : hors du site pour les photos d'un album protégé."""
    if src not in PRIVATE_SOURCES:
        return ASSETS / name
    PRIVATE_EXPORTS.mkdir(parents=True, exist_ok=True)
    target, published = PRIVATE_EXPORTS / name, ASSETS / name
    if published.is_file():
        if target.is_file():
            published.unlink()
        else:
            shutil.move(published, target)
    return target


def e(value):
    return escape(str(value), quote=True)


VERSIONS = {}


def versioned(match):
    """Ajoute l'empreinte du fichier à l'adresse d'un script ou d'un style.

    Un navigateur qui a gardé une ancienne version en cache recharge ainsi le fichier dès qu'il change :
    une page récente n'est jamais servie avec un script périmé.
    """
    file = f'{match[2]}/{match[3]}'
    if file not in VERSIONS:
        source = ROOT / file
        VERSIONS[file] = hashlib.sha256(source.read_bytes()).hexdigest()[:10] if source.is_file() else ''
    return match[0] if not VERSIONS[file] else f'"{match[1]}{file}?v={VERSIONS[file]}"'


def write(path, content):
    target = ROOT / path
    if target.suffix == '.html':
        for token, value in TOKENS.items():
            content = content.replace(token, value)
        leftover = LEFTOVER_TOKEN.search(content)
        if leftover:
            raise ValueError(f'Jeton non remplacé dans {path} : {leftover[0]}')
        content = render_navigation_arrows(content)
    album = next((a for a in ALBUMS if path == f'albums/{a["id"]}.html' and a.get('password_protected')), None)
    if album:
        cover = picture(album['cover'], album['title'], '../', loading='eager', sizes='(max-width:760px) 90vw, 520px')
        content = render_navigation_arrows(protect_page(
            content, album, cover, target.read_text(encoding='utf-8') if target.exists() else '', ASSETS))
    if target.suffix == '.html':
        content = re.sub(r'"((?:\.\./|/)?)(css|js|fonts)/([A-Za-z0-9_.-]+\.(?:css|js))"', versioned, content)
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
    available = path.is_file()
    entry = dict(MANIFEST.get(src, {}))
    rotated = False
    if available:
        with Image.open(path) as probe:
            width, height = probe.size
            orientation = probe.getexif().get(274)
            rotated = orientation in (2, 3, 4, 5, 6, 7, 8)
            if orientation in (5, 6, 7, 8):
                width, height = height, width
        entry.update(width=width, height=height)
        if src == 'images/portrait.jpg':
            entry['digest'] = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    elif 'width' in entry:
        width, height = entry['width'], entry['height']
    else:
        raise ValueError(f'Original introuvable et absent de data/image-manifest.json : {src}')
    MANIFEST[src] = entry
    key = variant_key(src)
    sizes = (480, 960)
    if large:
        sizes = (480, 960, 1600, MAX_WIDTH) if high_resolution or src.startswith(FULL_WIDTH_PREFIXES) else (480, 960, 1600)
    variants = []
    im = None
    qualities = entry.setdefault('qualites', {})
    for size in sorted(set(min(n, width) for n in sizes)):
        target = export_path(src, f'{key}-{size}.webp')
        exported = target.exists() and target.stat().st_size > 0
        if available:
            # Pleine largeur : un original WebP est publié tel quel ; sinon la grande version prend QUALITY_LARGE.
            if size == width and not high_resolution and not rotated and path.suffix.lower() == '.webp':
                wanted = 'original'
            else:
                wanted = QUALITY_LARGE if size == width or (high_resolution and size >= 1600) else QUALITY
            fresh = exported and target.stat().st_mtime >= path.stat().st_mtime and qualities.get(str(size), LEGACY_QUALITY) == wanted
            if not fresh:
                if wanted == 'original':
                    shutil.copyfile(path, target)
                else:
                    if im is None:
                        with Image.open(path) as original:
                            im = ImageOps.exif_transpose(original).convert('RGB')
                    resized = im if size == width else im.resize(
                        (size, max(1, round(height * size / width))), Image.Resampling.LANCZOS, reducing_gap=3.0)
                    resized.save(target, 'WEBP', quality=wanted, method=4)
            qualities[str(size)] = wanted
        elif not exported:
            raise ValueError(f'Export web manquant ({target.name}) et original absent : {src}')
        variants.append((f'images/optimized/{target.name}', size))
    result = {'width': width, 'height': height, 'variants': variants}
    CACHE[cache_key] = result
    return result


def variant_key(src):
    """Nom de base, sûr dans une URL, des exports web d'un original."""
    key = '_'.join(Path(src).with_suffix('').parts[1:])
    if re.search(r'[^A-Za-z0-9_.-]', key):
        key = re.sub(r'[^A-Za-z0-9_.-]+', '-', key) + '-' + hashlib.sha256(src.encode()).hexdigest()[:8]
    if src == 'images/portrait.jpg':
        path = ROOT / src
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12] if path.is_file() else MANIFEST.get(src, {}).get('digest')
        if not digest:
            raise ValueError('Portrait introuvable et absent de data/image-manifest.json')
        key += '-' + digest
    return key


def known(src):
    return (ROOT / src).is_file() or 'width' in MANIFEST.get(src, {})


def picture(src, alt, prefix='', loading='lazy', sizes='(max-width: 760px) 45vw, 30vw', css='', hero=False, large=False):
    alt = PHOTO_DESCRIPTIONS.get(src, alt)
    a = asset(src, large=hero or large)
    variants = a['variants'] if hero or large else [v for v in a['variants'] if v[1] <= 960] or a['variants'][:1]
    srcset = ', '.join(f'{prefix}{quote(p, safe="/")} {w}w' for p, w in variants)
    return (f'<img src="{prefix}{quote(variants[0][0], safe="/")}" srcset="{srcset}" sizes="{e(sizes)}" '
            f'width="{a["width"]}" height="{a["height"]}" alt="{e(alt)}" '
            f'loading="{loading}" decoding="async"' + (' fetchpriority="high"' if hero else '') +
            (f' style="--source-width:{a["width"]}px"' if hero else '') +
            (f' class="{css}"' if css else '') + '>')


def social_image(src, name):
    """Image de partage (réseaux sociaux, messageries) : 1200 × 630 px, recadrée depuis l'original.

    Elle n'est refaite que si l'original est plus récent qu'elle."""
    target = ASSETS / f'og-{name}.jpg'
    source = ROOT / src
    if not source.is_file() or (target.is_file() and target.stat().st_mtime >= source.stat().st_mtime):
        if target.is_file():
            return target.relative_to(ROOT).as_posix()
        raise ValueError(f'Image de partage manquante ({target.name}) et original absent : {src}')
    with Image.open(source) as im:
        ImageOps.fit(ImageOps.exif_transpose(im).convert('RGB'), (1200, 630)).save(target, quality=85, optimize=True)
    return target.relative_to(ROOT).as_posix()


def small_logo():
    """Fabrique la petite copie du logo utilisée par les pages (WebP sans perte : identique à l'écran)."""
    target = ROOT / LOGO
    if not LOGO_SOURCE.is_file():
        if target.is_file():
            return
        raise ValueError(f'Logo introuvable : {LOGO_SOURCE.relative_to(ROOT).as_posix()}')
    if target.is_file() and target.stat().st_mtime >= LOGO_SOURCE.stat().st_mtime:
        return
    with Image.open(LOGO_SOURCE) as logo:
        ImageOps.contain(logo.convert('RGBA'), (LOGO_SIZE, LOGO_SIZE), Image.Resampling.LANCZOS).save(target, 'WEBP', lossless=True)


def redirect(path, target, label):
    """Ancienne adresse : renvoie aussitôt vers la page qui l'a remplacée (GitHub Pages n'a pas de vraie redirection)."""
    folder = path.rsplit('/', 1)[0] + '/' if '/' in path else ''
    canonical = public_url(folder + target.split('#')[0])
    write(path, f'''<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(label)} | Thomas Soleil</title><meta name="robots" content="noindex, follow">
<link rel="canonical" href="{e(canonical)}"><meta http-equiv="refresh" content="0; url={e(target)}"></head>
<body><main><h1>{e(label)}</h1><p>Cette page a changé d’adresse : <a href="{e(target)}">continuer vers la nouvelle page</a>.</p></main></body></html>
''')


def legal_blocks():
    """Bloc d'identification légal, construit à partir de data/legal.json (valeurs vides omises)."""
    data = json.loads((ROOT / 'data/legal.json').read_text(encoding='utf-8'))
    lines = [f'Ce site est édité par <strong>{e(data["nom"])}</strong>, {e(data["statut"])}, {e(data["activite"])}.']
    if data.get('adresse'):
        lines.append(f'Adresse : {e(data["adresse"])}.')
    if data.get('siret'):
        lines.append(f'SIRET : {e(data["siret"])} — entreprise immatriculée au Registre national des entreprises (RNE).')
    if data.get('numero_tva'):
        lines.append(f'Numéro de TVA intracommunautaire : {e(data["numero_tva"])}.')
    elif data.get('tva_non_applicable'):
        lines.append('TVA non applicable, article 293 B du Code général des impôts.')
    contact = []
    if data.get('email'):
        contact.append(f'<a href="mailto:{e(data["email"])}">{e(data["email"])}</a>')
    if data.get('telephone'):
        contact.append(f'<a href="tel:{e(re.sub(r"[^0-9+]", "", data["telephone"]))}">{e(data["telephone"])}</a>')
    contact.append('<a href="index.html#contact">formulaire de contact</a>')
    publisher = ('<p>' + '<br>'.join(lines) + '</p><p>Directeur de la publication : ' + e(data['nom']) +
                 '.<br>Contact : ' + ' · '.join(contact) + '.</p>')
    host = data['hebergeur']
    host_lines = [f'Le site est hébergé par <a href="{e(host["site"])}">{e(host["nom"])}</a>.', f'Adresse : {e(host["adresse"])}.']
    if host.get('telephone'):
        host_lines.append(f'Téléphone : {e(host["telephone"])}.')
    mediator = data.get('mediateur', {})
    mediation = ''
    if mediator.get('nom'):
        details = ', '.join(e(part) for part in [mediator.get('adresse')] if part)
        site = f' — <a href="{e(mediator["site"])}">{e(mediator["site"])}</a>' if mediator.get('site') else ''
        mediation = ('\n<h2>Médiation de la consommation</h2><p>En cas de litige, après une réclamation écrite restée sans solution, '
                     'vous pouvez recourir gratuitement au médiateur de la consommation suivant : '
                     f'<strong>{e(mediator["nom"])}</strong>{", " + details if details else ""}{site}.</p>')
    return {'{{LEGAL_PUBLISHER}}': publisher, '{{LEGAL_HOST}}': '<p>' + '<br>'.join(host_lines) + '</p>', '{{LEGAL_MEDIATION}}': mediation}


def prune_optimized_images():
    """Supprime les seuls exports web que plus aucune page, feuille de style ou script n'utilise."""
    references = set()
    sources = GENERATED_PAGES | set((ROOT / 'css').glob('*.css')) | set((ROOT / 'js').glob('*.js'))
    sources.add(ROOT / 'data/albums.json')
    frozen_pages = {ROOT / f'albums/{album_id}.html' for album_id in FROZEN}
    for source in sources:
        text = source.read_text(encoding='utf-8')
        references.update(re.findall(r'images/optimized/([A-Za-z0-9_.-]+)', text if source in frozen_pages else expand_protected_page(text)))
    frozen_prefixes = tuple(variant_key(src) + '-' for a in ALBUMS if a['id'] in FROZEN for src in [a['cover'], *a['photos']])
    missing = [name for name in references if not (ASSETS / name).is_file()]
    if missing:
        raise ValueError(f'Exports web manquants : {missing}')
    removed, size = 0, 0
    for path in ASSETS.iterdir():
        if path.is_symlink() or not path.is_file() or path.suffix not in ('.jpg', '.webp', '.bin'):
            continue
        if path.suffix == '.bin' and FROZEN:
            continue  # images chiffrées d'un album non régénéré : sa page ne peut pas être lue ici
        if path.resolve().parent != ASSETS.resolve():
            raise ValueError(f'Image hors du dossier des exports : {path}')
        if path.name not in references and not (frozen_prefixes and path.name.startswith(frozen_prefixes)):
            size += path.stat().st_size
            path.unlink()
            removed += 1
    print(f'Nettoyage des exports web : {removed} fichiers inutilisés supprimés ({size / 1048576:.1f} Mo).')


def build():
    ids = [a['id'] for a in ALBUMS]
    if len(ids) != len(set(ids)):
        raise ValueError('Deux albums ont le même id dans data/albums.json')
    for a in ALBUMS:
        if not a['photos'] or len(a['photos']) != len(set(a['photos'])):
            raise ValueError(f'Album vide ou photo en double : {a["id"]}')
        if a.get('password_protected') and not has_password(a['id']):
            if not (ROOT / f'albums/{a["id"]}.html').is_file():
                raise ValueError(f'Album protégé sans mot de passe local ni page existante : {a["id"]}')
            FROZEN.add(a['id'])
            GENERATED_PAGES.add(ROOT / f'albums/{a["id"]}.html')
            print(f'ATTENTION : album protégé « {a["id"]} » non régénéré (mot de passe absent sur cette machine).')
        for src in [a['cover']] if a['id'] in FROZEN else [a['cover'], *a['photos']]:
            if not known(src):
                raise ValueError(f'Photo introuvable : {src}')
    public = public_photos(ALBUMS, page_photos())
    PRIVATE_SOURCES.update(src for a in ALBUMS if a.get('password_protected') and a['id'] not in FROZEN
                           for src in a['photos'] if src not in public)
    favicon_source = ROOT / 'images/favicon1.png'
    if favicon_source.is_file():
        with Image.open(favicon_source) as icon:
            for size, name in [(32, 'favicon-32.png'), (180, 'apple-touch-icon.png')]:
                ImageOps.contain(icon.convert('RGBA'), (size, size)).save(ROOT / 'images' / name, optimize=True)
    small_logo()
    home_og = social_image(PAGE_PHOTOS['accueil']['image_de_partage'], 'home-cover')
    print_references = build_universes(ALBUMS, picture, write, home_og, asset)

    mentions = (ROOT / 'templates/mentions.html').read_text(encoding='utf-8')
    for token, block in legal_blocks().items():
        mentions = mentions.replace(token, block)
    write('mentions.html', shell(mentions, 'Mentions légales & confidentialité | Thomas Soleil',
          'Informations sur l’éditeur, l’hébergement, les photographies et l’utilisation des données du formulaire de contact de Thomas Soleil.',
          'mentions.html', 'site', cover=home_og))

    dialog = lightbox_markup()
    for a in ALBUMS:
        if a['id'] in FROZEN:
            continue
        print(f'Album {a["id"]} : {len(a["photos"])} photos', flush=True)
        items = []
        for i, src in enumerate(a['photos']):
            alt = a.get('photo_alts', {}).get(src, PHOTO_DESCRIPTIONS.get(src, f'{a["title"]} — photographie {i + 1}'))
            viewer = asset(src, large=True)
            img = picture(src, alt, '../', loading='eager' if i < 3 else 'lazy')
            candidates = viewer['variants']
            largest = quote(candidates[-1][0], safe="/")
            viewer_srcset = ', '.join(f'../{quote(p, safe="/")} {w}w' for p, w in candidates)
            ratio = viewer['width'] / viewer['height']
            print_attribute = f' data-print-reference="{print_references[src]}"' if src in print_references else ''
            items.append(f'<li style="--photo-ratio:{ratio:.6f}"><a class="photo-link" href="../{e(largest)}" data-viewer-src="../{e(largest)}" data-viewer-srcset="{e(viewer_srcset)}"{print_attribute} aria-label="Agrandir : {e(alt)}">{img}</a></li>')
        path = f'albums/{a["id"]}.html'
        description = a['description']
        date_prefix = e(a['date']) + ' · ' if a.get('date') else ''
        context = f'<p class="gallery-description">{e(description)}</p><p class="gallery-meta">{date_prefix}{len(a["photos"])} photographies</p>'
        top_link = '<a class="back-to-top" href="#contenu" hidden>Retour en haut <span aria-hidden="true">↑</span></a>'
        og = social_image(a['cover'], a['id'])
        if a['category'] == 'Rugby':
            body = f'''<main id="contenu"><div class="frame"><header class="rugby-gallery-header"><a href="../rugby/index.html#reportages">← Les reportages rugby</a><h1>{e(a['title'].removeprefix('Rugby — '))}</h1><p class="gallery-description">{e(description)}</p></header><ul class="photo-grid" aria-label="Photographies du reportage">{''.join(items)}</ul><div class="gallery-end"><a href="../rugby/index.html#reportages">← Les reportages</a><a class="button outline" href="../rugby/contact.html">Demander un reportage sport ↗</a></div></div>{top_link}</main>{dialog}'''
            write(path, shell(body, a['title'] + ' | Thomas Soleil Rugby', description, path, 'rugby', '../', og, ('masonry.js', 'gallery.js')))
        elif a['category'] in ('Argentique', 'Autres regards'):
            gallery_label = 'Photographies individuelles' if a.get('presentation') == 'individual' else 'Photographies de la série'
            body = f'''<main id="contenu" class="frame art-gallery"><header class="art-gallery-header"><h1>{e(a['title'])}</h1>{context}</header><ul class="photo-grid" aria-label="{gallery_label}">{''.join(items)}</ul><div class="gallery-end"><a href="../regards/index.html">← Les projets personnels</a></div>{top_link}</main>{dialog}'''
            write(path, shell(body, a['title'] + ' | Thomas Soleil', description, path, 'regards', '../', og, ('masonry.js', 'gallery.js')))
        elif a['category'] in ('Mariage', 'Concerts'):
            universe = 'instants-de-vie' if a['category'] == 'Mariage' else 'concerts'
            contact_href = f'../{universe}/contact.html'
            return_href = f'../{universe}/index.html' + ('#reportages' if a['category'] == 'Concerts' else '')
            body = f'''<main id="contenu" class="frame"><header class="collection-gallery-header"><a href="{return_href}">← Les reportages</a><h1>{e(a['title'])}</h1>{context}</header><ul class="photo-grid" aria-label="Photographies du reportage">{''.join(items)}</ul><div class="gallery-end"><a href="{return_href}">← Les reportages</a><a href="{contact_href}">Contact ↗</a></div>{top_link}</main>{dialog}'''
            write(path, shell(body, a['title'] + ' | Thomas Soleil', description, path, universe, '../', og, ('masonry.js', 'gallery.js')))
        else:
            raise ValueError(f'Catégorie d’album inconnue : « {a["category"]} » ({a["id"]}). '
                             'Catégories possibles : Rugby, Mariage, Concerts, Argentique, Autres regards.')
    missing = (ROOT / 'templates/404.html').read_text(encoding='utf-8')
    write('404.html', shell(missing, 'Page introuvable | Thomas Soleil', 'Retrouvez les reportages de Thomas Soleil.',
                            '404.html', 'site', '/', home_og, noindex=True))
    for path, (target, label) in REDIRECTS.items():
        redirect(path, target, label)
    urls = ['', 'rugby/index.html', 'rugby/contact.html', 'rugby/tarifs.html', 'instants-de-vie/index.html', 'instants-de-vie/prestations.html', 'instants-de-vie/contact.html', 'concerts/index.html', 'concerts/contact.html', 'regards/index.html', 'regards/tirages.html', 'mentions.html'] + [f'albums/{a["id"]}.html' for a in ALBUMS if not a.get('password_protected')]
    dates = json.loads(SITEMAP_DATES_PATH.read_text(encoding='utf-8')) if SITEMAP_DATES_PATH.exists() else {}
    entries = []
    for url in urls:
        page = url or 'index.html'
        digest = hashlib.sha256((ROOT / page).read_bytes().replace(b'\r\n', b'\n')).hexdigest()[:16]
        if dates.get(page, {}).get('hash') != digest:
            dates[page] = {'hash': digest, 'date': date.today().isoformat()}
        entries.append(f'<url><loc>{public_url(page)}</loc><lastmod>{dates[page]["date"]}</lastmod></url>')
    listed = {url or 'index.html' for url in urls}
    SITEMAP_DATES_PATH.write_text(json.dumps({page: dates[page] for page in sorted(listed)}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(entries) + '\n</urlset>\n')
    write('robots.txt', 'User-agent: *\nAllow: /\nSitemap: ' + BASE + '/sitemap.xml\n')
    prune_optimized_images()
    MANIFEST_PATH.write_text(json.dumps({src: MANIFEST[src] for src in sorted(MANIFEST)}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'Terminé : {len(ALBUMS)} albums, {sum(len(a["photos"]) for a in ALBUMS)} photos.')


if __name__ == '__main__':
    build()
