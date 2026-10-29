"""Concert regressions: readable layouts, remembered entrance and detailed large photos."""
from pathlib import Path
import functools
import http.server
import json
import math
import os
import re
import sys
import threading
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/python'))
from PIL import Image
from playwright.sync_api import sync_playwright, expect
from test_browser import QuietHandler, unlock_album


def run():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
        functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/'
    errors, results = [], []
    out = ROOT / 'test-results/concerts-updated'
    out.mkdir(exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get('CHROME_PATH',
                r'C:\Program Files\Google\Chrome\Application\chrome.exe'))
            context = browser.new_context(viewport={'width': 390, 'height': 844})
            context.route('https://**/*', lambda route: route.abort())
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base + 'concerts/index.html')
            expect(page.locator('.theatre-enter')).to_be_visible()
            page.locator('.theatre-enter').click()
            assert page.locator('.theatre-curtain').first.evaluate('(el) => el.getAnimations().length') > 0, 'First entrance must animate'
            page.evaluate('document.querySelectorAll(".theatre-curtain").forEach(el => el.getAnimations().forEach(a => a.finish()))')
            expect(page.locator('[data-theatre]')).to_have_class(re.compile(r'\bis-open\b'))
            page.locator('.concert-ticket').first.click()
            page.go_back()
            expect(page.locator('.theatre-enter')).to_be_hidden()
            page.reload()
            expect(page.locator('.theatre-enter')).to_be_hidden()
            for album in ['concertsinfonia', 'noel']:
                page.goto(base + f'albums/{album}.html')
                unlock_album(page)
                page.locator('.collection-gallery-header>a').click()
                page.wait_for_url('**/concerts/index.html#reportages')
                expect(page.locator('.theatre-enter')).to_be_hidden()
            results.append('First visit animates; browser back, reload and album returns preserve access')
            for width, height in [(320, 568), (390, 844), (768, 1024), (1440, 900), (844, 390), (667, 375)]:
                page.set_viewport_size({'width': width, 'height': height})
                page.goto(base + 'concerts/index.html#reportages', wait_until='networkidle')
                page.evaluate('document.fonts.ready')
                page.evaluate('scrollTo(0,0)')
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), (width, height)
                image = page.locator('.concert-cover img')
                box = image.bounding_box()
                ratio = int(image.get_attribute('width')) / int(image.get_attribute('height'))
                assert abs(box['width'] / box['height'] - ratio) < .01, 'Hero must keep its proportions without a wide empty frame'
                if width > height:
                    assert box['height'] >= 250, 'Landscape photos must remain large enough to appreciate'
                page.locator('.concert-ticket').first.click()
                page.wait_for_url('**/albums/concertsinfonia.html')
            page.set_viewport_size({'width': 390, 'height': 844})
            page.goto(base + 'concerts/index.html#reportages')
            page.evaluate('document.documentElement.style.fontSize="200%";scrollTo(0,0)')
            page.wait_for_function('''() => {
                const nav=document.querySelector('.site-nav').getBoundingClientRect();
                const heading=document.querySelector('.concert-title-row').getBoundingClientRect();
                return heading.top >= nav.bottom;
            }''')
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
            page.evaluate('document.documentElement.style.removeProperty("font-size")')
            results.append('Six viewport formats: large proportional photos, working tickets, text at 200% below navigation')
            context.close()

            fallback = browser.new_context(java_script_enabled=False)
            fallback.route('https://**/*', lambda route: route.abort())
            page = fallback.new_page()
            page.goto(base + 'concerts/contact.html')
            expect(page.locator('#wedding-offer-group')).to_have_count(0)
            expect(page.locator('#project')).to_have_value('concert')
            expect(page.locator('form')).to_have_attribute('method', 'POST')
            page.goto(base + 'contact.html')
            expect(page.locator('#wedding-offer-group')).to_have_count(1)
            fallback.close()
            results.append('Concert contact has no wedding offers without JavaScript; general contact retains them')

            private = browser.new_context(viewport={'width': 390, 'height': 844})
            private.route('https://**/*', lambda route: route.abort())
            private.add_init_script("Object.defineProperty(window, 'sessionStorage', {get() {throw new DOMException('Unavailable', 'SecurityError')}})")
            page = private.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base + 'concerts/index.html')
            expect(page.locator('.theatre-enter')).to_be_visible()
            page.locator('.theatre-enter').click()
            page.reload()
            expect(page.locator('.theatre-enter')).to_be_hidden()
            private.close()
            results.append('Fresh sessions keep the first entrance; blocked session storage still preserves browser history')

            retina = browser.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=3)
            retina.route('https://**/*', lambda route: route.abort())
            page = retina.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base + 'albums/concertsinfonia.html')
            link = page.locator('.photo-link').nth(3)
            original = ROOT / unquote(urlsplit(link.get_attribute('href')).path.removeprefix('../'))
            link.click()
            photo = page.locator('#lightbox img')
            expect(photo).to_be_visible()
            current = photo.evaluate('(img) => img.currentSrc')
            export = ROOT / unquote(urlsplit(current).path.lstrip('/'))
            with Image.open(original) as master, Image.open(export) as image:
                needed = math.ceil(photo.bounding_box()['width'] * 3)
                assert image.width >= needed, (image.width, needed)
                assert image.width <= master.width
                native_candidate = link.get_attribute('data-viewer-srcset').split(',')[-1].strip()
                assert native_candidate.endswith(f'{master.width}w'), 'Native source resolution must stay available'
            assert export.stat().st_size < original.stat().st_size * .6, 'Avoid the oversized master when a detailed export covers the display'
            page.keyboard.press('ArrowRight')
            expect(page.locator('#photo-counter')).to_have_text('5 / 38')
            page.keyboard.press('Escape')
            expect(page.locator('#lightbox')).not_to_be_visible()
            results.append(f'Retina view: {export.name}, {export.stat().st_size:,} bytes; sufficient physical pixels and native master still offered')
            retina.close()
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        (out / 'regressions.json').write_text(json.dumps({'results': results, 'errors': errors}, indent=2), encoding='utf-8')
    for result in results:
        print('PASS:', result, flush=True)


if __name__ == '__main__':
    run()
