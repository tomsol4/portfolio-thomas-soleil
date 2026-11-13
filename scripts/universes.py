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
<div class="portal-title"><h1 id="home-title">Thomas Soleil</h1><p>Photographe en Occitanie</p></div>
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
                              prefix, loading='lazy', sizes='(max-width: 760px) 200px, 360px' if universe == 'concerts' else '(max-width: 760px) 90vw, 45vw'))
    content = content.replace('<main id="contenu" class="frame personal-page">',
                              '<section class="personal-section" id="presentation" aria-labelledby="presentation-title"><div class="frame personal-page">', 1)
    content = content.replace('</main>', '</div></section>', 1)
    return content.replace('<h1>', '<h2 id="presentation-title">', 1).replace('</h1>', '</h2>', 1)


def build_concert_contact(write):
    contact = (ROOT / 'templates/contact.html').read_text(encoding='utf-8')
    contact = contact.replace('class="container"', 'class="frame contact-page"')
    contact = contact.replace('Racontez-moi votre projet.', 'Votre prochain concert.')
    contact = contact.replace('Sport, mariage, événement ou concert : quelques mots suffisent pour commencer.',
                              'Un concert, un chœur ou un événement musical : quelques mots suffisent pour commencer.')
    contact = contact.replace('<option value="concert">', '<option value="concert" selected>')
    contact = re.sub(r'<div class="form-group" id="wedding-offer-group">.*?</select></div>\s*', '', contact, count=1, flags=re.S)
    contact = contact.replace('href="mentions.html#confidentialite"', 'href="../mentions.html#confidentialite"')
    contact = contact.replace('Votre idée, vos envies, le déroulé de l’événement…',
                              'Le concert, le lieu, la date et les images dont vous avez besoin…')
    write('concerts/contact.html', shell(contact, 'Votre projet concert | Contacter Thomas Soleil',
          'Un concert, un chœur ou un événement musical ? Contactez Thomas Soleil, photographe entre Toulouse et Castres.',
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
    contact = contact.replace('<h2>Échangeons simplement.</h2>', '<h3>Échangeons simplement.</h3>', 1)
    contact = contact.replace('</main>', '</div></section>', 1)
    portal = portal.replace('{{CONTACT}}', contact)
    write('index.html', shell(portal, 'Thomas Soleil | Photographe en Occitanie — Toulouse et Castres',
          'Mariages et événements, sport, concerts et projets personnels : découvrez les univers de Thomas Soleil, photographe en Occitanie, à Toulouse et Castres.',
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
          'Reportages rugby au cœur du jeu. Découvrez les rencontres du Castres Olympique photographiées par Thomas Soleil et préparons votre projet sportif.',
          'rugby/index.html', 'rugby', '../', 'images/optimized/og-co_rct.jpg'))
    contact = (ROOT / 'templates/contact.html').read_text(encoding='utf-8')
    contact = contact.replace('Racontez-moi votre projet.', 'Votre prochain coup d’envoi.')
    contact = contact.replace('Sport, mariage, événement ou concert : quelques mots suffisent pour commencer.', 'Un match, un tournoi ou un projet pour votre club : quelques mots suffisent pour commencer.')
    contact = contact.replace('<option value="sport">', '<option value="sport" selected>')
    contact = re.sub(r'<div class="form-group" id="wedding-offer-group">.*?</select></div>\s*', '', contact, count=1, flags=re.S)
    contact = contact.replace('href="mentions.html#confidentialite"', 'href="../mentions.html#confidentialite"')
    contact = contact.replace('Votre idée, vos envies, le déroulé de l’événement…', 'Le match, le lieu, les accès au terrain et les images dont vous avez besoin…')
    write('rugby/contact.html', shell(contact, 'Votre projet rugby | Contacter Thomas Soleil',
          'Un reportage de match ou des images pour votre club ? Contactez Thomas Soleil, photographe de rugby entre Toulouse et Castres.',
          'rugby/contact.html', 'rugby', '../', 'images/optimized/og-co_rct.jpg', ('contact.js',)))
    about = (ROOT / 'templates/rugby-about.html').read_text(encoding='utf-8')
    about = about.replace('{{PORTRAIT}}', picture('images/portrait.jpg', 'Thomas Soleil, joueur de rugby et photographe', '../',
                         loading='eager', sizes='(max-width: 760px) 90vw, 45vw'))
    write('rugby/a-propos.html', shell(about, 'À propos | Thomas Soleil, photographe de rugby',
          'Joueur et photographe de rugby entre Toulouse et Castres : découvrez Thomas Soleil et son regard sur le terrain.',
          'rugby/a-propos.html', 'rugby', '../', 'images/optimized/og-co_mhr.jpg'))
    concerts = [a for a in albums if a['category'] == 'Concerts']
    entries = []
    for index, album in enumerate(concerts, 1):
        image = picture(album['cover'], album['title'], '../', loading='lazy',
                        sizes='(max-width: 760px) calc(100vw - 40px), (max-width: 1000px) 60vw, 40vw', large=True)
        year = escape(album.get('date', ''))
        entries.append(f'''<a class="collection-link concert-ticket" href="../albums/{album['id']}.html"><div class="concert-entry-meta"><span class="concert-ticket-stub-label" aria-hidden="true">Reportage</span><span class="concert-entry-number"><span class="sr-only">Reportage </span>{index:02d}</span><span>{year}</span><span class="concert-ticket-stub-brand" aria-hidden="true">Thomas Soleil</span></div><div class="concert-entry-content"><div class="collection-image">{image}{lock_badge(album)}</div><div class="collection-caption"><div><p class="concert-entry-kind">Concert &amp; chœur</p><h2>{escape(album['title'])}</h2><span class="concert-entry-open">Voir le reportage <span aria-hidden="true">↗</span></span></div></div></div></a>''')
    body = (ROOT / 'templates/concerts.html').read_text(encoding='utf-8')
    body = body.replace('{{CONCERT_HERO}}', picture(by_id['concertsinfonia']['cover'],
                        'Le chœur Sinfonia Garonna et les musiciens réunis autour de leur chef', '../',
                        loading='eager', sizes='(max-width: 760px) calc(100vw - 40px), (max-height: 650px) min(680px, 86vw), min(1100px, max(480px, calc((100svh - 347px)*1.5)), 86vw)', hero=True, large=True))
    body = body.replace('{{CONCERT_REPORTAGES}}', ''.join(entries))
    body = body.replace('{{PRESENTATION}}', inline_presentation('concerts', picture))
    write('concerts/index.html', shell(body, 'Photographe de concert à Toulouse & Castres | Thomas Soleil',
          'Concerts, chœurs et orchestres en images : les reportages de Thomas Soleil, photographe de concert à Toulouse et Castres.',
          'concerts/index.html', 'concerts', '../', 'images/optimized/og-concertsinfonia.jpg', ('theatre.js',)))
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
          'Séries et photographies individuelles de Thomas Soleil : argentique, paysages et projets personnels.',
          'regards/index.html', 'regards', '../', 'images/optimized/og-Argentique.jpg', ('regards.js', 'gallery.js')))
    for universe, album_id, title, description in [
        ('rugby', 'co_mhr', 'Tarifs sport & rugby | Thomas Soleil', 'Reportage de match, tournoi et vie de club : prestations sportives sur devis à Toulouse et Castres.'),
        ('concerts', 'concertsinfonia', 'Tarifs concerts | Thomas Soleil', 'Reportages de concerts, chœurs et événements musicaux : une couverture sur devis adaptée à votre scène.')]:
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
                                      sizes='(max-width: 760px) 90vw, 45vw', large=True))
        path = universe + '/tarifs.html'
        write(path, shell(content, title, description, path, universe, '../', 'images/optimized/og-' + album_id + '.jpg'))
    return print_references


