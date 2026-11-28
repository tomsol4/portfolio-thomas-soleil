"""Les univers du site (accueil, rugby, mariage & événements, concerts, projets personnels) et leur habillage commun.

Les textes sont dans templates/, les prix dans data/tarifs.json et les photos montrées hors des albums dans
data/photos-des-pages.json.
"""
from datetime import date
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import quote
from site_metadata import structured_data, public_url, offers, BASE, INSTAGRAM
from prints import build_prints, PRINTS_ONLINE
from album_access import lock_badge, locked_link, access_dialog
from contact_form import contact_aside, contact_form, contact_page, home_contact, LIFE_PROJECTS
from prices import PRICES, WEDDING_FROM, euros

ROOT = Path(__file__).resolve().parents[1]
PAGE_PHOTOS = json.loads((ROOT / 'data/photos-des-pages.json').read_text(encoding='utf-8'))
# Logo des pages : une petite copie de images/logo.png, fabriquée par scripts/build.py.
LOGO = 'images/logo-small.webp'

# Menu de chaque univers, après « Tous les univers ». « site » : les pages hors univers (mentions légales, page introuvable).
UNIVERSE_LINKS = {
    'rugby': [('rugby/index.html#reportages', 'Reportages'), ('rugby/index.html#presentation', 'À propos'),
              ('rugby/tarifs.html', 'Tarifs'), ('rugby/contact.html', 'Contact')],
    'instants-de-vie': [('instants-de-vie/index.html#reportages', 'Photos'), ('instants-de-vie/index.html#presentation', 'À propos'),
                        ('instants-de-vie/prestations.html', 'Tarifs'), ('instants-de-vie/contact.html', 'Contact')],
    'concerts': [('concerts/index.html#reportages', 'Reportages'), ('concerts/index.html#presentation', 'À propos'),
                 ('concerts/contact.html', 'Contact')],
    'site': [('index.html#a-propos', 'À propos'), ('index.html#contact', 'Contact')],
}
UNIVERSE_LABELS = {'rugby': 'Sport', 'instants-de-vie': 'Mariage &amp; événements', 'concerts': 'Concerts'}
THEME_COLORS = {'portal': '#000000', 'rugby': '#0b1622', 'instants-de-vie': '#f6f1e9', 'concerts': '#1b1013',
                'regards': '#f5f4f1', 'site': '#f3f0e9'}
INSTAGRAM_ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" '
                  'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
                  'aria-hidden="true" focusable="false"><rect x="3" y="3" width="18" height="18" rx="5"/>'
                  '<circle cx="12" cy="12" r="4.2"/><circle cx="17.3" cy="6.7" r=".6" fill="currentColor"/></svg>')


def standard_navigation(universe, path, prefix):
    """Menu d'un univers ou d'une page hors univers : logo, liens et bouton du menu sur téléphone."""
    links = [('index.html#haut', 'Tous les univers'), *UNIVERSE_LINKS[universe]]
    nav = '\n'.join(f'<a href="{prefix}{href}"' + (' class="nav-contact"' if label == 'Contact' else '') +
                    (' aria-current="page"' if href == path else '') + f'>{label}</a>' for href, label in links)
    home = prefix + ('index.html#haut' if universe == 'site' else universe + '/index.html')
    name = '' if universe == 'instants-de-vie' else '<strong>Thomas Soleil</strong>'
    brand = (f'<img class="brand-mark" src="{prefix}{LOGO}" width="56" height="56" alt="">'
             f'<span class="brand-copy">{name}<span>{UNIVERSE_LABELS.get(universe, "Photographe")}</span></span>')
    return f'''<nav class="site-nav" aria-label="Navigation principale">
<a class="logo" href="{home}" aria-label="Thomas Soleil — Accueil">{brand}</a>
<button class="menu-toggle" type="button" aria-expanded="false" aria-controls="navigation" aria-label="Ouvrir le menu"><span aria-hidden="true"></span><span aria-hidden="true"></span></button>
<div class="nav-links" id="navigation">{nav}</div></nav>'''


def portal_navigation():
    """Bandeau de l'accueil, posé sur le diaporama : logo, nom du photographe, « À propos », « Contact » et Instagram.
    Sur tablette et téléphone, seule l'icône Instagram reste ; les deux sections se trouvent en défilant."""
    return f'''<header class="site-nav" id="haut">
<a class="logo" href="index.html#haut" aria-label="Thomas Soleil — Accueil"><img src="{LOGO}" width="56" height="56" alt=""></a>
<div class="portal-title"><h1 id="home-title">Thomas Soleil</h1><p>Photographe à Toulouse et Castres</p></div>
<div class="nav-links" id="navigation"><a class="portal-link" href="#a-propos">À propos</a><a class="portal-link" href="#contact">Contact</a><a class="portal-instagram" href="{INSTAGRAM}" target="_blank" rel="noopener noreferrer" aria-label="Instagram de Thomas Soleil (nouvel onglet)">{INSTAGRAM_ICON}</a></div></header>'''


