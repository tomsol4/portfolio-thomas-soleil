"""Independent visual universes, sharing the existing album data and viewer."""
from html import escape
from pathlib import Path
import re
from urllib.parse import quote
from site_metadata import structured_data, public_url, offers
from gallery_markup import lightbox_markup
from prints import build_prints
from album_access import lock_badge

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.tsoleil.fr'


def shell(body, title, description, path, universe, prefix='', cover='', scripts=(), schema_extra=()):
    rugby = universe == 'rugby'
    portal = universe == 'portal'
    artistic = universe == 'regards'
    brand_link = prefix + ('index.html#haut' if portal else universe + '/index.html')
    if rugby:
        links = [('index.html#haut', 'Tous les univers'), ('rugby/index.html#reportages', 'Reportages'),
                 ('rugby/index.html#presentation', 'À propos'), ('rugby/tarifs.html', 'Tarifs'),
                 ('rugby/contact.html', 'Contact')]
    elif universe == 'instants-de-vie':
        links = [('index.html#haut', 'Tous les univers'), ('instants-de-vie/index.html#reportages', 'Photos'),
                 ('instants-de-vie/index.html#presentation', 'À propos'), ('instants-de-vie/prestations.html', 'Tarifs'),
                 ('instants-de-vie/contact.html', 'Contact')]
    elif universe == 'concerts':
        links = [('index.html#haut', 'Tous les univers'), (universe + '/index.html#reportages', 'Reportages'),
                 ('concerts/index.html#presentation', 'À propos'),
                 ('concerts/tarifs.html', 'Tarifs'),
                 ('concerts/contact.html', 'Contact')]
    elif portal:
        links = [('#a-propos', 'À propos'), ('#contact', 'Contact')]
    else:
        links = [('index.html#a-propos', 'À propos'), ('index.html#contact', 'Contact')]
    nav = '\n'.join(f'<a href="{prefix}{href}"' + (' class="nav-contact"' if label == 'Contact' else '') +
                    (' aria-current="page"' if href == path else '') + f'>{label}</a>' for href, label in links)
    url = public_url(path)
    canonical = public_url(universe + '/index.html') if path.endswith('/a-propos.html') else url
    schema = structured_data(title, description, canonical, cover,
                             'CollectionPage' if path.startswith('albums/') else 'WebPage', schema_extra)
    tags = '\n'.join(f'<script src="{prefix}js/{script}" defer></script>' for script in ('main.js', *scripts))
    labels = {'rugby': 'Sport', 'instants-de-vie': 'Mariage &amp; événements', 'concerts': 'Concerts'}
    brand_name = '' if universe == 'instants-de-vie' else '<strong>Thomas Soleil</strong>'
    brand = (f'<img src="{prefix}images/logo.png" width="55" height="70" alt="">' if portal else
             f'<img class="brand-mark" src="{prefix}images/logo.png" width="56" height="56" alt="">'
             f'<span class="brand-copy">{brand_name}<span>{labels.get(universe, "Photographe")}</span></span>')
    navigation = f'''<nav class="site-nav" aria-label="Navigation principale">
<a class="logo" href="{brand_link}" aria-label="Thomas Soleil — Accueil">{brand}</a>
<button class="menu-toggle" type="button" aria-expanded="false" aria-controls="navigation" aria-label="Ouvrir le menu"><span aria-hidden="true"></span><span aria-hidden="true"></span></button>
<div class="nav-links" id="navigation">{nav}</div></nav>'''
    if path == 'concerts/index.html':
        drape = (ROOT / 'templates/theatre-nav.svg').read_text(encoding='utf-8')
        navigation = navigation.replace('<a class="logo"', drape + '\n<a class="logo"', 1)
    footer = f'''<footer class="site-footer"><div class="frame footer-inner"><p>© <span id="footer-year">2026</span> Thomas Soleil · Toulouse &amp; Castres</p><div class="footer-links"><a href="{prefix}index.html#haut">Tous les univers</a><a href="{prefix}mentions.html">Mentions légales &amp; confidentialité</a><a href="https://www.instagram.com/tomsol_photo/" target="_blank" rel="noopener noreferrer">Instagram<span class="sr-only"> (nouvel onglet)</span></a></div></div></footer>'''
    if artistic:
        destination = 'index.html#haut' if path == 'regards/index.html' else 'regards/index.html'
        label = 'Thomas Soleil — Accueil' if path == 'regards/index.html' else 'Thomas Soleil — Retour aux projets personnels'
        return_text = 'Les univers' if path == 'regards/index.html' else 'Les projets'
        navigation = f'<a class="art-return art-logo" href="{prefix}{destination}" aria-label="{label}"><img src="{prefix}images/logo.png" width="55" height="70" alt=""><span>{return_text}</span></a>'
        shop_href = '#demande' if path == 'regards/tirages.html' else prefix + 'regards/tirages.html'
        shop_label = 'Votre demande' if path == 'regards/tirages.html' else 'Tirages photo'
        navigation += f'<a class="art-shop-link" href="{shop_href}">{shop_label}<span aria-hidden="true">↗</span></a>'
        art_nav_class = 'art-navigation art-navigation-exhibition' if path == 'regards/index.html' else 'art-navigation'
        navigation = f'<nav class="{art_nav_class}" aria-label="Navigation principale">{navigation}</nav>'
        if path != 'regards/tirages.html':
            footer = ''
    if portal:
        # Bandeau de l'accueil : logo, nom du photographe et une seule icône vers Instagram.
        # « À propos » et « Contact » se trouvent en défilant, sous les portes.
        instagram = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" '
                     'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
                     'aria-hidden="true" focusable="false"><rect x="3" y="3" width="18" height="18" rx="5"/>'
                     '<circle cx="12" cy="12" r="4.2"/><circle cx="17.3" cy="6.7" r=".6" fill="currentColor"/></svg>')
        navigation = f'''<header class="site-nav" id="haut">
<a class="logo" href="{brand_link}" aria-label="Thomas Soleil — Accueil">{brand}</a>
<div class="portal-title"><h1 id="home-title">Thomas Soleil</h1><p>Photographe à Toulouse et Castres</p></div>
<div class="nav-links" id="navigation"><a class="portal-instagram" href="https://www.instagram.com/tomsol_photo/" target="_blank" rel="noopener noreferrer" aria-label="Instagram de Thomas Soleil (nouvel onglet)">{instagram}</a></div></header>'''
    shared_gallery = f'<link rel="stylesheet" href="{prefix}css/collections.css">' if universe in ('instants-de-vie', 'concerts', 'regards') else ''
    has_presentation = path.endswith('/a-propos.html') or path in ('rugby/index.html', 'instants-de-vie/index.html', 'concerts/index.html')
    presentation = f'<link rel="stylesheet" href="{prefix}css/presentation.css">' if has_presentation else ''
    tariffs = f'<link rel="stylesheet" href="{prefix}css/tarifs.css">' if path.endswith(('/tarifs.html', '/prestations.html')) else ''
    gallery_css = f'<link rel="stylesheet" href="{prefix}css/gallery.css">' if path.startswith('albums/') or artistic else ''
    contact_css = f'<link rel="stylesheet" href="{prefix}css/contact.css">' if path.endswith('contact.html') or portal or path == 'regards/tirages.html' else ''
    prints_css = f'<link rel="stylesheet" href="{prefix}css/prints.css">' if path == 'regards/tirages.html' else ''
    services_css = f'<link rel="stylesheet" href="{prefix}css/life-services.css">' if path == 'instants-de-vie/prestations.html' else ''
    theme = {'portal': '#000000', 'rugby': '#0b1622', 'instants-de-vie': '#f6f1e9', 'concerts': '#1b1013', 'regards': '#f5f4f1'}[universe]
    return f'''<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title><meta name="description" content="{escape(description, quote=True)}">
<meta name="author" content="Thomas Soleil"><meta name="theme-color" content="{theme}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/png" sizes="32x32" href="{prefix}images/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="{prefix}images/apple-touch-icon.png">
<link rel="preload" href="{prefix}fonts/CormorantGaramond-normal-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{prefix}fonts/cormorant-garamond.css">
<link rel="stylesheet" href="{prefix}fonts/montserrat.css">
<link rel="stylesheet" href="{prefix}css/universe-base.css">
<link rel="stylesheet" href="{prefix}css/navigation-icons.css">
{shared_gallery}
<link rel="stylesheet" href="{prefix}css/{universe}.css">
{presentation}
{tariffs}
{services_css}
{gallery_css}
{contact_css}
{prints_css}
<meta property="og:type" content="website"><meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="Thomas Soleil — Photographe">
<meta property="og:title" content="{escape(title, quote=True)}"><meta property="og:description" content="{escape(description, quote=True)}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{BASE}/{cover}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{escape(title, quote=True)}"><meta name="twitter:card" content="summary_large_image">
{schema}
{tags}</head><body class="{universe}-page{' home' if portal else ''}">
<a class="skip-link" href="#contenu">Aller au contenu</a>
{navigation}
{body}
{footer}
</body></html>'''


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


