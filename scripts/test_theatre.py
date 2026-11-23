"""Check the velvet curtain of the Concerts page in a real browser: entrance, replay, motion preference and fallbacks."""
from pathlib import Path
import functools
import http.server
import io
import json
import os
import re
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/python'))
from PIL import Image
from playwright.sync_api import sync_playwright, expect
from test_browser import QuietHandler

CHROME = os.environ.get('CHROME_PATH', r'C:\Program Files\Google\Chrome\Application\chrome.exe')


def mean(shot, x, y, size=24):
    """Average colour of a small square of the screenshot."""
    patch = shot.crop((max(0, x - size // 2), max(0, y - size // 2), x + size // 2, y + size // 2))
    pixels = list(patch.getdata())
    return tuple(sum(p[i] for p in pixels) / len(pixels) for i in range(3))


def velvet(colour):
    """Red velvet: clearly red, much more red than green or blue."""
    r, g, b = colour
    return r > 45 and r > 2.2 * g and r > 1.8 * b


def screenshot(page):
    return Image.open(io.BytesIO(page.screenshot())).convert('RGB')


def run():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
        functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/concerts/index.html'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME)
            for width in [390, 1440]:
                context = browser.new_context(viewport={'width': width, 'height': 900}, reduced_motion='no-preference')
                context.route('https://**/*', lambda route: route.abort())
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(url, wait_until='domcontentloaded')
                stage = page.locator('[data-theatre]')
                nav = page.locator('.site-nav')
                canvas = page.locator('.concert-curtain canvas')
                replay = page.locator('.theatre-replay')
                expect(stage).to_have_class(re.compile(r'\btheatre-ready\b'))
                expect(stage).to_have_attribute('data-curtain', re.compile('closed|opening'))
                expect(nav).to_have_css('background-color', 'rgba(0, 0, 0, 0)')
                stage_box, canvas_box = stage.bounding_box(), canvas.bounding_box()
                assert abs(canvas_box['width'] - stage_box['width']) < 1 and abs(canvas_box['height'] - stage_box['height']) < 1, \
                    'The curtain covers the whole stage'
                nav_height = nav.bounding_box()['height']
                shot = screenshot(page)
                assert velvet(mean(shot, int(width * .3), 450)), 'The first visit starts with the curtain closed'
                assert velvet(mean(shot, int(width * .5), int(nav_height * .8), 8)), 'The menu sits on the velvet valance'
                expect(stage).to_have_class(re.compile(r'\bis-open\b'), timeout=12000)
                expect(stage).to_have_attribute('data-curtain', 'open')
                expect(replay).to_be_visible()
                expect(replay).to_be_enabled()
                shot = screenshot(page)
                assert not velvet(mean(shot, width // 2, 620, 40)), 'Once open, the photograph fills the middle of the stage'
                assert velvet(mean(shot, 6, 450, 8)) and velvet(mean(shot, width - 7, 450, 8)), 'Gathered curtains stay at the sides'
                assert velvet(mean(shot, int(width * .5), int(nav_height * .8), 8)), 'The valance stays behind the menu'
                button = replay.bounding_box()
                assert not velvet(mean(shot, int(button['x'] + button['width'] - 6), int(button['y'] + button['height'] / 2), 6)), \
                    'The gathered curtain leaves the replay button visible'
                title = page.locator('.concert-opening h1').bounding_box()
                assert title['y'] >= nav.bounding_box()['height'] and title['y'] + title['height'] <= stage_box['y'] + stage_box['height'], \
                    'The title stays in the scene, below the menu'
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
                assert velvet(mean(screenshot(page), int(width * .5) + 40, 450)), 'Replay closes the curtain before reopening it'
                expect(stage).to_have_attribute('data-curtain', 'open', timeout=12000)
                expect(replay).to_be_enabled()
                first = page.locator('.concert-reportages .collection-link').first
                first.scroll_into_view_if_needed()
                expect(first).to_have_class(re.compile(r'\bis-visible\b'))
                first.click()
                page.wait_for_url('**/albums/concertsinfonia.html')
                page.goto(url + '#reportages')
                expect(stage).to_have_attribute('data-curtain', 'open')
                page.evaluate('scrollTo({top: 0, behavior: "instant"})')
                page.emulate_media(reduced_motion='reduce')
                expect(stage).not_to_have_class(re.compile(r'\btheatre-ready\b'))
                expect(replay).to_be_hidden()
                expect(page.locator('.theatre-reveal')).to_have_count(0)
                assert not errors, errors
                context.close()
                print(f'PASS {width}px: closed curtain and valance, side opening, replay, menu, album link and reduced motion', flush=True)
            reduced = browser.new_context(reduced_motion='reduce', viewport={'width': 1440, 'height': 900})
            reduced.route('https://**/*', lambda route: route.abort())
            page = reduced.new_page()
            page.goto(url)
            expect(page.locator('[data-theatre]')).to_have_attribute('data-curtain', 'open')
            expect(page.locator('[data-theatre]')).not_to_have_class(re.compile(r'\btheatre-is-moving\b'))
            expect(page.locator('.theatre-replay')).to_be_hidden()
            assert page.locator('.concert-cover img').evaluate('(img) => img.getAnimations().length') == 0
            shot = screenshot(page)
            assert velvet(mean(shot, 6, 450, 8)) and not velvet(mean(shot, 720, 620, 40))
            reduced.close()
            print('PASS: a reduced-motion visit opens at once, curtains already gathered at the sides', flush=True)
            fallback = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844})
            fallback.route('https://**/*', lambda route: route.abort())
            page = fallback.new_page()
            page.goto(url)
            expect(page.locator('.concert-curtain')).to_be_hidden()
            expect(page.locator('.theatre-replay')).to_be_hidden()
            expect(page.locator('.concert-opening h1')).to_be_visible()
            concert_count = sum(album['category'] == 'Concerts' for album in json.loads(
                (ROOT / 'data/albums.json').read_text(encoding='utf-8')))
            expect(page.locator('.concert-reportages .collection-link')).to_have_count(concert_count)
            expect(page.locator('.concert-reportages .collection-link').first).to_have_css('opacity', '1')
            fallback.close()
            print('PASS: without JavaScript the title, the photograph and the reportages remain visible', flush=True)
            browser.close()
            plain = p.chromium.launch(executable_path=CHROME, args=['--disable-webgl', '--disable-3d-apis'])
            page = plain.new_page(viewport={'width': 1440, 'height': 900})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(url)
            expect(page.locator('.concert-curtain')).to_be_hidden()
            expect(page.locator('.theatre-replay')).to_be_hidden()
            expect(page.locator('[data-theatre]')).to_have_attribute('data-curtain', 'open')
            assert not errors, errors
            plain.close()
            print('PASS: without WebGL the page opens directly, without curtain', flush=True)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    run()
