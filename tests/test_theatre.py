"""Le rideau de velours de la page Concerts : ouverture, « Rejouer », mouvement réduit et appareils sans WebGL."""
import io
import json
import re
import unittest

import support
from support import ROOT, CHROME, expect, offline
from PIL import Image
from playwright.sync_api import sync_playwright


def mean(shot, x, y, size=24):
    """Couleur moyenne d'un petit carré de la capture d'écran."""
    patch = shot.crop((max(0, x - size // 2), max(0, y - size // 2), x + size // 2, y + size // 2))
    return patch.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))


def velvet(colour):
    """Velours rouge : nettement rouge, bien plus rouge que vert ou bleu."""
    r, g, b = colour
    return r > 45 and r > 2.2 * g and r > 1.8 * b


def screenshot(page):
    return Image.open(io.BytesIO(page.screenshot())).convert('RGB')


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

    def test_curtain_opens_and_replays(self):
        """Rideau fermé puis ouvert sur les côtés, lambrequin derrière le menu, « Rejouer », menu et lien d'album."""
        for width in [390, 1440]:
            with self.subTest(width=width):
                context = offline(self.browser.new_context(viewport={'width': width, 'height': 900}, reduced_motion='no-preference'))
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(self.url, wait_until='domcontentloaded')
                stage = page.locator('[data-theatre]')
                nav = page.locator('.site-nav')
                canvas = page.locator('.concert-curtain canvas')
                replay = page.locator('.theatre-replay')
                expect(stage).to_have_class(re.compile(r'\btheatre-ready\b'))
                expect(stage).to_have_attribute('data-curtain', re.compile('closed|opening'))
                expect(nav).to_have_css('background-color', 'rgba(0, 0, 0, 0)')
                stage_box, canvas_box = stage.bounding_box(), canvas.bounding_box()
                assert abs(canvas_box['width'] - stage_box['width']) < 1 and abs(canvas_box['height'] - stage_box['height']) < 1, \
                    'Le rideau couvre toute la scène'
                nav_height = nav.bounding_box()['height']
                shot = screenshot(page)
                assert velvet(mean(shot, int(width * .3), 450)), 'La première visite commence rideau fermé'
                assert velvet(mean(shot, int(width * .5), int(nav_height * .8), 8)), 'Le menu est posé sur le lambrequin de velours'
                expect(stage).to_have_class(re.compile(r'\bis-open\b'), timeout=12000)
                expect(stage).to_have_attribute('data-curtain', 'open')
                expect(replay).to_be_visible()
                expect(replay).to_be_enabled()
                shot = screenshot(page)
                assert not velvet(mean(shot, width // 2, 620, 40)), 'Une fois ouvert, la photo remplit le milieu de la scène'
                assert velvet(mean(shot, 6, 450, 8)) and velvet(mean(shot, width - 7, 450, 8)), 'Les pans restent froncés sur les côtés'
                assert velvet(mean(shot, int(width * .5), int(nav_height * .8), 8)), 'Le lambrequin reste derrière le menu'
                button = replay.bounding_box()
                assert not velvet(mean(shot, int(button['x'] + button['width'] - 6), int(button['y'] + button['height'] / 2), 6)), \
                    'Le rideau froncé laisse voir le bouton « Rejouer »'
                title = page.locator('.concert-opening h1').bounding_box()
                assert title['y'] >= nav.bounding_box()['height'] and title['y'] + title['height'] <= stage_box['y'] + stage_box['height'], \
                    'Le titre reste dans la scène, sous le menu'
                page.evaluate('scrollTo(0, 150)')
                expect(nav).to_have_css('background-color', 'rgb(17, 11, 14)')
                page.evaluate('scrollTo(0, 0)')
                expect(nav).to_have_css('background-color', 'rgba(0, 0, 0, 0)')
                if width == 390:
                    page.locator('.menu-toggle').click()
                    expect(nav).to_have_css('background-color', 'rgb(17, 11, 14)')
                    page.keyboard.press('Escape')
                    expect(nav).to_have_css('background-color', 'rgba(0, 0, 0, 0)')
                replay.click()
                expect(stage).to_have_attribute('data-curtain', 'opening')
                expect(replay).to_be_disabled()
                page.wait_for_timeout(1250)
                assert velvet(mean(screenshot(page), int(width * .5) + 40, 450)), '« Rejouer » referme le rideau avant de le rouvrir'
                expect(stage).to_have_attribute('data-curtain', 'open', timeout=12000)
                expect(replay).to_be_enabled()
                first = page.locator('.concert-reportages .collection-link').first
                first.scroll_into_view_if_needed()
                expect(first).to_have_class(re.compile(r'\bis-visible\b'))
                first.click()
                page.wait_for_url('**/albums/concertsinfonia.html')
                page.goto(self.url + '#reportages')
                expect(stage).to_have_attribute('data-curtain', 'open')
                page.evaluate('scrollTo({top: 0, behavior: "instant"})')
                page.emulate_media(reduced_motion='reduce')
                expect(stage).not_to_have_class(re.compile(r'\btheatre-ready\b'))
                expect(replay).to_be_hidden()
                expect(page.locator('.theatre-reveal')).to_have_count(0)
                context.close()
                assert not errors, errors

    def test_reduced_motion_opens_at_once(self):
        reduced = offline(self.browser.new_context(reduced_motion='reduce', viewport={'width': 1440, 'height': 900}))
        page = reduced.new_page()
        page.goto(self.url)
        expect(page.locator('[data-theatre]')).to_have_attribute('data-curtain', 'open')
        expect(page.locator('[data-theatre]')).not_to_have_class(re.compile(r'\btheatre-is-moving\b'))
        expect(page.locator('.theatre-replay')).to_be_hidden()
        assert page.locator('.concert-cover img').evaluate('(img) => img.getAnimations().length') == 0
        shot = screenshot(page)
        assert velvet(mean(shot, 6, 450, 8)) and not velvet(mean(shot, 720, 620, 40))
        reduced.close()

    def test_without_javascript(self):
        """Sans JavaScript, le titre, la photo et les reportages restent visibles."""
        fallback = offline(self.browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844}))
        page = fallback.new_page()
        page.goto(self.url)
        expect(page.locator('.concert-curtain')).to_be_hidden()
        expect(page.locator('.theatre-replay')).to_be_hidden()
        expect(page.locator('.concert-opening h1')).to_be_visible()
        concert_count = sum(album['category'] == 'Concerts' for album in json.loads(
            (ROOT / 'data/albums.json').read_text(encoding='utf-8')))
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