# Tarif horaire des concerts, en euros : repris sur la page Tarifs et dans sa description.
CONCERT_RATE = 60

# Photo d'ouverture de la page Concerts : elle remplit toute la scène derrière le rideau (recadrée à l'écran).
# Elle doit venir d'un album de concert public ; sa légende reprend le titre et l'année de cet album.
CONCERT_HERO = 'images/concert/repetition_bougie_sinfonia/2026_09_RepetBougie-85.jpg'

# Photos montrées sous les billets, rangée par rangée (photos entières, jamais recadrées).
# Seules les photos d'un album public sont affichées ; chacune ouvre son reportage.
CONCERT_MOSAIC = [
    ['images/concert/repetition_bougie_sinfonia/2026_09_RepetBougie-36.jpg',
     'images/concert/concertsinfonia/IMG_8656 (1) (1).jpg',
     'images/concert/concertsinfonia/IMG_2096.jpg'],
    ['images/concert/concertsinfonia/IMG_8581.jpg',
     'images/concert/repetition_bougie_sinfonia/2026_09_RepetBougie-96.jpg',
     'images/concert/repetition_bougie_sinfonia/2026_09_RepetBougie-28.jpg',
     'images/concert/concertsinfonia/IMG_2109.jpg']]


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
    return (f'<a class="collection-link concert-ticket" href="../albums/{album["id"]}.html">'
            '<div class="concert-entry-meta"><span class="concert-ticket-stub-label" aria-hidden="true">Reportage</span>'
            f'<span class="concert-entry-number"><span class="sr-only">Reportage </span>{index:02d}</span>'
            f'<span class="concert-entry-year">{escape(album.get("date", ""))}</span>'
            '<span class="concert-ticket-stub-brand" aria-hidden="true">Thomas Soleil</span></div>'
            f'<div class="concert-entry-content"><div class="collection-image">{image}{lock_badge(album)}</div>'
            f'<div class="collection-caption"><div><p class="concert-entry-kind">{escape(concert_kind(album))}</p>'
            f'<h3>{escape(album["title"])}</h3><dl class="concert-entry-facts">{details}</dl>'
            f'<span class="concert-entry-open">{action} <span aria-hidden="true">↗</span></span></div></div></div></a>')


