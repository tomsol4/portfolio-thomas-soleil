"""Independent visual universes, sharing the existing album data and viewer."""
from html import escape
from pathlib import Path
from site_metadata import structured_data
from gallery_markup import lightbox_markup
from prints import build_prints

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.tsoleil.fr'


def shell(body, title, description, path, universe, prefix='', cover='', scripts=()):
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
        links = [('rugby/index.html', 'Sport'), ('instants-de-vie/index.html', 'Mariage &amp; événements'),
                 ('concerts/index.html', 'Concerts'), ('regards/index.html', 'Projets personnels'),
                 ('a-propos.html', 'À propos'), ('contact.html', 'Contact')]
    else:
        links = [('a-propos.html', 'À propos'), ('contact.html', 'Contact')]
    nav = '\n'.join(f'<a href="{prefix}{href}"' + (' class="nav-contact"' if label == 'Contact' else '') +
                    (' aria-current="page"' if href == path else '') + f'>{label}</a>' for href, label in links)
    url = BASE + ('/' if path == 'index.html' else '/' + path)
    canonical = BASE + '/' + universe + '/index.html' if path.endswith('/a-propos.html') else url
    schema = structured_data(title, description, canonical, cover,
                             'CollectionPage' if path.startswith('albums/') else 'WebPage')
    tags = '\n'.join(f'<script src="{prefix}js/{script}" defer></script>' for script in ('main.js', *scripts))
    labels = {'rugby': 'Sport', 'instants-de-vie': 'Mariage &amp; événements', 'concerts': 'Concerts'}
    brand = (f'<img src="{prefix}images/logo.png" width="55" height="70" alt="">' if portal else
             f'<img class="brand-mark" src="{prefix}images/logo.png" width="56" height="56" alt="">'
             f'<span class="brand-copy"><strong>Thomas Soleil</strong><span>{labels.get(universe, "Photographe")}</span></span>')
    navigation = f'''<nav class="site-nav" aria-label="Navigation principale">
<a class="logo" href="{brand_link}" aria-label="Thomas Soleil — Accueil">{brand}</a>
<button class="menu-toggle" type="button" aria-expanded="false" aria-controls="navigation" aria-label="Ouvrir le menu"><span aria-hidden="true"></span><span aria-hidden="true"></span></button>
<div class="nav-links" id="navigation">{nav}</div></nav>'''
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
        navigation = navigation.replace('<span aria-hidden="true"></span><span aria-hidden="true"></span></button>', '<span aria-hidden="true"></span><span aria-hidden="true"></span><span aria-hidden="true"></span></button>')
    shared_gallery = f'<link rel="stylesheet" href="{prefix}css/collections.css">' if universe in ('instants-de-vie', 'concerts', 'regards') else ''
    has_presentation = path.endswith('/a-propos.html') or path in ('rugby/index.html', 'instants-de-vie/index.html', 'concerts/index.html')
    presentation = f'<link rel="stylesheet" href="{prefix}css/presentation.css">' if has_presentation else ''
    tariffs = f'<link rel="stylesheet" href="{prefix}css/tarifs.css">' if path.endswith(('/tarifs.html', '/prestations.html')) else ''
    gallery_css = f'<link rel="stylesheet" href="{prefix}css/gallery.css">' if path.startswith('albums/') or artistic else ''
    contact_css = f'<link rel="stylesheet" href="{prefix}css/contact.css">' if path.endswith('contact.html') or path == 'regards/tirages.html' else ''
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
<link rel="preload" href="{prefix}fonts/Rosehot.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{prefix}fonts/montserrat.css">
<link rel="stylesheet" href="{prefix}css/universe-base.css">
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
                              prefix, loading='lazy', sizes='(max-width: 760px) 90vw, 45vw'))
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
    contact = contact.replace('href="mentions.html#confidentialite"', 'href="../mentions.html#confidentialite"')
    contact = contact.replace('Votre idée, vos envies, le déroulé de l’événement…',
                              'Le concert, le lieu, la date et les images dont vous avez besoin…')
    write('concerts/contact.html', shell(contact, 'Votre projet concert | Contacter Thomas Soleil',
          'Un concert, un chœur ou un événement musical ? Contactez Thomas Soleil, photographe entre Toulouse et Castres.',
          'concerts/contact.html', 'concerts', '../', 'images/optimized/og-concertsinfonia.jpg', ('contact.js',)))


