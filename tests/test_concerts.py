"""Page Concerts : formats d'écran, contact sans JavaScript, navigation privée stricte et photos détaillées."""
import json
import math
import unittest
from urllib.parse import unquote, urlsplit

import support
from support import ROOT, CHROME, expect, offline
from PIL import Image
from playwright.sync_api import sync_playwright
from album_list import load_albums


class Concerts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._site = support.local_site()
        cls.base = cls._site.__enter__() + '/'
        cls._playwright = sync_playwright().start()
        cls.browser = cls._playwright.chromium.launch(executable_path=CHROME)
        cls.concerts = [album for album in load_albums() if album['category'] == 'Concerts']

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

    def test_six_screen_formats(self):
        """Six formats d'écran : rien ne déborde, les billets ouvrent leur album, le titre agrandi à 200 % reste sous le menu."""
        context, page = self.new_page(viewport={'width': 390, 'height': 844})
        first_album = 'albums/{}.html'.format(next(a['id'] for a in self.concerts if not a.get('password_protected')))
        for width, height in [(320, 568), (390, 844), (768, 1024), (1440, 900), (844, 390), (667, 375)]:
            with self.subTest(width=width, height=height):
                page.set_viewport_size({'width': width, 'height': height})
                page.goto(self.base + 'concerts/index.html#reportages', wait_until='networkidle')
                page.evaluate('document.fonts.ready')
                page.evaluate('scrollTo(0,0)')
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), (width, height)
                page.locator('.concert-ticket:not([data-album-locked])').first.click()
                page.wait_for_url('**/' + first_album)
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

    def test_blocked_session_storage(self):
        """Navigation privée stricte (stockage interdit) : la page Concerts s'ouvre et se recharge sans erreur."""
        context, page = self.new_page(viewport={'width': 390, 'height': 844})
        context.add_init_script("Object.defineProperty(window, 'sessionStorage', {get() {throw new DOMException('Unavailable', 'SecurityError')}})")
        page.goto(self.base + 'concerts/index.html', wait_until='load')
        expect(page.locator('.concert-reportages .collection-link')).to_have_count(len(self.concerts))
        page.reload(wait_until='load')
        expect(page.locator('.concert-reportages .collection-link')).to_have_count(len(self.concerts))
        context.close()

    def test_retina_viewer(self):
        """Sur un écran très dense, la visionneuse charge assez de pixels, sans dépasser l'export de 2560 px."""
        album = next(a for a in self.concerts if not a.get('password_protected') and len(a['photos']) > 4)
        context, page = self.new_page(viewport={'width': 1440, 'height': 900}, device_scale_factor=3)
        page.goto(self.base + f'albums/{album["id"]}.html')
        link = page.locator('.photo-link').nth(3)
        source = album['photos'][3]
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
        expect(page.locator('#photo-counter')).to_have_text(f'5 / {len(album["photos"])}')
        page.keyboard.press('Escape')
        expect(page.locator('#lightbox')).not_to_be_visible()
        context.close()


if __name__ == '__main__':
    unittest.main()