# Diapositive de chaque série dans le diaporama des projets personnels, notée en fabriquant ce diaporama (avant les
# pages d'albums) : le retour depuis une série rouvre le diaporama sur elle, pas sur la première.
SLIDE_ANCHORS = {}


def personal_projects_href(album_id=None):
    """Adresse du diaporama des projets personnels, ouvert sur la série qu'on quitte s'il la montre."""
    anchor = SLIDE_ANCHORS.get(album_id)
    return 'regards/index.html' + (f'#{anchor}' if anchor else '')


# Visite en 3D des projets personnels : une page à part (regards/galerie/), faite par
# scripts/musee_3d.py (dans Blender) ; le bouton n'apparaît que si elle existe.
GALLERY = 'regards/galerie/index.html'


def gallery_rooms():
    """Album → salle de la visite en 3D (d'après regards/galerie/plan.json) : depuis un album, on entre dans sa salle."""
    try:
        rooms = json.loads((ROOT / 'regards/galerie/plan.json').read_text(encoding='utf-8'))['salles']
    except (OSError, ValueError, KeyError):
        return {}
    return {room['lien'].rsplit('/', 1)[-1].removesuffix('.html'): name for name, room in rooms.items() if room.get('lien')}


def art_navigation(path, prefix):
    """Projets personnels : un retour (vers l'accueil ou vers les projets), le bouton de la visite en 3D
    et, si la page Tirages est en ligne, son lien."""
    exhibition, prints = path == 'regards/index.html', path == 'regards/tirages.html'
    album_id = path.removeprefix('albums/').removesuffix('.html') if path.startswith('albums/') else None
    destination = 'index.html#haut' if exhibition else personal_projects_href(album_id)
    label = 'Thomas Soleil — Accueil' if exhibition else 'Thomas Soleil — Retour aux projets personnels'
    css = 'art-navigation art-navigation-exhibition' if exhibition else 'art-navigation'
    shop_href = '#demande' if prints else prefix + 'regards/tirages.html'
    shop = (f'<a class="art-shop-link" href="{shop_href}">{"Votre demande" if prints else "Tirages photo"}'
            '<span aria-hidden="true">↗</span></a>') if PRINTS_ONLINE else ''
    room = gallery_rooms().get(album_id)
    visit = (f'<a class="art-visit-link" href="{prefix}{GALLERY}{"#" + room if room else ""}">Visite en 3D</a>'
             if (ROOT / GALLERY).is_file() and not prints else '')
    links = f'<div class="art-links">{visit}{shop}</div>' if visit or shop else ''
    return (f'<nav class="{css}" aria-label="Navigation principale"><a class="art-return art-logo" href="{prefix}{destination}" '
            f'aria-label="{label}"><img src="{prefix}{LOGO}" width="56" height="56" alt=""><span>{"Les univers" if exhibition else "Les projets"}</span></a>'
            f'{links}</nav>')


def footer(prefix):
    return (f'<footer class="site-footer"><div class="frame footer-inner"><p>© <span id="footer-year">{date.today().year}</span> '
            f'Thomas Soleil · Toulouse &amp; Castres</p><div class="footer-links"><a href="{prefix}index.html#haut">Tous les univers</a>'
            f'<a href="{prefix}mentions.html">Mentions légales &amp; confidentialité</a><a href="{INSTAGRAM}" target="_blank" '
            'rel="noopener noreferrer">Instagram<span class="sr-only"> (nouvel onglet)</span></a></div></div></footer>')


def stylesheets(universe, path, prefix, locked):
    """Feuilles de style de la page, dans l'ordre où elles s'appliquent."""
    names = ['universe-base']
    if universe in ('instants-de-vie', 'concerts', 'regards'):
        names.append('collections')
    names.append(universe)
    if path in ('rugby/index.html', 'instants-de-vie/index.html', 'concerts/index.html'):
        names.append('presentation')
    if path.endswith(('/tarifs.html', '/prestations.html')):
        names.append('tarifs')
    if path == 'instants-de-vie/prestations.html':
        names.append('life-services')
    if path.startswith('albums/') or (universe == 'regards' and path != 'regards/index.html'):
        names.append('gallery')
    if path.endswith('contact.html') or universe == 'portal' or path == 'regards/tirages.html':
        names.append('contact')
    if path == 'regards/tirages.html':
        names.append('prints')
    if locked:
        names.append('album-access')
    return '\n'.join(f'<link rel="stylesheet" href="{prefix}css/{name}.css">' for name in names)