def build_universes(albums, picture, write, home_cover, asset):
    rugby = [a for a in albums if a['category'] == 'Rugby']
    by_id = {a['id']: a for a in albums}
    portal = (ROOT / 'templates/portal.html').read_text(encoding='utf-8')
    for token, src, alt in [
        ('SPORT_IMAGE', by_id['co_mhr']['cover'], 'Deux joueurs au contact, Castres face à Montpellier'),
        ('LIFE_IMAGE', by_id['mariage']['cover'], 'Les mariés à la sortie de la cérémonie'),
        ('CONCERT_IMAGE', by_id['concertsinfonia']['cover'], 'Le chœur Sinfonia Garonna en concert'),
        ('ART_IMAGE', by_id['autres']['photos'][1], 'Une personne assise dans une église, en noir et blanc')]:
        sizes = '(max-width: 760px) calc(100vw - 40px), (max-width: 1100px) 45vw, 25vw'
        if token in ('SPORT_IMAGE', 'LIFE_IMAGE', 'CONCERT_IMAGE', 'ART_IMAGE'):
            # Cover crops fill the tile's height, so the required image width exceeds the tile width.
            source = asset(src, large=True)
            ratio = source['width'] / source['height']
            sizes = (f'(max-width: 480px) max(calc(100vw - 40px), {round(360 * ratio)}px), '
                     f'(max-width: 760px) max(50vw, {round(300 * ratio)}px), '
                     f'(max-width: 1100px) max(50vw, {round(420 * ratio)}px), '
                     f'max(25vw, {round(460 * ratio)}px)')
        image = picture(src, alt, loading='lazy', sizes=sizes, large=True)
        portal = portal.replace('{{' + token + '}}', image)
    write('index.html', shell(portal, 'Thomas Soleil | Photographe à Toulouse et Castres',
          'Sport, mariage et événements, concerts et projets personnels : les univers de Thomas Soleil, photographe à Toulouse et Castres.',
          'index.html', 'portal', cover=home_cover))
    cards = []
    for album in rugby:
        image = picture(album['cover'], album['title'], '../', sizes='(max-width: 760px) calc(100vw - 40px), 30vw', large=True)
        title = album['title'].removeprefix('Rugby — ')
        cards.append(f'''<a class="rugby-reportage" href="../albums/{album['id']}.html"><div class="rugby-reportage-image">{image}</div><div class="reportage-copy"><div><h3>{escape(title)}</h3></div><span class="reportage-arrow" aria-hidden="true">↗</span></div></a>''')
    body = (ROOT / 'templates/rugby.html').read_text(encoding='utf-8')
    body = body.replace('{{HERO_IMAGE}}', picture(by_id['co_rct']['cover'], 'Une touche sous les projecteurs, Castres face à Toulon', '../',
                        loading='eager', sizes='(max-width: 1280px) 100vw, 1280px', hero=True))
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
        entries.append(f'''<a class="collection-link" href="../albums/{album['id']}.html"><div class="concert-entry-meta"><span>Reportage {index:02d}</span><span>{year}</span></div><div class="concert-entry-content"><div class="collection-image">{image}</div><div class="collection-caption"><h2>{escape(album['title'])}</h2><span aria-hidden="true">↗</span></div></div></a>''')
    body = (ROOT / 'templates/concerts.html').read_text(encoding='utf-8')
    body = body.replace('{{CONCERT_HERO}}', picture(by_id['noel']['cover'],
                        'Le Chœur Unum réuni dans une église pour son concert de Noël', '../',
                        loading='eager', sizes='(max-width: 760px) calc(100vw - 40px), (max-width: 1280px) 55vw, 680px', hero=True, large=True))
    body = body.replace('{{CONCERT_REPORTAGES}}', ''.join(entries))
    body = body.replace('{{PRESENTATION}}', inline_presentation('concerts', picture))
    write('concerts/index.html', shell(body, 'En scène. | Concerts — Thomas Soleil',
          'Concerts, chœurs et musique en images. Les reportages de Thomas Soleil, photographe à Toulouse et Castres.',
          'concerts/index.html', 'concerts', '../', 'images/optimized/og-concertsinfonia.jpg'))
    build_concert_contact(write)
    build_life_universe(albums, picture, write)
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
        photographs.append(f'''<figure class="art-slide art-work" data-kind="photo" data-title="Photographie {index:02d}" role="group" aria-roledescription="diapositive" aria-label="{len(series) + index} sur {len(series) + len(individual_photos)}"><a class="art-image-link art-photo-link photo-link" href="../{escape(src, quote=True)}" data-viewer-src="../{candidates[-1][0]}" data-viewer-srcset="{escape(srcset, quote=True)}" aria-label="Agrandir la photographie individuelle {index:02d}">{image}</a><figcaption><span class="art-series-title">Photographie {index:02d}</span></figcaption></figure>''')
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
        content = content.replace('{{PHOTO}}', picture(album['cover'], album['title'], '../', loading='eager',
                                  sizes='(max-width: 760px) 90vw, 45vw', large=universe == 'concerts'))
        path = universe + '/tarifs.html'
        write(path, shell(content, title, description, path, universe, '../', 'images/optimized/og-' + album_id + '.jpg'))
    return print_references


