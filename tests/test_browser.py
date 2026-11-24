"""Le site dans un vrai navigateur : pages, menus, diaporamas, albums, visionneuse et formulaire.

Ces tests vérifient que le site marche (liens, gestes, clavier, formulaire, lisibilité, poids), pas son apparence :
changer une couleur, une police, une photo ou une mise en page ne doit pas obliger à les réécrire.
Chaque test ouvre un navigateur neuf. Les envois du formulaire sont interceptés : aucun message n'est envoyé.
"""
import hashlib
import io
import json
import os
import re
import unittest
from pathlib import Path

import support
from support import ROOT, OUT, CHROME, expect, offline, watch_errors, unlock_album, check_masonry, contrast_ratio
from PIL import Image
from playwright.sync_api import sync_playwright
from album_list import load_albums
from build import variant_key
from site_metadata import photo_descriptions

PAGES = ['index.html', 'rugby/index.html', 'rugby/contact.html', 'rugby/tarifs.html', 'instants-de-vie/index.html',
         'instants-de-vie/prestations.html', 'instants-de-vie/contact.html', 'concerts/index.html',
         'concerts/contact.html', 'regards/index.html', 'regards/tirages.html', 'mentions.html', '404.html']
WIDTHS = [320, 390, 768, 1440]
ENDPOINT = 'https://formspree.io/f/xblwgnop'
CORS = {'Access-Control-Allow-Origin': '*'}
PHOTOS_TO_LOAD = '.home-slide.is-active img, .life-hero-image img, .life-stories img, #presentation img, .concert-reportages img'