LIFE_OFFERS = [('Reportage de mariage — cérémonie', 600), ('Reportage de mariage — cérémonie et cocktail', 850),
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
          'Photographies de mariage et d’événements à Toulouse et Castres. Découvrez les images et l’approche discrète de Thomas Soleil.',
          'instants-de-vie/index.html', 'instants-de-vie', '../', cover))
    for name, template, title, description in [
        ('a-propos', 'life-about', 'À propos | Thomas Soleil, mariage et événements', 'Le regard et le parcours de Thomas Soleil, photographe de mariage à Toulouse et Castres.'),
        ('prestations', 'life-services', 'Tarifs mariage, baptême & événements | Thomas Soleil', 'Mariage : 600 €, 850 € ou 1 000 €. Baptême : 250 €. Fiançailles : 300 €. Couple et famille : 100 € en tarif de lancement. Numérique inclus, argentique en option.')]:
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
    contact = contact.replace('Racontez-moi votre projet.', 'Parlons de votre histoire.')
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
    contact = contact.replace('Votre idée, vos envies, le déroulé de l’événement…', 'Votre histoire, le lieu, la date et les images qui vous tiennent à cœur…')
    write('instants-de-vie/contact.html', shell(contact, 'Votre histoire | Contacter Thomas Soleil',
          'Un mariage, un baptême ou une séance à deux ? Contactez Thomas Soleil, photographe à Toulouse et Castres.',
          'instants-de-vie/contact.html', 'instants-de-vie', '../', cover, ('contact.js',)))
