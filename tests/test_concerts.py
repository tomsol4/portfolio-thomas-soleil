"""Page Concerts : entrée mémorisée, mise en page sur six formats d'écran, contact et photos détaillées."""
import json
import math
import re
import unittest
from urllib.parse import unquote, urlsplit

import support
from support import ROOT, OUT, CHROME, expect, offline, unlock_album
from PIL import Image
from playwright.sync_api import sync_playwright


class Concerts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._site = support.local_site()
        cls.base = cls._site.__enter__() + '/'
        cls._playwright = sync_playwright().start()
        cls.browser = cls._playwright.chromium.launch(executable_path=CHROME)
        cls.out = OUT / 'concerts-updated'
        cls.out.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._playwright.stop()
        cls._site.__exit__(None, None, None)

    def setUp(self):
        self.errors = []

    def tearDown(self):
        self.assertFalse(self.errors, self.errors)

    def new_page(self, **options):
        context = offline(self.browser.new_context(**options))
        page = context.new_page()
        page.on('pageerror', lambda error: self.errors.append(str(error)))
        return context, page

    def test_entrance_is_remembered(self):
        """La première visite ouvre le rideau ; retour, rechargement et retour d'album gardent la scène ouverte."""
        context, page = self.new_page(viewport={'width': 390, 'height': 844})
        page.goto(self.base + 'concerts/index.html', wait_until='domcontentloaded')
        stage = page.locator('[data-theatre]')
        expect(stage).to_have_attribute('data-curtain', re.compile('closed|opening'))
        expect(stage).to_have_attribute('data-curtain', 'opening', timeout=5000)   # la première visite s'ouvre seule
        expect(stage).to_have_class(re.compile(r'\bis-open\b'), timeout=12000)
        page.locator('.concert-ticket').first.click()
        page.go_back()
        expect(stage).to_have_attribute('data-curtain', 'open')
        expect(stage).not_to_have_class(re.compile(r'\btheatre-is-moving\b'))
        page.reload()
        expect(stage).to_have_attribute('data-curtain', 'open')
        expect(stage).not_to_have_class(re.compile(r'\btheatre-is-moving\b'))
        for album in ['concertsinfonia', 'noel']:
            page.goto(self.base + f'albums/{album}.html')
            unlock_album(page)
            page.locator('.collection-gallery-header>a').click()
            page.wait_for_url('**/concerts/index.html#reportages')
            expect(stage).to_have_attribute('data-curtain', 'open')
        context.close()

    def test_six_screen_formats(self):
        """La photo remplit la scène, le titre reste sous le menu, les billets marchent, le texte à 200 % reste lisible."""
        context, page = self.new_page(viewport={'width': 390, 'height': 844})
        for width, height in [(320, 568), (390, 844), (768, 1024), (1440, 900), (844, 390), (667, 375)]:
            with self.subTest(width=width, height=height):
                page.set_viewport_size({'width': width, 'height': height})
                page.goto(self.base + 'concerts/index.html#reportages', wait_until='networkidle')
                page.evaluate('document.fonts.ready')
                page.evaluate('scrollTo(0,0)')
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), (width, height)
                stage = page.locator('[data-theatre]').bounding_box()
                image = page.locator('.concert-cover img')
                box = image.bounding_box()
                assert abs(box['width'] - stage['width']) < 1 and abs(box['y'] + box['height'] - stage['y'] - stage['height']) < 1, 'La photo couvre la scène jusqu’au plancher'
                assert image.evaluate('(img) => getComputedStyle(img).objectFit') == 'cover', 'La photo est recadrée, jamais déformée'
                assert abs(box['y'] - stage['y']) < 1, 'La photo remplit toute la scène'
                if width > height:
                    assert box['height'] >= 250, 'En largeur, la photo reste assez grande'
                # Le titre est au centre de la scène, sous le menu, sans déborder de la scène.
                copy = page.locator('.concert-hero-copy').bounding_box()
                nav = page.locator('.site-nav').bounding_box()
                assert copy['y'] >= nav['y'] + nav['height'] - 1, 'Le titre reste sous le menu'
                assert copy['y'] + copy['height'] <= stage['y'] + stage['height'] + 1, 'Le titre reste dans la scène'
                page.locator('.concert-ticket').first.click()
                page.wait_for_url('**/albums/concertsinfonia.html')
        page.set_viewport_size({'width': 390, 'height': 844})
        page.goto(self.base + 'concerts/index.html#reportages')
        page.evaluate('''async () => {
            await document.fonts.ready;
            document.documentElement.style.fontSize = '200%';
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            scrollTo({top:0,behavior:'instant'});
        }''')
        page.wait_for_function('''() => {
            const nav=document.querySelector('.site-nav').getBoundingClientRect();
            const heading=document.querySelector('.concert-hero-copy').getBoundingClientRect();
            return heading.top >= nav.bottom;
        }''')
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
        context.close()

    def test_contact_without_javascript(self):
        """Le contact Concerts n'a pas de formule de mariage ; celui de l'accueil la garde."""
        fallback = offline(self.browser.new_context(java_script_enabled=False))
        page = fallback.new_page()
        page.goto(self.base + 'concerts/contact.html')
        expect(page.locator('#wedding-offer-group')).to_have_count(0)
        expect(page.locator('#project')).to_have_value('concert')
        expect(page.locator('form')).to_have_attribute('method', 'POST')
        page.goto(self.base + 'index.html')
        expect(page.locator('#wedding-offer-group')).to_have_count(1)
        fallback.close()

    def test_questions_without_prices(self):
        """Pas de page Tarifs : le contact répond aux questions fréquentes sans aucun prix ; l'ancienne adresse y mène."""
        context, page = self.new_page(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
        for path in ['concerts/index.html', 'concerts/contact.html', 'albums/concertsinfonia.html']:
            page.goto(self.base + path)
            expect(page.locator('a[href*="tarifs"]')).to_have_count(0)
            expect(page.locator('body')).not_to_contain_text('€')
        page.goto(self.base + 'concerts/contact.html')
        questions = page.locator('#questions details')
        expect(questions).to_have_count(4)
        answer = questions.first.locator('p')
        expect(answer).to_be_hidden()
        questions.first.locator('summary').click()
        expect(answer).to_be_visible()
        page.locator('.concert-faq-more a').click()
        expect(page.locator('#contact-form')).to_be_in_viewport()
        page.goto(self.base + 'concerts/tarifs.html', wait_until='commit')
        page.wait_for_url('**/concerts/contact.html#questions')
        expect(page.locator('#questions')).to_be_in_viewport()
        context.close()

    def test_blocked_session_storage(self):
        """Navigation privée stricte : la première entrée s'ouvre, et le rechargement garde la scène ouverte."""
        context, page = self.new_page(viewport={'width': 390, 'height': 844})
        context.add_init_script("Object.defineProperty(window, 'sessionStorage', {get() {throw new DOMException('Unavailable', 'SecurityError')}})")
        page.goto(self.base + 'concerts/index.html', wait_until='domcontentloaded')
        expect(page.locator('[data-theatre]')).to_have_attribute('data-curtain', 'opening', timeout=5000)
        page.reload()
        expect(page.locator('[data-theatre]')).to_have_attribute('data-curtain', 'open')
        context.close()

    def test_retina_viewer(self):
        """Sur un écran très dense, la visionneuse charge assez de pixels, sans dépasser l'export de 2560 px."""
        context, page = self.new_page(viewport={'width': 1440, 'height': 900}, device_scale_factor=3)
        page.goto(self.base + 'albums/concertsinfonia.html')
        link = page.locator('.photo-link').nth(3)
        albums = json.loads((ROOT / 'data/albums.json').read_text(encoding='utf-8'))
        source = next(album for album in albums if album['id'] == 'concertsinfonia')['photos'][3]
        original = ROOT / source
        manifest = json.loads((ROOT / 'data/image-manifest.json').read_text(encoding='utf-8'))
        link.click()
        photo = page.locator('#lightbox img')
        expect(photo).to_be_visible()
        current = photo.evaluate('(img) => img.currentSrc')
        export = ROOT / unquote(urlsplit(current).path.lstrip('/'))
        with Image.open(export) as image:
            largest = min(manifest[source]['width'], 2560)
            needed = min(math.ceil(photo.bounding_box()['width'] * 3), largest)
            assert image.width >= needed, (image.width, needed)
            assert image.width <= largest
            native_candidate = link.get_attribute('data-viewer-srcset').split(',')[-1].strip()
            assert native_candidate.endswith(f'{largest}w') and '/images/optimized/' in native_candidate, 'Le plus grand choix est un export web de 2560 px au plus, jamais l’original'
        if original.is_file():
            assert export.stat().st_size < original.stat().st_size * .6, 'La visionneuse utilise un export léger'
        page.keyboard.press('ArrowRight')
        expect(page.locator('#photo-counter')).to_have_text('5 / 38')
        page.keyboard.press('Escape')
        expect(page.locator('#lightbox')).not_to_be_visible()
        context.close()


if __name__ == '__main__':
    unittest.main()
