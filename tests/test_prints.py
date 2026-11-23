"""Page des tirages : une photo d'exemple et la demande par le formulaire (envois simulés, aucun message réel)."""
import re
import unittest

import support
from support import OUT, CHROME, expect, offline, watch_errors
from playwright.sync_api import sync_playwright

ENDPOINT = 'https://formspree.io/f/xblwgnop'


class Prints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._site = support.local_site()
        cls.base = cls._site.__enter__()
        cls._playwright = sync_playwright().start()
        cls.browser = cls._playwright.chromium.launch(executable_path=CHROME, headless=True)

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
        self.assertFalse(self.errors, self.errors)

    def test_one_example_on_every_screen(self):
        page = self.page
        for width in [320, 390, 768, 1440]:
            with self.subTest(width=width):
                page.set_viewport_size({'width': width, 'height': 900})
                page.goto(self.base + '/regards/tirages.html', wait_until='networkidle')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), width
                expect(page.locator('main img')).to_have_count(1)
                expect(page.locator('.prints-example img')).to_have_attribute('src', re.compile('argentiqueNB-15'))
                assert page.locator('.prints-example img').evaluate('(img) => img.complete && img.naturalWidth > 0')
                expect(page.locator('#demande')).to_be_visible()
                page.get_by_role('link', name='Parlons de votre tirage').click()
                assert page.evaluate('location.hash') == '#demande'
                if width in [390, 1440]:
                    page.evaluate('scrollTo(0, 0)')
                    page.screenshot(path=str(OUT / f'tirages-simple-{width}.png'), full_page=True)

    def test_request_form(self):
        """Échec puis réussite simulés ; la demande contient bien « tirage » ; le lien des projets mène ici."""
        page = self.page
        page.goto(self.base + '/regards/tirages.html')
        page.locator('#name').fill('Test tirage local')
        page.locator('#email').fill('test@example.invalid')
        page.locator('#message').fill('Je souhaite un tirage du Couvent.')
        page.route(ENDPOINT, lambda route: route.fulfill(status=422, content_type='application/json', body='{}'))
        page.get_by_role('button', name='Envoyer').click()
        expect(page.locator('#form-status')).to_contain_text('n’a pas pu être confirmé')
        expect(page.locator('#message')).to_have_value('Je souhaite un tirage du Couvent.')
        page.unroute(ENDPOINT)
        payload = []

        def accepted(route):
            payload.append(route.request.post_data)
            route.fulfill(status=200, content_type='application/json', body='{}')
        page.route(ENDPOINT, accepted)
        page.get_by_role('button', name='Envoyer').click()
        expect(page.locator('#form-status')).to_contain_text('demande de tirage a été envoyée')
        assert len(payload) == 1 and 'tirage' in payload[0] and 'Couvent' in payload[0]
        expect(page.locator('#message')).to_have_value('')
        page.goto(self.base + '/regards/index.html')
        page.locator('.art-shop-link').click()
        page.wait_for_url('**/regards/tirages.html')

    def test_without_javascript(self):
        nojs = offline(self.browser.new_context(java_script_enabled=False))
        fallback = nojs.new_page()
        fallback.goto(self.base + '/regards/tirages.html')
        expect(fallback.locator('#demande')).to_be_visible()
        expect(fallback.locator('form')).to_have_attribute('method', 'POST')
        nojs.close()


if __name__ == '__main__':
    unittest.main()