def shell(body, title, description, path, universe, prefix='', cover='', scripts=(), schema_extra=(), noindex=False):
    """Page complète : en-tête, menu de l'univers, contenu et pied de page."""
    url = public_url(path)
    # Une liste qui mène à un album protégé demande son mot de passe au clic, avant d'ouvrir la page de l'album.
    locked = re.search(r' data-album-locked="([^"]*)"', body)
    if locked:
        scripts = (*scripts, 'album-lock.js')
    tags = '\n'.join(f'<script src="{prefix}js/{script}" defer></script>' for script in ('main.js', *scripts))
    if universe == 'portal':
        navigation = portal_navigation()
    elif universe == 'regards':
        navigation = art_navigation(path, prefix)
    else:
        navigation = standard_navigation(universe, path, prefix)
    # Les projets personnels n'ont un pied de page que sur la page des tirages.
    page_footer = '' if universe == 'regards' and path != 'regards/tirages.html' else footer(prefix)
    robots = '<meta name="robots" content="noindex, follow">\n' if noindex else ''
    schema = '' if noindex else structured_data(title, description, url, cover,
                                                'CollectionPage' if path.startswith('albums/') else 'WebPage', schema_extra)
    dialog = '\n' + access_dialog(locked[1], on_arrival=False) if locked else ''
    return f'''<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title><meta name="description" content="{escape(description, quote=True)}">
<meta name="author" content="Thomas Soleil"><meta name="theme-color" content="{THEME_COLORS[universe]}">
<meta name="referrer" content="strict-origin-when-cross-origin">
{robots}<link rel="canonical" href="{url}">
<link rel="icon" type="image/png" sizes="32x32" href="{prefix}images/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="{prefix}images/apple-touch-icon.png">
<link rel="preload" href="{prefix}fonts/CormorantGaramond-normal-latin.woff2" as="font" type="font/woff2" crossorigin>
{stylesheets(universe, path, prefix, locked)}
<meta property="og:type" content="website"><meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="Thomas Soleil — Photographe">
<meta property="og:title" content="{escape(title, quote=True)}"><meta property="og:description" content="{escape(description, quote=True)}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{BASE}/{cover}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{escape(title, quote=True)}"><meta name="twitter:card" content="summary_large_image">
{schema}
{tags}</head><body class="{universe}-page{' home' if universe == 'portal' else ''}">
<a class="skip-link" href="#contenu">Aller au contenu</a>
{navigation}
{body}{dialog}
{page_footer}
</body></html>'''


def photo_entry(entry):
    """Une photo de data/photos-des-pages.json : un chemin seul, ou {"photo": chemin, "texte": description}."""
    return (entry, None) if isinstance(entry, str) else (entry['photo'], entry.get('texte'))


def page_picture(picture, albums, entry, **options):
    """Image d'une photo choisie dans data/photos-des-pages.json, pour une page d'univers.

    Sans « texte », la photo est décrite par le titre de son album (une description de data/photo-descriptions.json
    reste prioritaire, comme pour toutes les photos)."""
    src, text = photo_entry(entry)
    album = next((a for a in albums if src == a['cover'] or src in a['photos']), None)
    return picture(src, text or (album['title'] if album else 'Photographie de Thomas Soleil'), '../', **options)


def inline_presentation(universe, picture):
    template = {'rugby': 'rugby-about.html', 'instants-de-vie': 'life-about.html', 'concerts': 'concerts-about.html'}[universe]
    prefix = '../'
    content = (ROOT / 'templates' / template).read_text(encoding='utf-8')
    content = content.replace('{{PORTRAIT}}', picture('images/portrait.jpg', 'Thomas Soleil, photographe à Toulouse et Castres',
                              prefix, loading='lazy', sizes='(max-width: 760px) min(70vw, 300px), 400px' if universe == 'concerts' else '(max-width: 760px) 90vw, 45vw'))
    content = content.replace('<main id="contenu" class="frame personal-page">',
                              '<section class="personal-section" id="presentation" aria-labelledby="presentation-title"><div class="frame personal-page">', 1)
    content = content.replace('</main>', '</div></section>', 1)
    return content.replace('<h1>', '<h2 id="presentation-title">', 1).replace('</h1>', '</h2>', 1)


def concert_kind(album):
    """Nature du reportage inscrite sur le billet : le champ « kind » de l'album, sinon déduite du titre."""
    return album.get('kind') or ('Répétition' if album['title'].startswith('Répétition') else 'Concert')