def build_life_universe(albums, picture, write):
    wedding = next(a for a in albums if a['id'] == 'mariage')
    selected = [a for a in albums if a['category'] == 'Mariage']
    cover = 'images/optimized/og-mariage.jpg'
    body = (ROOT / 'templates/life-home.html').read_text(encoding='utf-8')
    for token, src, alt in [
        ('WEDDING_HERO', 'images/mariage/n (13).jpg', 'Les mariés près d’une voiture ancienne, dans un parc'),
        ('WEDDING_DETAIL', 'images/mariage/n (7).jpg', 'Le bouquet et les détails de la robe de la mariée'),
        ('WEDDING_MOMENT', 'images/mariage/mariage19NB.jpg', 'Vue de la cérémonie de mariage dans une église, avec l’autel et les invités, en noir et blanc')]:
        # Home selections must belong to the explicitly published reportage.
        source = src if src in wedding['photos'] else wedding['cover']
        if source != src:
            alt = wedding['title']
        hero = token == 'WEDDING_HERO'
        sizes = ('(max-width: 760px) calc(100vw - 40px), (max-width: 1000px) calc(100vw - 56px), min(calc(100vw - 96px), 1220px)' if hero else
                 '(max-width: 760px) calc(100vw - 40px), 35vw' if token == 'WEDDING_DETAIL' else
                 '(max-width: 760px) calc(100vw - 40px), 55vw')
        body = body.replace('{{' + token + '}}', picture(source, alt, '../', loading='eager' if hero else 'lazy',
                            sizes=sizes, hero=hero, large=True))
    reportages = []
    for album in selected:
        image = picture(album['cover'], album['title'], '../', sizes='(max-width: 760px) calc(100vw - 40px), 55vw', large=True)
        reportages.append(f'''<a class="collection-link" href="../albums/{album['id']}.html"><div class="collection-image">{image}</div><div class="collection-caption"><p class="kicker">Quelques instants</p><h3>Photographies de mariage.</h3><span class="life-story-open">Voir les photographies <span aria-hidden="true">↗</span></span></div></a>''')
    body = body.replace('{{LIFE_REPORTAGES}}', ''.join(reportages))
    body = body.replace('{{PRESENTATION}}', inline_presentation('instants-de-vie', picture))
    write('instants-de-vie/index.html', shell(body, 'Mariage & événements | Thomas Soleil, Toulouse & Castres',
          'Photographies de mariage et d’événements à Toulouse et Castres. Découvrez les images et l’approche discrète de Thomas Soleil.',
          'instants-de-vie/index.html', 'instants-de-vie', '../', cover))
    for name, template, title, description in [
        ('a-propos', 'life-about', 'À propos | Thomas Soleil, mariage et événements', 'Le regard et le parcours de Thomas Soleil, photographe de mariage à Toulouse et Castres.'),
        ('prestations', 'life-services', 'Tarifs mariage, baptême & événements | Thomas Soleil', 'Comparez les trois formules mariage : Cérémonie dès 600 €, Cérémonie et cocktail, Reportage complet. Baptême, couple, famille et autres événements sur devis.')]:
        content = (ROOT / 'templates' / (template + '.html')).read_text(encoding='utf-8')
        if template == 'life-services':
            for token, source, alt in [
                ('BAPTISM_CEREMONY', 'images/bapteme/Aribastire-8289.jpg', 'Une main bénit un bébé en tenue blanche pendant son baptême, en noir et blanc'),
                ('BAPTISM_DETAIL', 'images/bapteme/Aribastire-8443.jpg', 'Une médaille dorée tenue entre les doigts, près de la main d’un bébé')]:
                content = content.replace('{{' + token + '}}', picture(source, alt, '../', loading='lazy',
                                          sizes='(max-width: 900px) 60vw, 40vw'))
        if '{{PORTRAIT}}' in content:
            content = content.replace('{{PORTRAIT}}', picture('images/portrait.jpg', 'Thomas Soleil, photographe', '../',
                                      loading='eager', sizes='(max-width: 760px) 90vw, 45vw'))
        path = 'instants-de-vie/' + name + '.html'
        write(path, shell(content, title, description, path, 'instants-de-vie', '../', cover))
    contact = (ROOT / 'templates/contact.html').read_text(encoding='utf-8')
    contact = contact.replace('Racontez-moi votre projet.', 'Parlons de votre histoire.')
    contact = contact.replace('Sport, mariage, événement ou concert : quelques mots suffisent pour commencer.',
                              'Mariage, événement, couple ou famille : racontez-moi le moment que vous souhaitez photographier.')
    contact = contact.replace('<option value="mariage">', '<option value="mariage" selected>')
    contact = contact.replace('<option value="portrait">Portrait</option><option value="sport">Sport</option><option value="concert">Concert</option>',
                              '<option value="bapteme">Baptême</option><option value="couple">Couple</option><option value="famille">Famille</option>')
    contact = contact.replace('href="mentions.html#confidentialite"', 'href="../mentions.html#confidentialite"')
    contact = contact.replace('Votre idée, vos envies, le déroulé de l’événement…', 'Votre histoire, le lieu, la date et les images qui vous tiennent à cœur…')
    write('instants-de-vie/contact.html', shell(contact, 'Votre histoire | Contacter Thomas Soleil',
          'Un mariage, un baptême ou une séance à deux ? Contactez Thomas Soleil, photographe à Toulouse et Castres.',
          'instants-de-vie/contact.html', 'instants-de-vie', '../', cover, ('contact.js',)))
