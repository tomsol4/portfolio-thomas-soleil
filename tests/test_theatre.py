"""Le rideau de la page Concerts : mouvement réduit, et page complète sans JavaScript ou sans WebGL."""
import re
import unittest

import support
from support import CHROME, expect, offline
from playwright.sync_api import sync_playwright
from album_list import load_albums


class Theatre(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._site = support.local_site()
        cls.url = cls._site.__enter__() + '/concerts/index.html'
        cls._playwright = sync_playwright().start()
        cls.browser = cls._playwright.chromium.launch(executable_path=CHROME)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._playwright.stop()
        cls._site.__exit__(None, None, None)

    def test_reduced_motion_opens_at_once(self):
        """Avec « réduire les animations », la scène est ouverte tout de suite, sans mouvement."""
        reduced = offline(self.browser.new_context(reduced_motion='reduce', viewport={'width': 1440, 'height': 900}))
        page = reduced.new_page()
        page.goto(self.url)
        expect(page.locator('[data-theatre]')).to_have_attribute('data-curtain', 'open')
        expect(page.locator('[data-theatre]')).not_to_have_class(re.compile(r'\btheatre-is-moving\b'))
        expect(page.locator('.theatre-replay')).to_be_hidden()
        assert page.locator('.concert-cover img').evaluate('(img) => img.getAnimations().length') == 0
        reduced.close()

    def test_without_javascript(self):
        """Sans JavaScript, le titre, la photo et les reportages restent visibles."""
        fallback = offline(self.browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844}))
        page = fallback.new_page()
        page.goto(self.url)
        expect(page.locator('.concert-curtain')).to_be_hidden()
        expect(page.locator('.theatre-replay')).to_be_hidden()
        expect(page.locator('.concert-opening h1')).to_be_visible()
        concert_count = sum(album['category'] == 'Concerts' for album in load_albums())
        expect(page.locator('.concert-reportages .collection-link')).to_have_count(concert_count)
        expect(page.locator('.concert-reportages .collection-link').first).to_have_css('opacity', '1')
        fallback.close()

    def test_without_webgl(self):
        """Sans WebGL, la page s'ouvre directement, sans rideau."""
        plain = self._playwright.chromium.launch(executable_path=CHROME, args=['--disable-webgl', '--disable-3d-apis'])
        page = plain.new_page(viewport={'width': 1440, 'height': 900})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(self.url)
        expect(page.locator('.concert-curtain')).to_be_hidden()
        expect(page.locator('.theatre-replay')).to_be_hidden()
        expect(page.locator('[data-theatre]')).to_have_attribute('data-curtain', 'open')
        plain.close()
        assert not errors, errors


if __name__ == '__main__':
    unittest.main()