def concert_ticket(index, album, picture):
    """Billet d'un reportage : la photo, le titre, quelques repères et le talon numéroté."""
    image = picture(album['cover'], album['title'], '../', loading='lazy',
                    sizes='(max-width: 760px) calc(100vw - 108px), (max-width: 1000px) 46vw, min(40vw, 470px)', large=True)
    protected = album.get('password_protected')
    facts = [('Lieu', album.get('place', '')), ('Accès', 'Mot de passe' if protected else '')]
    details = ''.join(f'<div><dt>{label}</dt><dd>{escape(value)}</dd></div>' for label, value in facts if value)
    action = 'Ouvrir l’album' if protected else 'Voir le reportage'
    return (f'<a class="collection-link concert-ticket" href="../albums/{album["id"]}.html"{locked_link(album)}>'
            '<div class="concert-entry-meta"><span class="concert-ticket-stub-label" aria-hidden="true">Reportage</span>'
            f'<span class="concert-entry-number"><span class="sr-only">Reportage </span>{index:02d}</span>'
            f'<span class="concert-entry-year">{escape(album.get("date", ""))}</span>'
            '<span class="concert-ticket-stub-brand" aria-hidden="true">Thomas Soleil</span></div>'
            f'<div class="concert-entry-content"><div class="collection-image">{image}{lock_badge(album)}</div>'
            f'<div class="collection-caption"><div><p class="concert-entry-kind">{escape(concert_kind(album))}</p>'
            f'<h3>{escape(album["title"])}</h3><dl class="concert-entry-facts">{details}</dl>'
            f'<span class="concert-entry-open">{action} <span aria-hidden="true">↗</span></span></div></div></div></a>')


def concert_mosaic(concerts, picture, asset):
    """Photos des reportages, en rangées justifiées (photos entières, jamais recadrées) ; chacune ouvre son reportage.

    Une photo d'album protégé choisie ici devient publique ; son lien demande le mot de passe de l'album."""
    # Une photo présente dans un album public et dans un album protégé ouvre l'album public.
    source = {src: album for album in sorted(concerts, key=lambda a: not a.get('password_protected')) for src in album['photos']}
    rows = []
    for row in PAGE_PHOTOS['concerts']['mosaique']:
        cells = []
        for src in row:
            if src not in source:
                continue
            album = source[src]
            dimensions = asset(src)
            ratio = dimensions['width'] / dimensions['height']
            photo = picture(src, album['title'], '../', sizes=f'(max-width: 760px) 50vw, {round(ratio * 340)}px')
            cells.append(f'<a class="concert-mosaic-photo" style="--ratio:{ratio:.4f}" href="../albums/{album["id"]}.html"{locked_link(album)}>'
                         f'{photo}<span class="concert-mosaic-caption"><span class="sr-only">Voir le reportage : </span>'
                         f'{escape(album["title"])}</span></a>')
        if cells:
            rows.append('<div class="concert-mosaic-row">' + ''.join(cells) + '</div>')
    if not rows:
        return ''
    return ('<section class="concert-extracts frame" aria-labelledby="extracts-title">'
            '<div class="concert-section-heading"><h2 id="extracts-title">Quelques photos</h2></div>'
            f'<div class="concert-mosaic">{"".join(rows)}</div></section>')


def build_concerts(albums, picture, write, asset):
    concerts = [a for a in albums if a['category'] == 'Concerts']
    years = sorted({a['date'] for a in concerts if a.get('date')})
    summary = f'{len(concerts)} reportage' + ('s' if len(concerts) > 1 else '')
    if years:
        summary += ' · ' + (years[0] if len(years) == 1 else f'{years[0]} – {years[-1]}')
    # Photo d'ouverture : elle remplit toute la scène derrière le rideau (recadrée à l'écran).
    hero = PAGE_PHOTOS['concerts']['ouverture']
    # Un reportage public de préférence ; une photo d'album protégé est permise et devient publique.
    hero_album = next((a for a in sorted(concerts, key=lambda a: bool(a.get('password_protected'))) if hero in a['photos']), None)
    if hero_album is None:
        raise ValueError(f'La photo d’ouverture des concerts doit venir d’un reportage de concert : {hero}')
    hero_dimensions = asset(hero, large=True)
    hero_width_in_vh = 100 * hero_dimensions['width'] / hero_dimensions['height']
    body = (ROOT / 'templates/concerts.html').read_text(encoding='utf-8')
    # La photo couvre toute la scène (object-fit: cover) : sa largeur utile dépend aussi de la hauteur d'écran.
    body = body.replace('{{CONCERT_HERO}}', picture(hero, hero_album['title'], '../', loading='eager',
                        sizes=f'max(100vw, {hero_width_in_vh:.2f}dvh)', hero=True, large=True))
    body = body.replace('{{CONCERT_SUMMARY}}', summary)
    body = body.replace('{{CONCERT_REPORTAGES}}', ''.join(
        concert_ticket(index, album, picture) for index, album in enumerate(concerts, 1)))
    body = body.replace('{{CONCERT_EXTRACTS}}', concert_mosaic(concerts, picture, asset))
    body = body.replace('{{PRESENTATION}}', inline_presentation('concerts', picture))
    write('concerts/index.html', shell(body, 'Photographe de concert à Toulouse & Castres | Thomas Soleil',
          'Chœurs et orchestres en concert et en répétition : les reportages de Thomas Soleil, photographe à Toulouse et Castres.',
          'concerts/index.html', 'concerts', '../', 'images/optimized/og-concertsinfonia.jpg', ('theatre.js',)))