def wait_until_loaded(page, photo):
    page.wait_for_function('(image) => image.complete && image.naturalWidth > 0', arg=photo.element_handle())


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._site = support.local_site()
        cls.base = cls._site.__enter__()
        cls._playwright = sync_playwright().start()
        cls.browser = cls._playwright.chromium.launch(executable_path=CHROME, headless=True)
        cls.albums = load_albums()
        cls.rugby = next(a for a in cls.albums if a['category'] == 'Rugby')
        cls.rugby_page = f'albums/{cls.rugby["id"]}.html'
        cls.rugby_count = len(cls.rugby['photos'])
        portrait = ROOT / 'images/portrait.jpg'
        manifest = json.loads((ROOT / 'data/image-manifest.json').read_text(encoding='utf-8'))
        cls.portrait_digest = (hashlib.sha256(portrait.read_bytes()).hexdigest()[:12]
                               if portrait.is_file() else manifest['images/portrait.jpg']['digest'])
        cls.art_albums = [a for a in cls.albums if a['category'] in ('Argentique', 'Autres regards') and a.get('presentation') != 'individual']
        cls.individual_photos = [src for a in cls.albums if a.get('presentation') == 'individual' for src in a['photos']]
        cls.art_count = len(cls.art_albums) + len(cls.individual_photos)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._playwright.stop()
        cls._site.__exit__(None, None, None)

    def setUp(self):
        self.errors = []
        self.context = offline(self.browser.new_context(reduced_motion='reduce'))
        self.page = self.context.new_page()
        watch_errors(self.page, self.base, self.errors)

    def tearDown(self):
        self.context.close()
        self.assertFalse(self.errors, 'Erreurs dans le navigateur :\n' + '\n'.join(self.errors))

    def open(self, path, width, height=900, **options):
        self.page.set_viewport_size({'width': width, 'height': height})
        self.page.goto(f'{self.base}/{path}', **options)
        return self.page

    # Mise en page

    def test_pages_fit_every_screen(self):
        """Aucune page ne déborde en largeur et chacune a un seul titre principal ; les albums s'ouvrent en mosaïque."""
        page = self.page
        for width in WIDTHS:
            for path in PAGES + [f'albums/{a["id"]}.html' for a in self.albums]:
                with self.subTest(width=width, path=path):
                    self.open(path, width, wait_until='networkidle')
                    overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                    if overflow:
                        print(page.evaluate('Array.from(document.querySelectorAll("body *")).filter(el => { const b=el.getBoundingClientRect(); return b.width && b.right > innerWidth + 1; }).slice(0,12).map(el => ({tag:el.tagName,css:el.className,width:el.getBoundingClientRect().width,right:el.getBoundingClientRect().right}))'), flush=True)
                        page.screenshot(path=str(OUT / f'overflow-{width}.png'), full_page=True)
                    self.assertFalse(overflow, f'La page déborde en largeur : {path} à {width}px')
                    expect(page.locator('h1')).to_have_count(1)
                    if path.startswith('albums/'):
                        unlock_album(page)
                        check_masonry(page)

    @unittest.skipUnless(os.environ.get('CAPTURES'), 'captures sur demande : lancer les tests avec CAPTURES=1')
    def test_screenshots_for_review(self):
        """Captures rangées dans test-results/, pour juger la mise en page d'un coup d'œil (seulement sur demande)."""
        page = self.page
        paths = ['index.html', 'rugby/index.html', 'instants-de-vie/index.html', 'concerts/index.html', 'regards/index.html',
                 'instants-de-vie/prestations.html', 'instants-de-vie/contact.html', 'rugby/tarifs.html', 'concerts/contact.html',
                 'mentions.html', '404.html']
        for width in [390, 1440]:
            for path in paths:
                with self.subTest(width=width, path=path):
                    self.open(path, width, wait_until='networkidle')
                    for photo in page.locator(PHOTOS_TO_LOAD).all():
                        photo.scroll_into_view_if_needed()
                        wait_until_loaded(page, photo)
                    name = path[:-5].replace('/index', '').replace('/', '-')
                    if path in ['rugby/index.html', 'instants-de-vie/index.html', 'concerts/index.html']:
                        page.locator('#presentation').screenshot(path=str(OUT / f'{name}-presentation-{width}.png'))
                    page.evaluate('scrollTo(0, 0)')
                    page.screenshot(path=str(OUT / f'{name}-{width}.png'), full_page=not path.startswith('regards/'))
                    if path == 'index.html':
                        page.screenshot(path=str(OUT / f'cover-{width}.png'))

    # Accueil et menus

    def test_phone_home_and_menus(self):
        """Accueil sur téléphone : glissements et touchers entre les univers ; menu des univers au clavier."""
        page = self.open('index.html', 390, 844)
        assert not page.locator('#navigation').evaluate('(el) => el.inert')
        # Glisser le doigt : vers la gauche l'univers suivant, vers la droite le précédent ; un geste vertical fait défiler la page.
        touch = offline(self.browser.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True))
        phone = touch.new_page()
        phone.goto(self.base + '/index.html')
        cdp = touch.new_cdp_session(phone)

        def swipe(x0, y0, x1, y1):
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x0, 'y': y0}]})
            for step in range(1, 7):
                cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x0 + (x1 - x0) * step / 6, 'y': y0 + (y1 - y0) * step / 6}]})
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        shown = phone.locator('.home-chapter.is-active')
        for gesture, universe in [((320, 420, 80, 430), 'sport'), ((80, 420, 320, 425), 'life'), ((80, 420, 320, 425), 'art')]:
            swipe(*gesture)
            expect(shown).to_have_class(re.compile(r'\bhome-chapter-' + universe + r'\b'))
            expect(phone.locator('.home-slide.is-active')).to_have_class(re.compile(r'\bhome-slide-' + universe + r'\b'))
        expect(phone.locator('.home-stage')).not_to_have_class(re.compile(r'\bis-playing\b'))
        swipe(200, 600, 210, 250)
        phone.wait_for_timeout(300)
        expect(shown).to_have_class(re.compile(r'\bhome-chapter-art\b'))
        phone.evaluate('scrollTo(0, 0)')
        swipe(300, 780, 60, 780)
        expect(shown).to_have_class(re.compile(r'\bhome-chapter-life\b'))
        assert phone.url.endswith('/index.html'), 'Glisser entre les univers change la photo sans ouvrir un univers'
        # Toucher la photo passe à l'univers suivant ; toucher le titre ouvre la page de l'univers.
        # On attend d'abord que la page ait fini de glisser : un toucher pendant l'élan ne fait que l'arrêter.
        phone.evaluate('''() => new Promise(resolve => {
            let last = scrollY, still = 0;
            const check = () => { still = scrollY === last ? still + 1 : 0; last = scrollY; if (still >= 12) resolve(); else requestAnimationFrame(check); };
            requestAnimationFrame(check);
        })''')
        phone.touchscreen.tap(195, 300)
        expect(shown).to_have_class(re.compile(r'\bhome-chapter-sport\b'))
        expect(phone.locator('.home-slide.is-active')).to_have_class(re.compile(r'\bhome-slide-sport\b'))
        assert phone.url.endswith('/index.html'), 'Toucher la photo change d’univers sans quitter la page'
        phone.locator('.home-copy.is-active h2 a').tap()
        phone.wait_for_url('**/rugby/index.html')
        touch.close()
        page.goto(self.base + '/rugby/index.html')
        menu = page.locator('.menu-toggle')
        expect(menu).to_have_accessible_name('Ouvrir le menu')
        menu.focus()
        page.keyboard.press('Enter')
        expect(menu).to_have_attribute('aria-expanded', 'true')
        assert not page.locator('#navigation').evaluate('(el) => el.inert')
        page.keyboard.press('Escape')
        expect(menu).to_be_focused()
        assert page.locator('#navigation').evaluate('(el) => el.inert')
        page.set_viewport_size({'width': 1440, 'height': 900})
        expect(menu).to_be_hidden()
        expect(menu).to_have_attribute('aria-expanded', 'false')
        expect(page.locator('#navigation')).to_be_visible()
        assert not page.locator('#navigation').evaluate('(el) => el.inert')
        page.locator('#navigation a').first.focus()
        expect(page.locator('#navigation a').first).to_be_focused()

    def test_home_on_computer(self):
        """Accueil sur ordinateur : liens du bandeau, survol et flèches du clavier, titres qui ouvrent chaque univers."""
        page = self.open('index.html', 1440)
        instagram = page.locator('#navigation .portal-instagram')
        expect(instagram).to_have_accessible_name(re.compile('Instagram'))
        assert min(instagram.bounding_box()[side] for side in ('width', 'height')) >= 44, 'L’icône Instagram est facile à toucher'
        page.locator('#navigation a[href="#a-propos"]').click()
        page.wait_for_function('Math.abs(document.getElementById("a-propos").getBoundingClientRect().top) <= 2')
        page.locator('#a-propos .button').click()
        page.wait_for_function('Math.abs(document.getElementById("contact").getBoundingClientRect().top) <= 2')
        page.evaluate('scrollTo({top: 0, behavior: "instant"})')
        expect(page.locator('#contact form')).to_have_attribute('method', 'POST')
        expect(page.locator('.home-slide.is-active')).to_have_count(1)
        assert page.locator('.home-slide-art img').get_attribute('src') is None, 'Les photos suivantes attendent d’être montrées'
        page.locator('.home-chapter-sport').hover()
        expect(page.locator('.home-slide.is-active')).to_have_class(re.compile(r'\bhome-slide-sport\b'))
        expect(page.locator('.home-copy.is-active')).to_have_class(re.compile(r'\bhome-copy-sport\b'))
        page.mouse.move(700, 300)
        # Flèches du clavier : univers suivant, précédent, et retour au dernier après le premier.
        for key, universe in [('ArrowRight', 'concert'), ('ArrowLeft', 'sport'), ('ArrowLeft', 'life'), ('ArrowLeft', 'art'), ('ArrowRight', 'life')]:
            page.keyboard.press(key)
            expect(page.locator('.home-slide.is-active')).to_have_class(re.compile(r'\bhome-slide-' + universe + r'\b'))
            expect(page.locator('.home-chapter.is-active')).to_have_class(re.compile(r'\bhome-chapter-' + universe + r'\b'))
        page.locator('#contact input').first.focus()
        page.keyboard.press('ArrowRight')
        page.wait_for_timeout(300)
        expect(page.locator('.home-slide.is-active')).to_have_class(re.compile(r'\bhome-slide-life\b'))
        page.evaluate('document.activeElement.blur(); scrollTo({top: 0, behavior: "instant"})')
        # Chaque univers a la même adresse sur sa vignette, son titre et son bouton ; le titre affiché ouvre son univers.
        destinations = [chapter.get_attribute('href') for chapter in page.locator('.home-chapter').all()]
        assert [link.get_attribute('href') for link in page.locator('.home-go').all()] == destinations
        assert [title.get_attribute('href') for title in page.locator('.home-copy h2 a').all()] == destinations
        for href in destinations:
            assert page.request.get(self.base + '/' + href).ok, href
        page.locator('.home-copy.is-active h2 a').click()
        page.wait_for_url('**/' + destinations[0])

    def test_rugby_journey(self):
        """De l'accueil au rugby, puis un album, le contact préréglé et le retour à l'accueil."""
        page = self.open('index.html', 1440)
        page.locator('.home-chapter-sport').click()
        page.wait_for_url('**/rugby/index.html')
        expect(page.locator('body')).to_have_class('rugby-page')
        hero_photo = page.locator('.rugby-hero>img')
        assert hero_photo.bounding_box()['width'] <= int(hero_photo.get_attribute('width')) + 1
        expect(page.locator('.rugby-reportage')).to_have_count(sum(a['category'] == 'Rugby' for a in self.albums))
        page.locator('.rugby-reportage').first.click()
        page.wait_for_url('**/' + self.rugby_page)
        expect(page.locator('body')).to_have_class('rugby-page')
        page.locator('.gallery-end .button').click()
        page.wait_for_url('**/rugby/contact.html')
        expect(page.locator('body')).to_have_class('rugby-page')
        expect(page.locator('#project')).to_have_value('sport')
        expect(page.locator('#wedding-offer-group')).to_be_hidden()
        page.set_viewport_size({'width': 390, 'height': 844})
        page.locator('.menu-toggle').click()
        page.locator('#navigation a').filter(has_text='Tous les univers').click()
        page.wait_for_url('**/index.html#haut')
        assert page.evaluate('scrollY') <= 1, 'Le retour montre le haut de l’accueil'

    def test_wedding_and_concert_doors(self):
        """Mariage et Concerts : la porte de l'accueil, un reportage, la visionneuse et le retour à l'accueil."""
        page = self.page
        for door, destination, category in [('home-chapter-life', 'instants-de-vie', 'Mariage'), ('home-chapter-concert', 'concerts', 'Concerts')]:
            with self.subTest(universe=destination):
                self.open('index.html', 390, 844)
                page.locator('.' + door).click()
                page.wait_for_url('**/' + destination + '/index.html')
                expected = [a for a in self.albums if a['category'] == category]
                expect(page.locator('.collection-link')).to_have_count(len(expected))
                page.locator('.collection-link').first.click()
                page.wait_for_url('**/albums/' + expected[0]['id'] + '.html')
                expect(page.locator('body')).to_have_class(destination + '-page')
                page.locator('.photo-link').first.click()
                expect(page.get_by_role('dialog')).to_be_visible()
                page.keyboard.press('Escape')
                if page.locator('.menu-toggle').is_visible():
                    page.locator('.menu-toggle').click()
                page.locator('#navigation a[href$="index.html#haut"]').click()
                page.wait_for_url('**/index.html#haut')
                assert page.evaluate('scrollY') <= 1, destination

    # Projets personnels

    def test_personal_projects_slideshow(self):
        """Une image à la fois, visionneuse au clavier, ouverture d'une série et retours."""
        page = self.open('regards/index.html', 390, 844)
        art_count, photos = self.art_count, len(self.individual_photos)
        expect(page.locator('.art-series-work')).to_have_count(len(self.art_albums))
        expect(page.locator('.art-work')).to_have_count(photos)
        expect(page.locator('.art-photo-link')).to_have_count(photos)
        expect(page.locator('.art-slide:visible')).to_have_count(1)
        expect(page.locator('.art-controls')).to_be_visible()
        expect(page.locator('.art-progress')).to_have_text(f'01 / {art_count:02d}')
        page.locator('.art-prev').click()
        expect(page.locator('.art-progress')).to_have_text(f'{art_count:02d} / {art_count:02d}')
        page.locator('.art-photo-link').last.click()
        expect(page.get_by_role('dialog')).to_be_visible()
        expect(page.locator('#photo-counter')).to_have_text(f'{photos} / {photos}')
        page.keyboard.press('ArrowRight')
        expect(page.locator('#photo-counter')).to_have_text(f'1 / {photos}')
        expect(page.locator('.art-progress')).to_have_text(f'{art_count:02d} / {art_count:02d}')
        page.keyboard.press('Escape')
        expect(page.locator('.art-photo-link').last).to_be_focused()
        page.keyboard.press('ArrowRight')
        expect(page.locator('.art-progress')).to_have_text(f'01 / {art_count:02d}')
        page.keyboard.press('ArrowRight')
        page.locator('.art-series-link').nth(1).click()
        page.wait_for_url('**/albums/' + self.art_albums[1]['id'] + '.html')
        expect(page.locator('body')).to_have_class('regards-page')
        expect(page.locator('.photo-link')).to_have_count(len(self.art_albums[1]['photos']))
        page.locator('.photo-link').first.click()
        expect(page.get_by_role('dialog')).to_be_visible()
        page.keyboard.press('Escape')
        page.locator('.art-return').click()
        page.wait_for_url('**/regards/index.html')
        page.locator('.art-return').click()
        page.wait_for_url('**/index.html#haut')
        assert page.evaluate('scrollY') <= 1, 'Le retour montre le haut de l’accueil'

    # Présentations et liens vers le contact

    def test_concert_presentation(self):
        page = self.open('concerts/index.html', 1440)
        page.locator('#navigation a').filter(has_text='À propos').click()
        page.wait_for_url('**/concerts/index.html#presentation')
        expect(page.locator('#presentation .personal-portrait img')).to_be_visible()
        assert '/portrait-' + self.portrait_digest + '-' in page.locator('#presentation img').get_attribute('src'), 'Le portrait affiché est le dernier'
        page.locator('#presentation .personal-actions a').click()
        page.wait_for_url('**/concerts/contact.html')
        expect(page.locator('body')).to_have_class('concerts-page')
        expect(page.locator('#project')).to_have_value('concert')

    def test_wedding_contact_presets(self):
        """Chaque « Demander un devis » des tarifs Mariage ouvre le contact avec le bon projet et la bonne formule."""
        page = self.page
        for project in ['bapteme', 'fiancailles', 'couple', 'famille', 'evenement']:
            with self.subTest(project=project):
                self.open('instants-de-vie/prestations.html', 1440)
                page.locator('.life-services-page a[href$="projet=' + project + '"]').click()
                page.wait_for_url('**/instants-de-vie/contact.html?projet=' + project)
                expect(page.locator('#project')).to_have_value(project)
                expect(page.locator('#wedding-offer-group')).to_be_hidden()
        for index, offer in enumerate(['ceremonie', 'cocktail', 'complet']):
            with self.subTest(offer=offer):
                self.open('instants-de-vie/prestations.html', 1440)
                page.locator('.life-price-row').nth(index).locator('a').click()
                page.wait_for_url('**/instants-de-vie/contact.html?projet=mariage&offre=' + offer)
                expect(page.locator('#project')).to_have_value('mariage')
                expect(page.locator('#wedding-offer')).to_have_value(offer)
                expect(page.locator('#wedding-offer-group')).to_be_visible()
                expect(page.locator('body')).to_have_class('instants-de-vie-page')

    def test_tariff_contact_links(self):
        """Tarifs du sport : le devis ouvre le contact de l'univers, avec le bon projet (les concerts n'ont pas de tarifs)."""
        page = self.page
        for universe, contact_path, project, button in [('rugby', '/rugby/contact.html', 'sport', '.rugby-pricing-summary .button')]:
            with self.subTest(universe=universe):
                self.open(universe + '/index.html', 1440)
                page.locator('#navigation a').filter(has_text='Tarifs').click()
                page.wait_for_url('**/' + universe + '/tarifs.html')
                page.locator(button).click()
                page.wait_for_url('**' + contact_path)
                expect(page.locator('#project')).to_have_value(project)

    # Albums et visionneuse

    def test_albums_order_and_masonry(self):
        """Chaque album montre ses photos dans l'ordre choisi, avec leurs descriptions, en mosaïque sans trou."""
        page = self.page
        descriptions = photo_descriptions(ROOT)
        for album in self.albums:
            with self.subTest(album=album['id']):
                self.open(f'albums/{album["id"]}.html', 1440)
                unlock_album(page)
                expect(page.locator('.photo-link')).to_have_count(len(album['photos']))
                expect(page.locator('.gallery-description')).to_have_text(album['description'])
                links = page.locator('.photo-link').evaluate_all('(links)=>links.map(link=>decodeURI(new URL(link.href).pathname.slice(1)))')
                alts = page.locator('.photo-link img').evaluate_all('(images)=>images.map(image=>image.alt)')
                for index, (link, alt, source) in enumerate(zip(links, alts, album['photos'], strict=True), 1):
                    assert link.startswith('images/optimized/'), 'Seuls les exports web sont publiés'
                    if re.fullmatch(r'p-[0-9a-f]{32}\.bin', Path(link).name):
                        assert album.get('password_protected'), 'Seuls les albums protégés publient des images chiffrées'
                        # Sans description écrite, la photo est décrite par le titre de l'album et son rang.
                        expected = descriptions.get(source, album.get('photo_alts', {}).get(source, f'{album["title"]} — photographie {index}'))
                        assert alt == expected, 'Le choix et l’ordre des photos sont respectés'
                        continue
                    assert Path(link).name.startswith(variant_key(source) + '-'), 'Le choix et l’ordre des photos sont respectés'
                schema = page.locator('script[type="application/ld+json"]').text_content()
                assert any(node['@type'] == 'CollectionPage' for node in json.loads(schema)['@graph'])
                check_masonry(page)
        for width in [320, 1440, 768, 390]:
            with self.subTest(resized_to=width):
                page.set_viewport_size({'width': width, 'height': 844})
                check_masonry(page)

    def test_viewer_keyboard_and_focus(self):
        """Visionneuse : clavier, retour à la première photo après la dernière, focus gardé dans la fenêtre."""
        page = self.open(self.rugby_page, 390, 844)
        count = self.rugby_count
        first = page.locator('.photo-link').first
        first.focus()
        page.keyboard.press('Enter')
        expect(page.get_by_role('dialog')).to_be_visible()
        expect(page.get_by_role('button', name='Fermer la photo')).to_be_focused()
        steps = min(32, count - 1)
        for _ in range(steps):
            page.keyboard.press('ArrowRight')
        expect(page.locator('#photo-counter')).to_have_text(f'{steps + 1} / {count}')
        page.keyboard.press('Escape')
        expect(first).to_be_focused()
        page.locator('.photo-link').last.click()
        expect(page.locator('#photo-counter')).to_have_text(f'{count} / {count}')
        page.keyboard.press('ArrowRight')
        expect(page.locator('#photo-counter')).to_have_text(f'1 / {count}')
        page.keyboard.press('ArrowLeft')
        expect(page.locator('#photo-counter')).to_have_text(f'{count} / {count}')
        for width in [320, 390, 768, 1440]:
            page.set_viewport_size({'width': width, 'height': 844})
            for control in ['.lightbox-prev', '.lightbox-next', '.lightbox-close']:
                box = page.locator(control).bounding_box()
                assert box and box['x'] >= 0 and box['x'] + box['width'] <= width, (width, control, box)
            for _ in range(8):
                page.keyboard.press('Tab')
                assert page.evaluate('document.getElementById("lightbox").contains(document.activeElement)')
        page.set_viewport_size({'width': 390, 'height': 844})
        page.keyboard.press('Escape')
        expect(page.locator('.photo-link').last).to_be_focused()

    def test_viewer_recovers_from_missing_photo(self):
        page = self.open(self.rugby_page, 390, 844)
        failed = [part.strip().split()[0].removeprefix('../') for part in page.locator('.photo-link').first.get_attribute('data-viewer-srcset').split(',')]
        for path in failed:
            page.route('**/' + path, lambda route: route.fulfill(status=404, body='not available'))
        page.goto(self.base + '/' + self.rugby_page)
        page.locator('.photo-link').first.click()
        expect(page.locator('#photo-status')).to_contain_text('ne peut pas être chargée')
        page.keyboard.press('ArrowRight')
        expect(page.locator('#lightbox img')).to_be_visible()
        page.keyboard.press('Escape')
        for path in failed:
            page.unroute('**/' + path)
        self.errors[:] = [error for error in self.errors if not any('/' + path in error for path in failed)]

    # Formulaire de contact (envois interceptés)

    def fill_form(self, name, message):
        self.page.locator('#name').fill(name)
        self.page.locator('#email').fill('test@example.invalid')
        self.page.locator('#message').fill(message)

    def test_contact_form(self):
        """Projet prérempli, échec puis réussite simulés, message gardé en cas d'échec, pas de double envoi."""
        page = self.open('index.html?projet=mariage#contact', 390, 844)
        expect(page.locator('#project')).to_have_value('mariage')
        assert page.locator('#message').evaluate('(el) => el.dispatchEvent(new MouseEvent("contextmenu", {bubbles:true, cancelable:true}))')
        self.fill_form('Test local', 'Message de test intercepté, sans envoi réel.')
        page.route(ENDPOINT, lambda route: route.fulfill(status=422, headers=CORS, content_type='application/json', body='{"errors":[]}'))
        page.get_by_role('button', name='Envoyer').click()
        expect(page.locator('#form-status')).to_contain_text('n’a pas pu être confirmé')
        expect(page.locator('#message')).not_to_have_value('')
        expect(page.get_by_role('button', name='Envoyer')).to_be_enabled()
        page.unroute(ENDPOINT)
        held = []
        page.route(ENDPOINT, lambda route: held.append(route))
        page.evaluate('document.getElementById("contact-form").requestSubmit(); document.getElementById("contact-form").requestSubmit()')
        expect(page.get_by_role('button', name='Envoi en cours…')).to_be_disabled()
        page.wait_for_timeout(100)
        assert len(held) == 1, 'Un seul envoi, même en cliquant deux fois'
        held[0].fulfill(status=200, headers=CORS, content_type='application/json', body='{"ok":true}')
        expect(page.locator('#form-status')).to_contain_text('bien été envoyé')
        expect(page.locator('#message')).to_have_value('')
        expect(page.locator('#project')).to_have_value('mariage')

    def test_contact_form_keeps_recent_edits(self):
        """Un texte modifié pendant l'envoi reste dans le formulaire, et le curseur aussi."""
        page = self.open('index.html#contact', 390, 844)
        held = []
        page.route(ENDPOINT, lambda route: held.append(route))
        self.fill_form('Test de modification', 'Message envoyé')
        page.get_by_role('button', name='Envoyer').click()
        expect(page.get_by_role('button', name='Envoi en cours…')).to_be_disabled()
        page.locator('#message').fill('Nouveau texte pendant l’envoi')
        page.wait_for_function('document.querySelector("#contact-form").getAttribute("aria-busy") === "true"')
        assert len(held) == 1
        held[0].fulfill(status=200, headers=CORS, content_type='application/json', body='{"ok":true}')
        expect(page.locator('#form-status')).to_contain_text('Vos modifications récentes sont conservées')
        expect(page.locator('#message')).to_have_value('Nouveau texte pendant l’envoi')
        expect(page.locator('#message')).to_be_focused()

    # Accessibilité et légèreté

    def test_short_mobile_screens(self):
        """Sur un téléphone tenu en largeur (écran très bas), tous les liens du menu restent atteignables."""
        page = self.page
        for path in ['rugby/index.html', 'instants-de-vie/index.html', 'concerts/index.html', 'mentions.html']:
            with self.subTest(path=path):
                self.open(path, 390, 320)
                page.locator('.menu-toggle').click()
                menu = page.locator('#navigation')
                menu_box = menu.bounding_box()
                assert menu_box['y'] + menu_box['height'] <= 320, f'Le menu sort de l’écran : {path}'
                last = menu.locator('a').last
                last.scroll_into_view_if_needed()
                last_box = last.bounding_box()
                assert last_box['y'] >= menu_box['y'] and last_box['y'] + last_box['height'] <= 320, path
                page.keyboard.press('Escape')
                expect(menu).to_be_hidden()

    def test_text_at_200_percent(self):
        """Avec le texte agrandi à 200 %, l'accueil et le titre du mariage restent lisibles en entier."""
        page = self.page
        for width in [320, 390]:
            for path in ['index.html', 'instants-de-vie/index.html']:
                with self.subTest(width=width, path=path):
                    self.open(path, width, 844)
                    page.evaluate('document.documentElement.style.fontSize="200%"')
                    page.evaluate('document.fonts.ready')
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), (path, width, 'le texte à 200 % déborde')
                    selector = '.home-copy.is-active, .home-chapter' if path == 'index.html' else '.life-hero-heading'
                    for element in page.locator(selector).all():
                        assert element.evaluate('''el => {
                            const bounds = el.getBoundingClientRect();
                            const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
                            while (walker.nextNode()) {
                                if (!walker.currentNode.textContent.trim() || walker.currentNode.parentElement.closest('.sr-only')) continue;
                                const range = document.createRange();
                                range.selectNodeContents(walker.currentNode);
                                for (const rect of range.getClientRects()) {
                                    if (rect.left < bounds.left - 1 || rect.right > bounds.right + 1) return false;
                                }
                            }
                            return true;
                        }'''), (path, width, 'Le texte agrandi reste dans son cadre')
                    if path == 'index.html':
                        boxes = [el.bounding_box() for el in page.locator('.home-chapter').all()]
                        assert all(a['x'] + a['width'] <= b['x'] + 1 or b['x'] + b['width'] <= a['x'] + 1 or
                                   a['y'] + a['height'] <= b['y'] + 1 or b['y'] + b['height'] <= a['y'] + 1
                                   for k, a in enumerate(boxes) for b in boxes[k + 1:]), 'Les noms agrandis des univers ne se chevauchent pas'

    def test_without_javascript(self):
        """Sans JavaScript : les liens des albums, le menu et le formulaire marchent encore."""
        nojs = offline(self.browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844}))
        fallback = nojs.new_page()
        fallback.goto(self.base + '/regards/index.html')
        expect(fallback.locator('.art-series-work:visible, .art-work:visible')).to_have_count(self.art_count)
        expect(fallback.locator('.art-controls')).to_be_hidden()
        fallback.locator('.art-series-link').first.click()
        expect(fallback.locator('.photo-link')).to_have_count(len(self.art_albums[0]['photos']))
        fallback.goto(self.base + '/' + self.rugby_page)
        expect(fallback.locator('.photo-link')).to_have_count(self.rugby_count)
        expect(fallback.locator('#navigation a').first).to_be_visible()
        fallback.goto(self.base + '/index.html')
        expect(fallback.locator('form')).to_have_attribute('method', 'POST')
        fallback.goto(self.base + '/rugby/contact.html')
        expect(fallback.locator('#wedding-offer-group')).to_have_count(0)
        expect(fallback.locator('#project')).to_have_value('sport')
        expect(fallback.locator('form')).to_have_attribute('method', 'POST')
        nojs.close()

    def test_contrast_and_readability(self):
        """Icône Instagram bien contrastée, petits textes d'au moins 12 px, retour en haut au clavier."""
        page = self.open('index.html', 390, 844, wait_until='networkidle')
        link = page.locator('#navigation .portal-instagram')
        link_box = link.bounding_box()
        link_color = tuple(map(int, re.findall(r'\d+', link.evaluate('(el)=>getComputedStyle(el).color'))[:3]))
        pixels = Image.open(io.BytesIO(page.screenshot())).convert('RGB')
        background = pixels.getpixel((int(link_box['x']) - 3, int(link_box['y']) + 2))
        assert contrast_ratio(link_color, background) >= 4.5, 'L’icône Instagram de l’accueil manque de contraste'
        for path in ['index.html', 'instants-de-vie/index.html', 'concerts/index.html']:
            page.goto(self.base + '/' + path)
            for element in page.locator('.kicker, .site-footer a, .nav-links a').all():
                assert element.evaluate('(el)=>parseFloat(getComputedStyle(el).fontSize)') >= 12
        page.goto(self.base + '/' + self.rugby_page)
        page.locator('.photo-link').last.scroll_into_view_if_needed()
        expect(page.locator('.back-to-top')).to_be_visible()
        page.locator('.back-to-top').click()
        expect(page.locator('main')).to_be_focused()

    def test_homepage_weight_on_phone(self):
        """Premier affichage de l'accueil sur téléphone : moins de 1 Mo, et jamais le portrait original."""
        fresh = offline(self.browser.new_context(viewport={'width': 390, 'height': 844}))
        landing = fresh.new_page()
        landing.goto(self.base + '/index.html', wait_until='networkidle')
        resources = landing.evaluate('performance.getEntriesByType("resource").map(r=>({url:r.name,bytes:r.transferSize}))')
        initial_bytes = sum(r['bytes'] for r in resources)
        (OUT / 'homepage-resources.json').write_text(json.dumps({'viewport': 390, 'resourceBytes': initial_bytes, 'resources': resources}, indent=2), encoding='utf-8')
        fresh.close()
        assert initial_bytes < 1000000, f'Accueil trop lourd sur téléphone : {initial_bytes} octets'
        assert all('/images/portrait.jpg' not in r['url'] for r in resources)


if __name__ == '__main__':
    unittest.main()