def concert_mosaic(concerts, picture, asset):
    """Sélection de photos des reportages publics, en rangées justifiées."""
    source = {src: album for album in concerts if not album.get('password_protected') for src in album['photos']}
    rows = []
    for row in CONCERT_MOSAIC:
        cells = []
        for src in row:
            if src not in source:
                continue
            album = source[src]
            dimensions = asset(src)
            ratio = dimensions['width'] / dimensions['height']
            photo = picture(src, album['title'], '../', sizes=f'(max-width: 760px) 50vw, {round(ratio * 340)}px')
            cells.append(f'<a class="concert-mosaic-photo" style="--ratio:{ratio:.4f}" href="../albums/{album["id"]}.html">'
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
    hero_album = next((a for a in concerts if CONCERT_HERO in a['photos'] and not a.get('password_protected')), None)
    if hero_album is None:
        raise ValueError(f'Photo d’ouverture des concerts absente des albums publics : {CONCERT_HERO}')
    hero_dimensions = asset(CONCERT_HERO, large=True)
    hero_width_in_vh = 100 * hero_dimensions['width'] / hero_dimensions['height']
    body = (ROOT / 'templates/concerts.html').read_text(encoding='utf-8')
    # La photo couvre toute la scène (object-fit: cover) : sa largeur utile dépend aussi de la hauteur d'écran.
    body = body.replace('{{CONCERT_HERO}}', picture(CONCERT_HERO, hero_album['title'], '../', loading='eager',
                        sizes=f'max(100vw, {hero_width_in_vh:.2f}dvh)', hero=True, large=True))
    body = body.replace('{{CONCERT_HERO_CAPTION}}', escape(
        hero_album['title'] + (', ' + hero_album['date'] if hero_album.get('date') else '')))
    body = body.replace('{{CONCERT_SUMMARY}}', summary)
    body = body.replace('{{CONCERT_REPORTAGES}}', ''.join(
        concert_ticket(index, album, picture) for index, album in enumerate(concerts, 1)))
    body = body.replace('{{CONCERT_EXTRACTS}}', concert_mosaic(concerts, picture, asset))
    body = body.replace('{{PRESENTATION}}', inline_presentation('concerts', picture))
    write('concerts/index.html', shell(body, 'Photographe de concert à Toulouse & Castres | Thomas Soleil',
          'Chœurs et orchestres en concert et en répétition : les reportages de Thomas Soleil, photographe à Toulouse et Castres.',
          'concerts/index.html', 'concerts', '../', 'images/optimized/og-concertsinfonia.jpg', ('theatre.js',)))


def build_concert_contact(write):
    """Contact des concerts : le formulaire est un billet, les informations pratiques sont sur son talon."""
    contact = (ROOT / 'templates/contact.html').read_text(encoding='utf-8')
    contact = contact.replace('class="container"', 'class="frame contact-page concert-subpage"')
    contact = contact.replace('<header class="page-header"><p class="eyebrow">Contact</p>',
                              '<header class="concert-page-header"><p class="kicker">Contact</p>', 1)
    contact = contact.replace('<div class="contact-layout">', '<div class="contact-layout concert-booking">', 1)
    contact = contact.replace('<aside class="contact-aside">', '<aside class="contact-aside concert-booking-stub">', 1)
    contact = contact.replace('répondre.<a href=', 'répondre. <a href=', 1)
    contact = contact.replace('Me contacter.', 'Un concert à photographier ?')
    contact = contact.replace('Indiquez la date et le lieu, c’est ce qu’il me faut pour vous répondre.',
                              'Indiquez le concert ou la répétition, la date et le lieu.')
    contact = contact.replace('<option value="concert">', '<option value="concert" selected>')
    contact = re.sub(r'<div class="form-group" id="wedding-offer-group">.*?</select></div>\s*', '', contact, count=1, flags=re.S)
    contact = contact.replace('href="mentions.html#confidentialite"', 'href="../mentions.html#confidentialite"')
    contact = contact.replace('Votre projet, vos questions…',
                              'Le programme, la durée, les répétitions éventuelles…')
    write('concerts/contact.html', shell(contact, 'Votre projet concert | Contacter Thomas Soleil',
          'Un concert ou une répétition à photographier ? Écrivez à Thomas Soleil, photographe à Toulouse et Castres.',
          'concerts/contact.html', 'concerts', '../', 'images/optimized/og-concertsinfonia.jpg', ('contact.js',)))


def door_picture(asset, tall, wide, alt, first=False):
    """Photo d'une porte de l'accueil : cadrage horizontal sur téléphone, vertical au-delà."""
    def candidates(source):
        return ', '.join(f'{quote(path, safe="/")} {width}w' for path, width in source['variants'])
    portrait, landscape = asset(tall, large=True), asset(wide, large=True)
    # Les portes recadrent la photo (object-fit: cover) : la largeur utile dépend aussi de la hauteur d'écran.
    tall_ratio = 100 * portrait['width'] / portrait['height']
    wide_ratio = 25 * landscape['width'] / landscape['height']
    return (f'<picture><source media="(max-width: 760px)" srcset="{candidates(landscape)}" '
            f'sizes="max(100vw, {wide_ratio:.0f}vh)" width="{landscape["width"]}" height="{landscape["height"]}">'
            f'<img src="{quote(portrait["variants"][0][0], safe="/")}" srcset="{candidates(portrait)}" '
            f'sizes="(max-width: 1100px) max(50vw, {tall_ratio / 2:.0f}vh), max(42vw, {tall_ratio:.0f}vh)" '
            f'width="{portrait["width"]}" height="{portrait["height"]}" alt="{escape(alt, quote=True)}" '
            f'loading="eager" decoding="async"' + (' fetchpriority="high"' if first else '') + '></picture>')


def build_universes(albums, picture, write, home_cover, asset):
    rugby = [a for a in albums if a['category'] == 'Rugby']
    by_id = {a['id']: a for a in albums}
    portal = (ROOT / 'templates/portal.html').read_text(encoding='utf-8')
    # Chaque porte a deux cadrages : une photo verticale pour les panneaux hauts (ordinateur, tablette)
    # et une photo horizontale pour les bandeaux du téléphone. Toutes viennent d'albums publics.
    art = by_id['autres']['photos'][1]
    for index, (token, tall, wide, alt) in enumerate([
        ('LIFE_IMAGE', 'images/mariage/mariage_argentique (28).jpg', by_id['mariage']['cover'],
         'Les mariés, le jour de leur mariage'),
        ('SPORT_IMAGE', 'images/rugby/co_rct/26_06_CO-RCT-0753.jpg', by_id['co_mhr']['cover'],
         'Une action de match de rugby'),
        ('CONCERT_IMAGE', 'images/concert/concertsinfonia/IMG_2300 (1).jpg', by_id['concertsinfonia']['cover'],
         'Le chœur Sinfonia Garonna en concert'),
        ('ART_IMAGE', art, art, 'Une personne assise dans une église, en noir et blanc')]):
        portal = portal.replace('{{' + token + '}}', door_picture(asset, tall, wide, alt, first=index == 0))
    # « À propos » et « Contact » ne sont plus des pages : ce sont deux sections sous les portes.
    portal = portal.replace('{{PORTRAIT}}', picture('images/portrait.jpg', 'Thomas Soleil, photographe à Toulouse et Castres',
                            loading='lazy', sizes='(max-width: 760px) calc(100vw - 40px), 40vw'))
    contact = (ROOT / 'templates/contact.html').read_text(encoding='utf-8')
    contact = contact.replace('<main id="contenu" class="container">',
                              '<section class="portal-contact" id="contact" aria-labelledby="contact-title"><div class="frame">', 1)
    contact = contact.replace('<p class="eyebrow">', '<p class="portal-eyebrow">', 1)
    contact = contact.replace('<h1>', '<h2 id="contact-title">', 1).replace('</h1>', '</h2>', 1)
    contact = contact.replace('<h2>Pour commencer</h2>', '<h3>Pour commencer</h3>', 1)
    contact = contact.replace('</main>', '</div></section>', 1)
    portal = portal.replace('{{CONTACT}}', contact)
    write('index.html', shell(portal, 'Thomas Soleil | Photographe à Toulouse et Castres',
          'Thomas Soleil, photographe à Toulouse et Castres : mariages et événements, rugby, concerts et projets personnels.',
          'index.html', 'portal', cover=home_cover, scripts=('contact.js',)))
    cards = []
    for album in rugby:
        image = picture(album['cover'], album['title'], '../', sizes='(max-width: 760px) calc(100vw - 40px), 30vw', large=True)
        title = album['title'].removeprefix('Rugby — ')
        cards.append(f'''<a class="rugby-reportage" href="../albums/{album['id']}.html"><div class="rugby-reportage-image">{image}</div><div class="reportage-copy"><div><h3>{escape(title)}</h3></div><span class="reportage-arrow" aria-hidden="true">↗</span></div></a>''')
    body = (ROOT / 'templates/rugby.html').read_text(encoding='utf-8')
    hero_source = 'images/rugby/co_rct/26_06_CO-RCT-0796.jpg'
    hero_dimensions = asset(hero_source, large=True)
    hero_width_in_vh = 100 * hero_dimensions['width'] / hero_dimensions['height']
    body = body.replace('{{HERO_IMAGE}}', picture(hero_source, 'Une touche sous les projecteurs, Castres face à Toulon', '../',
                        loading='eager', sizes=f'max(100vw, {hero_width_in_vh:.2f}dvh)', hero=True))
    body = body.replace('{{HERO_DATE}}', escape(by_id['co_rct'].get('date', '')))
    body = body.replace('{{RUGBY_CARDS}}', ''.join(cards))
    body = body.replace('{{PRESENTATION}}', inline_presentation('rugby', picture))
    write('rugby/index.html', shell(body, 'Rugby & sport | Thomas Soleil, photographe à Toulouse et Castres',
          'Photos de rugby par Thomas Soleil, photographe né à Castres : matchs du Castres Olympique, photos pour les clubs, tournois et écoles de rugby.',
          'rugby/index.html', 'rugby', '../', 'images/optimized/og-co_rct.jpg'))
    contact = (ROOT / 'templates/contact.html').read_text(encoding='utf-8')
    contact = contact.replace('Me contacter.', 'Un match à couvrir ?')
    contact = contact.replace('Indiquez la date et le lieu, c’est ce qu’il me faut pour vous répondre.', 'Indiquez le match, le tournoi ou la saison, avec la date et le lieu.')
    contact = contact.replace('<option value="sport">', '<option value="sport" selected>')
    contact = re.sub(r'<div class="form-group" id="wedding-offer-group">.*?</select></div>\s*', '', contact, count=1, flags=re.S)
    contact = contact.replace('href="mentions.html#confidentialite"', 'href="../mentions.html#confidentialite"')
    contact = contact.replace('Votre projet, vos questions…', 'Le club, le niveau, les matchs concernés…')
    write('rugby/contact.html', shell(contact, 'Votre projet rugby | Contacter Thomas Soleil',
          'Un match, un tournoi ou des photos pour votre club ? Écrivez à Thomas Soleil, photographe de rugby à Toulouse et Castres.',
          'rugby/contact.html', 'rugby', '../', 'images/optimized/og-co_rct.jpg', ('contact.js',)))
    about = (ROOT / 'templates/rugby-about.html').read_text(encoding='utf-8')
    about = about.replace('{{PORTRAIT}}', picture('images/portrait.jpg', 'Thomas Soleil, photographe de rugby', '../',
                         loading='eager', sizes='(max-width: 760px) 90vw, 45vw'))
    write('rugby/a-propos.html', shell(about, 'À propos | Thomas Soleil, photographe de rugby',
          'Thomas Soleil, photographe de rugby à Toulouse et Castres.',
          'rugby/a-propos.html', 'rugby', '../', 'images/optimized/og-co_mhr.jpg'))
    build_concerts(albums, picture, write, asset)
    build_concert_contact(write)
    build_life_universe(albums, picture, write, asset)
    print_references = build_prints(albums, picture, write, shell)
    artistic_albums = [a for a in albums if a['category'] in ('Argentique', 'Autres regards')]
    series = [a for a in artistic_albums if a.get('presentation') != 'individual']
    individual_photos = [src for a in artistic_albums if a.get('presentation') == 'individual' for src in a['photos']]
    series_markup = []
    for index, album in enumerate(series):
        featured = index == 0
        title = album['title'].removeprefix('Argentique — ')
        image = picture(album['cover'], album['title'], '../',
                        loading='eager' if featured else 'lazy',
                        sizes='(max-width: 760px) calc(100vw - 40px), calc(100vw - 176px)', hero=featured, large=True)
        href = '../albums/' + album['id'] + '.html'
        series_markup.append(f'''<figure class="art-slide art-series-work{' art-feature' if featured else ''}" data-kind="series" data-title="{escape(title, quote=True)}" role="group" aria-roledescription="diapositive" aria-label="{index + 1} sur {len(series) + len(individual_photos)}"><a class="art-image-link art-series-link" href="{href}" aria-label="Voir la série : {escape(title, quote=True)}">{image}</a><figcaption><a href="{href}"><span class="art-series-title">{escape(title)}</span><span class="art-open">Voir la série <span aria-hidden="true">↗</span></span></a></figcaption></figure>''')
    photographs = []
    for index, src in enumerate(individual_photos, 1):
        image = picture(src, f'Photographie personnelle {index}', '../', loading='lazy',
                        sizes='(max-width: 760px) calc(100vw - 40px), calc(100vw - 176px)', large=True)
        candidates = asset(src, large=True)['variants']
        srcset = ', '.join(f'../{path} {width}w' for path, width in candidates)
        photographs.append(f'''<figure class="art-slide art-work" data-kind="photo" data-title="Photographie {index:02d}" role="group" aria-roledescription="diapositive" aria-label="{len(series) + index} sur {len(series) + len(individual_photos)}"><a class="art-image-link art-photo-link photo-link" href="../{candidates[-1][0]}" data-viewer-src="../{candidates[-1][0]}" data-viewer-srcset="{escape(srcset, quote=True)}" aria-label="Agrandir la photographie individuelle {index:02d}">{image}</a><figcaption><span class="art-series-title">Photographie {index:02d}</span></figcaption></figure>''')
    body = (ROOT / 'templates/regards.html').read_text(encoding='utf-8')
    body = body.replace('{{SLIDES}}', ''.join(series_markup + photographs))
    if individual_photos:
        body += lightbox_markup()
    write('regards/index.html', shell(body, 'Projets personnels | Thomas Soleil',
          'Les projets personnels de Thomas Soleil : séries argentiques, montagne et photos isolées.',
          'regards/index.html', 'regards', '../', 'images/optimized/og-Argentique.jpg', ('regards.js', 'gallery.js')))
    for universe, album_id, title, description in [
        ('rugby', 'co_mhr', 'Tarifs sport & rugby | Thomas Soleil', 'Photos de match, saison et tournois pour les clubs de rugby, sur devis. Galerie complète le lendemain du match. Toulouse et Castres.'),
        ('concerts', 'concertsinfonia', 'Tarifs concerts | Thomas Soleil', f'Photos de concert et de répétition : {CONCERT_RATE} € de l’heure, retouche comprise, sans minimum. Toulouse et Castres.')]:
        album = by_id[album_id]
        content = (ROOT / 'templates' / (universe + '-tarifs.html')).read_text(encoding='utf-8')
        if universe == 'rugby':
            for token, src, alt in [
                ('MATCH_PHOTO', 'images/rugby/co_rct/26_06_CO-RCT-1078.jpg', 'Action de jeu entre le Castres Olympique et le RC Toulon'),
                ('TOURNAMENT_PHOTO', 'images/rugby/TouchCO-5783.jpg', 'Vue du tournoi TouchCO sur les terrains du stade Pierre-Fabre'),
                ('CLUB_PHOTO', 'images/rugby/vie du club.jpg', 'Joueurs réunis autour d’un exercice de touche pendant un entraînement de rugby')]:
                content = content.replace('{{' + token + '}}', picture(src, alt, '../',
                                          sizes='(max-width: 760px) calc(100vw - 40px), 33vw'))
        else:
            content = content.replace('{{PHOTO}}', picture(album['cover'], album['title'], '../', loading='eager',
                                      sizes='(max-width: 760px) calc(100vw - 108px), (max-width: 1000px) 60vw, 420px', large=True))
            content = content.replace('{{RATE}}', str(CONCERT_RATE))
        path = universe + '/tarifs.html'
        write(path, shell(content, title, description, path, universe, '../', 'images/optimized/og-' + album_id + '.jpg'))
    return print_references


LIFE_OFFERS = [('Reportage de mariage — cérémonie', 500), ('Reportage de mariage — demi-journée', 750),
               ('Reportage de mariage — journée complète', 1000), ('Reportage de baptême', 250),
               ('Reportage de fiançailles', 300), ('Séance photo de couple', 100), ('Séance photo de famille', 100)]


# Sélection affichée sous la couverture d'un reportage, rangée par rangée (photos entières, jamais recadrées).
LIFE_MOSAICS = {'mariage': [
    ['images/mariage/mariage_argentique (22).jpg', 'images/mariage/mariage_argentique (21).jpg',
     'images/mariage/mariage_argentique (10).jpg',
     'images/mariage/mariage_argentique (5).jpg']]}


def build_life_universe(albums, picture, write, asset):
    wedding = next(a for a in albums if a['id'] == 'mariage')
    selected = [a for a in albums if a['category'] == 'Mariage']
    cover = 'images/optimized/og-mariage.jpg'
    body = (ROOT / 'templates/life-home.html').read_text(encoding='utf-8')
    source = 'images/mariage/mariage_argentique (35).jpg'
    alt = 'Les mariés près d’une voiture ancienne, dans un parc'
    if source not in wedding['photos']:
        source, alt = wedding['cover'], wedding['title']
    body = body.replace('{{WEDDING_HERO}}', picture(source, alt, '../', loading='eager',
                        sizes='max(100vw, 170svh)', hero=True, large=True))
    reportages = []
    for album in selected:
        href = f"../albums/{album['id']}.html"
        image = picture(album['cover'], album['title'], '../', sizes='(max-width: 760px) calc(100vw - 40px), min(860px, calc(100vw - 96px))', large=True)
        rows = []
        for row in LIFE_MOSAICS.get(album['id'], []):
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
        reportages.append(f'''<article class="life-story"><a class="collection-link" href="{href}"><h3 class="life-story-title">{escape(album.get('reportage_title', album['title']))}</h3><div class="collection-image">{image}{lock_badge(album)}</div></a>{mosaic}<p class="life-story-action"><a class="button outline life-story-open" href="{href}">{'Ouvrir l’album' if album.get('password_protected') else 'Voir le reportage'} <span aria-hidden="true">↗</span></a></p></article>''')
    body = body.replace('{{LIFE_REPORTAGES}}', ''.join(reportages))
    for token, src, alt in [
            ('OFFER_WEDDING', 'images/mariage/mariage_argentique (20).jpg', 'Les mariés à la sortie de la cérémonie'),
            ('OFFER_BAPTISM', 'images/bapteme/Aribastire-8443.jpg', 'Une médaille de baptême tenue entre les doigts'),
            ('OFFER_FAMILY', 'images/mariage/mariage_argentique (2).jpg', 'Un couple entouré d’enfants, dans un parc')]:
        body = body.replace('{{' + token + '}}', picture(src, alt, '../', sizes='(max-width: 860px) calc(100vw - 40px), 360px'))
    body = body.replace('{{PRESENTATION}}', inline_presentation('instants-de-vie', picture))
    write('instants-de-vie/index.html', shell(body, 'Mariage & événements | Thomas Soleil, Toulouse & Castres',
          'Photographe de mariage et de baptême à Toulouse et Castres. Mariage à partir de 500 €, photos livrées dans une galerie privée.',
          'instants-de-vie/index.html', 'instants-de-vie', '../', cover))
    for name, template, title, description in [
        ('a-propos', 'life-about', 'À propos | Thomas Soleil, mariage et événements', 'Thomas Soleil, photographe de mariage et d’événements à Toulouse et Castres.'),
        ('prestations', 'life-services', 'Tarifs mariage, baptême & événements | Thomas Soleil', 'Mariage : 500 €, 750 € ou 1 000 €. Baptême : 250 €. Fiançailles : 300 €. Couple et famille : 100 €. Photos retouchées, livrées dans une galerie privée.')]:
        content = (ROOT / 'templates' / (template + '.html')).read_text(encoding='utf-8')
        if template == 'life-services':
            content = content.replace('{{WEDDING_SERVICES_PHOTO}}', picture(
                'images/mariage/mariage_argentique (9).jpg', 'Les mariés pendant la cérémonie, entourés de leurs proches', '../',
                loading='eager', sizes='(max-width: 760px) calc(100vw - 40px), 46vw', large=True))
            for token, source, alt in [
                ('BAPTISM_CEREMONY', 'images/bapteme/Aribastire-8289.jpg', 'Une main bénit un bébé en tenue blanche pendant son baptême, en noir et blanc'),
                ('BAPTISM_DETAIL', 'images/bapteme/Aribastire-8443.jpg', 'Une médaille dorée tenue entre les doigts, près de la main d’un bébé')]:
                content = content.replace('{{' + token + '}}', picture(source, alt, '../', loading='lazy',
                                          sizes='(max-width: 900px) 60vw, 40vw'))
        if '{{PORTRAIT}}' in content:
            content = content.replace('{{PORTRAIT}}', picture('images/portrait.jpg', 'Thomas Soleil, photographe', '../',
                                      loading='eager', sizes='(max-width: 760px) 90vw, 45vw'))
        path = 'instants-de-vie/' + name + '.html'
        extra = offers(LIFE_OFFERS) if template == 'life-services' else ()
        write(path, shell(content, title, description, path, 'instants-de-vie', '../', cover, schema_extra=extra))
    contact = (ROOT / 'templates/contact.html').read_text(encoding='utf-8')
    contact = contact.replace('Me contacter.', 'Parlons de votre journée.')
    contact = contact.replace('class="container"', 'class="container life-contact-page"', 1)
    before_aside, _, aside_and_form = contact.partition('<aside class="contact-aside">')
    _, _, after_aside = aside_and_form.partition('</aside>')
    contact_photo = picture('images/mariage/mariage_argentique (5).jpg',
                            'Les mariés côte à côte pendant la cérémonie, en noir et blanc', '../',
                            loading='lazy', sizes='(max-width: 1000px) 300px, 344px', large=True)
    contact = before_aside + f'<div class="life-contact-photo">{contact_photo}</div>' + after_aside
    contact = contact.replace('<div class="form-group"><label for="project">',
                              '<div class="form-row life-project-row"><div class="form-group"><label for="project">', 1)
    contact = contact.replace('</select></div>\n<div class="form-row"><div class="form-group"><label for="date">',
                              '</select></div></div>\n<div class="form-row"><div class="form-group"><label for="date">', 1)
    contact = contact.replace('<option value="mariage">', '<option value="mariage" selected>')
    contact = contact.replace('<option value="portrait">Portrait</option><option value="sport">Sport</option><option value="concert">Concert</option>',
                              '<option value="bapteme">Baptême</option><option value="fiancailles">Fiançailles</option><option value="couple">Couple</option><option value="famille">Famille</option>')
    contact = contact.replace('href="mentions.html#confidentialite"', 'href="../mentions.html#confidentialite"')
    contact = contact.replace('Votre projet, vos questions…', 'Le lieu de la cérémonie, celui de la réception, vos questions…')
    write('instants-de-vie/contact.html', shell(contact, 'Votre histoire | Contacter Thomas Soleil',
          'Un mariage, un baptême ou une séance en famille ? Écrivez à Thomas Soleil, photographe à Toulouse et Castres.',
          'instants-de-vie/contact.html', 'instants-de-vie', '../', cover, ('contact.js',)))