def build_concert_contact(write):
    """Contact des concerts : le formulaire est un billet, les informations pratiques sont sur son talon.

    Les concerts n'ont pas de page de tarifs : les questions fréquentes (templates/concerts-faq.html), sous le billet,
    répondent sans afficher de prix."""
    body = contact_page('Un concert à photographier ?',
                        contact_aside('Indiquez le concert ou la répétition, la date et le lieu.', css='contact-aside concert-booking-stub'),
                        contact_form('../', project='concert', message_hint='Le programme, la durée, les répétitions éventuelles…'),
                        main_class='frame contact-page concert-subpage', header_class='concert-page-header',
                        eyebrow_class='kicker', layout_class='contact-layout concert-booking',
                        after=(ROOT / 'templates/concerts-faq.html').read_text(encoding='utf-8'))
    write('concerts/contact.html', shell(body, 'Votre projet concert | Contacter Thomas Soleil',
          'Un concert ou une répétition à photographier ? Écrivez à Thomas Soleil, photographe à Toulouse et Castres.',
          'concerts/contact.html', 'concerts', '../', 'images/optimized/og-concertsinfonia.jpg', ('contact.js',)))


def home_picture(asset, wide, tall, alt, first=False):
    """Photo plein écran d'un univers de l'accueil : horizontale sur un écran large, verticale sur un écran en hauteur."""
    def candidates(source):
        return ', '.join(f'{quote(path, safe="/")} {width}w' for path, width in source['variants'])
    landscape, portrait = asset(wide, large=True), asset(tall, large=True)
    # La photo couvre tout l'écran (object-fit: cover) : la largeur utile dépend aussi de la hauteur d'écran.
    wide_ratio = 100 * landscape['width'] / landscape['height']
    tall_ratio = 100 * portrait['width'] / portrait['height']
    # Seule la première photo se charge avec la page ; les autres attendent d'être montrées (data-src, js/portal.js),
    # pour que le premier écran reste léger sur téléphone.
    lazy = '' if first else 'data-'
    # Écran en hauteur : 530 px annoncés, l'export de 1600 px suffit même aux écrans très denses (×3) ; jamais 2560 px sur un téléphone.
    return (f'<picture><source media="(orientation: portrait)" {lazy}srcset="{candidates(portrait)}" '
            f'sizes="min(max(100vw, {tall_ratio:.0f}vh), 530px)" width="{portrait["width"]}" height="{portrait["height"]}">'
            f'<img {lazy}src="{quote(landscape["variants"][0][0], safe="/")}" {lazy}srcset="{candidates(landscape)}" '
            f'sizes="max(100vw, {wide_ratio:.0f}vh)" width="{landscape["width"]}" height="{landscape["height"]}" '
            f'alt="{escape(alt, quote=True)}" decoding="async"' + (' fetchpriority="high"' if first else '') + '></picture>')


# Diaporama de l'accueil : jeton du modèle et rubrique de data/photos-des-pages.json, dans l'ordre des univers.
HOME_SLIDES = [('LIFE_IMAGE', 'mariage'), ('SPORT_IMAGE', 'rugby'), ('CONCERT_IMAGE', 'concerts'), ('ART_IMAGE', 'projets')]


def build_universes(albums, picture, write, home_cover, asset):
    rugby = [a for a in albums if a['category'] == 'Rugby']
    portal = (ROOT / 'templates/portal.html').read_text(encoding='utf-8')
    # Chaque univers a deux cadrages : une photo horizontale pour les écrans larges (ordinateur)
    # et une photo verticale pour les écrans en hauteur (téléphone).
    for index, (token, universe) in enumerate(HOME_SLIDES):
        slide = PAGE_PHOTOS['accueil'][universe]
        portal = portal.replace('{{' + token + '}}', home_picture(asset, slide['horizontale'], slide['verticale'], slide['texte'],
                                                                   first=index == 0))
    # « À propos » et « Contact » sont deux sections sous le diaporama.
    portal = portal.replace('{{PORTRAIT}}', picture('images/portrait.jpg', 'Thomas Soleil, photographe à Toulouse et Castres',
                            loading='lazy', sizes='(max-width: 760px) calc(100vw - 40px), 40vw'))
    portal = portal.replace('{{CONTACT}}', home_contact())
    write('index.html', shell(portal, 'Thomas Soleil | Photographe à Toulouse et Castres',
          'Thomas Soleil, photographe à Toulouse et Castres : mariages et événements, rugby, concerts et projets personnels.',
          'index.html', 'portal', cover=home_cover, scripts=('contact.js', 'portal.js')))

    cards = []
    for album in rugby:
        image = picture(album['cover'], album['title'], '../', sizes='(max-width: 760px) calc(100vw - 40px), 30vw', large=True)
        title = album['title'].removeprefix('Rugby — ')
        cards.append(f'''<a class="rugby-reportage" href="../albums/{album['id']}.html"><div class="rugby-reportage-image">{image}</div><div class="reportage-copy"><div><h3>{escape(title)}</h3></div><span class="reportage-arrow" aria-hidden="true">↗</span></div></a>''')
    body = (ROOT / 'templates/rugby.html').read_text(encoding='utf-8')
    hero, hero_text = photo_entry(PAGE_PHOTOS['rugby']['ouverture'])
    hero_album = next((a for a in rugby if hero == a['cover'] or hero in a['photos']), None)
    if hero_album is None:
        raise ValueError(f'La photo d’ouverture du rugby doit venir d’un reportage rugby : {hero}')
    hero_dimensions = asset(hero, large=True)
    hero_width_in_vh = 100 * hero_dimensions['width'] / hero_dimensions['height']
    body = body.replace('{{HERO_IMAGE}}', picture(hero, hero_text or hero_album['title'], '../',
                        loading='eager', sizes=f'max(100vw, {hero_width_in_vh:.2f}dvh)', hero=True))
    caption = hero_album['title'].removeprefix('Rugby — ') + (' · ' + hero_album['date'] if hero_album.get('date') else '')
    body = body.replace('{{HERO_CAPTION}}', escape(caption))
    body = body.replace('{{RUGBY_CARDS}}', ''.join(cards))
    body = body.replace('{{PRESENTATION}}', inline_presentation('rugby', picture))
    rugby_cover = f'images/optimized/og-{hero_album["id"]}.jpg'
    write('rugby/index.html', shell(body, 'Rugby & sport | Thomas Soleil, photographe à Toulouse et Castres',
          'Photos de rugby par Thomas Soleil, photographe né à Castres : matchs du Castres Olympique, photos pour les clubs, tournois et écoles de rugby.',
          'rugby/index.html', 'rugby', '../', rugby_cover))
    body = contact_page('Un match à couvrir ?', contact_aside('Indiquez le match, le tournoi ou la saison, avec la date et le lieu.'),
                        contact_form('../', project='sport', message_hint='Le club, le niveau, les matchs concernés…'))
    write('rugby/contact.html', shell(body, 'Votre projet rugby | Contacter Thomas Soleil',
          'Un match, un tournoi ou des photos pour votre club ? Écrivez à Thomas Soleil, photographe de rugby à Toulouse et Castres.',
          'rugby/contact.html', 'rugby', '../', rugby_cover, ('contact.js',)))
    content = (ROOT / 'templates/rugby-tarifs.html').read_text(encoding='utf-8')
    for token, key in [('MATCH_PHOTO', 'match'), ('TOURNAMENT_PHOTO', 'tournoi'), ('CLUB_PHOTO', 'saison')]:
        content = content.replace('{{' + token + '}}', page_picture(picture, albums, PAGE_PHOTOS['rugby']['tarifs'][key],
                                  sizes='(max-width: 760px) calc(100vw - 40px), 33vw'))
    write('rugby/tarifs.html', shell(content, 'Tarifs sport & rugby | Thomas Soleil',
          'Photos de match, saison et tournois pour les clubs de rugby, sur devis. Galerie complète le lendemain du match. Toulouse et Castres.',
          'rugby/tarifs.html', 'rugby', '../', 'images/optimized/og-co_mhr.jpg'))

    build_concerts(albums, picture, write, asset)
    build_concert_contact(write)

    build_life_universe(albums, picture, write, asset)
    print_references = build_prints(albums, picture, write, shell)
    artistic_albums = [a for a in albums if a['category'] in ('Argentique', 'Autres regards')]
    series = [a for a in artistic_albums if a.get('presentation') != 'individual']
    individual_photos = [src for a in artistic_albums if a.get('presentation') == 'individual' for src in a['photos']]
    total = len(series) + len(individual_photos)

    def slide_sizes(src):
        """Largeur réellement affichée : une photo en hauteur est limitée par la hauteur de l'écran, pas par sa largeur.

        Hauteurs retirées (en-tête, marges, titre), un peu arrondies vers le bas : le navigateur ne choisit jamais
        une version trop petite."""
        photo = asset(src, large=True)
        ratio = photo['width'] / photo['height']
        return (f'(max-width: 760px) min(100vw, calc((100vh - 160px) * {ratio:.3f})), '
                f'min(calc(100vw - 160px), calc((100vh - 175px) * {ratio:.3f}))')

    series_markup = []
    for index, album in enumerate(series):
        featured = index == 0
        title = album['title'].removeprefix('Argentique — ')
        image = picture(album['cover'], album['title'], '../',
                        loading='eager' if featured else 'lazy',
                        sizes=slide_sizes(album['cover']), hero=featured, large=True)
        href = '../albums/' + album['id'] + '.html'
        SLIDE_ANCHORS[album['id']] = anchor = 'serie-' + album['id']
        series_markup.append(f'''<figure class="art-slide art-series-work{' art-feature' if featured else ''}" id="{escape(anchor, quote=True)}" data-kind="series" data-title="{escape(title, quote=True)}" role="group" aria-roledescription="diapositive" aria-label="{index + 1} sur {total}"><a class="art-image-link art-series-link" href="{href}" aria-label="Voir la série : {escape(title, quote=True)}">{image}</a><figcaption><a href="{href}"><span class="art-series-title">{escape(title)}</span><span class="art-open">Voir la série <span aria-hidden="true">↗</span></span></a></figcaption></figure>''')
    # Photos seules : déjà montrées en grand, sans lien ni visionneuse ; leur ligne de titre reste vide pour que
    # toutes les photos gardent la même place (et, sur téléphone, les flèches leur place sous la photo).
    photographs = []
    for index, src in enumerate(individual_photos, 1):
        image = picture(src, f'Photographie personnelle {index}', '../', loading='lazy',
                        sizes=slide_sizes(src), large=True)
        photographs.append(f'''<figure class="art-slide art-work" id="photo-{index:02d}" data-kind="photo" role="group" aria-roledescription="diapositive" aria-label="{len(series) + index} sur {total}"><div class="art-image-link">{image}</div><figcaption></figcaption></figure>''')
    body = (ROOT / 'templates/regards.html').read_text(encoding='utf-8')
    body = body.replace('{{SLIDES}}', ''.join(series_markup + photographs))
    write('regards/index.html', shell(body, 'Projets personnels | Thomas Soleil',
          'Les projets personnels de Thomas Soleil : séries argentiques, montagne, monastère de La Garde, messe et photos isolées.',
          'regards/index.html', 'regards', '../', 'images/optimized/og-Argentique.jpg', ('regards.js',)))
    return print_references


# Prestations à prix affiché, décrites pour Google : (nom, prix dans data/tarifs.json).
LIFE_OFFERS = [('Reportage de mariage — cérémonie', 'mariage_ceremonie'), ('Reportage de mariage — demi-journée', 'mariage_demi_journee'),
               ('Reportage de mariage — journée complète', 'mariage_journee'), ('Reportage de baptême', 'bapteme'),
               ('Reportage de fiançailles', 'fiancailles'), ('Séance photo de couple', 'seance_couple'),
               ('Séance photo de famille', 'seance_famille')]


def services_description():
    """Description de la page des tarifs « Mariage & événements », reprise par Google."""
    couple, family = PRICES['seance_couple'], PRICES['seance_famille']
    sessions = f'Couple et famille : {euros(couple)}' if couple == family else f'Couple : {euros(couple)}. Famille : {euros(family)}'
    return (f'Mariage : {euros(PRICES["mariage_ceremonie"])}, {euros(PRICES["mariage_demi_journee"])} ou {euros(PRICES["mariage_journee"])}. '
            f'Baptême : {euros(PRICES["bapteme"])}. Fiançailles : {euros(PRICES["fiancailles"])}. {sessions}. '
            'Photos retouchées, livrées dans une galerie privée.')


def build_life_universe(albums, picture, write, asset):
    photos = PAGE_PHOTOS['mariage']
    wedding = next(a for a in albums if a['id'] == 'mariage')
    selected = [a for a in albums if a['category'] == 'Mariage']
    cover = 'images/optimized/og-mariage.jpg'
    body = (ROOT / 'templates/life-home.html').read_text(encoding='utf-8')
    source, alt = photo_entry(photos['ouverture'])
    if source not in wedding['photos']:
        source, alt = wedding['cover'], wedding['title']
    body = body.replace('{{WEDDING_HERO}}', picture(source, alt or wedding['title'], '../', loading='eager',
                        sizes='max(100vw, 170svh)', hero=True, large=True))
    reportages = []
    for album in selected:
        href = f"../albums/{album['id']}.html"
        image = picture(album['cover'], album['title'], '../', sizes='(max-width: 760px) calc(100vw - 40px), min(860px, calc(100vw - 96px))', large=True)
        # Sous la couverture, une sélection rangée par rangée (photos entières, jamais recadrées).
        rows = []
        for row in photos['mosaiques'].get(album['id'], []):
            if not all(src in album['photos'] for src in row):
                continue
            cells = []
            for src in row:
                dimensions = asset(src)
                ratio = dimensions['width'] / dimensions['height']
                photo = picture(src, album['title'], '../', sizes='(max-width: 700px) 50vw, 240px')
                cells.append(f'<div class="life-mosaic-photo" style="--ratio:{ratio:.4f}">{photo}</div>')
            rows.append('<div class="life-mosaic-row">' + ''.join(cells) + '</div>')
        mosaic = f'<div class="life-mosaic">{"".join(rows)}</div>' if rows else ''
        reportages.append(f'''<article class="life-story"><a class="collection-link" href="{href}"{locked_link(album)}><h3 class="life-story-title">{escape(album.get('reportage_title', album['title']))}</h3><div class="collection-image">{image}{lock_badge(album)}</div></a>{mosaic}<p class="life-story-action"><a class="button outline life-story-open" href="{href}"{locked_link(album)}>{'Ouvrir l’album' if album.get('password_protected') else 'Voir le reportage'} <span aria-hidden="true">↗</span></a></p></article>''')
    body = body.replace('{{LIFE_REPORTAGES}}', ''.join(reportages))
    for token, key in [('OFFER_WEDDING', 'mariage'), ('OFFER_BAPTISM', 'bapteme'), ('OFFER_FAMILY', 'couple_et_famille')]:
        body = body.replace('{{' + token + '}}', page_picture(picture, albums, photos['formules'][key],
                            sizes='(max-width: 860px) calc(100vw - 40px), 360px'))
    body = body.replace('{{PRESENTATION}}', inline_presentation('instants-de-vie', picture))
    write('instants-de-vie/index.html', shell(body, 'Mariage & événements | Thomas Soleil, Toulouse & Castres',
          f'Photographe de mariage et de baptême à Toulouse et Castres. Mariage à partir de {euros(WEDDING_FROM)}, photos livrées dans une galerie privée.',
          'instants-de-vie/index.html', 'instants-de-vie', '../', cover))

    content = (ROOT / 'templates/life-services.html').read_text(encoding='utf-8')
    content = content.replace('{{WEDDING_SERVICES_PHOTO}}', page_picture(picture, albums, photos['tarifs'], loading='eager',
                              sizes='(max-width: 760px) calc(100vw - 40px), 46vw', large=True))
    if len(photos['tarifs_bapteme']) != 2:
        raise ValueError('data/photos-des-pages.json : « tarifs_bapteme » doit contenir exactement deux photos.')
    for token, entry in zip(('BAPTISM_CEREMONY', 'BAPTISM_DETAIL'), photos['tarifs_bapteme']):
        content = content.replace('{{' + token + '}}', page_picture(picture, albums, entry, loading='lazy',
                                  sizes='(max-width: 900px) 60vw, 40vw'))
    write('instants-de-vie/prestations.html', shell(content, 'Tarifs mariage, baptême & événements | Thomas Soleil',
          services_description(), 'instants-de-vie/prestations.html', 'instants-de-vie', '../', cover,
          schema_extra=offers([(name, PRICES[key]) for name, key in LIFE_OFFERS])))

    contact_photo = page_picture(picture, albums, photos['contact'], loading='lazy', sizes='(max-width: 1000px) 300px, 344px', large=True)
    body = contact_page('Parlons de votre journée.', f'<div class="life-contact-photo">{contact_photo}</div>',
                        contact_form('../', project='mariage', projects=LIFE_PROJECTS, wedding_formula=True, project_row=True,
                                     message_hint='Le lieu de la cérémonie, celui de la réception, vos questions…'),
                        main_class='container life-contact-page')
    write('instants-de-vie/contact.html', shell(body, 'Votre histoire | Contacter Thomas Soleil',
          'Un mariage, un baptême ou une séance en famille ? Écrivez à Thomas Soleil, photographe à Toulouse et Castres.',
          'instants-de-vie/contact.html', 'instants-de-vie', '../', cover, ('contact.js',)))
