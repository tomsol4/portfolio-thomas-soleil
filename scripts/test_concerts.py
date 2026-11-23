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
    out.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get('CHROME_PATH',
                r'C:\Program Files\Google\Chrome\Application\chrome.exe'))
            context = browser.new_context(viewport={'width': 390, 'height': 844})
            context.route('https://**/*', lambda route: route.abort())
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base + 'concerts/index.html', wait_until='domcontentloaded')
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
                page.goto(base + f'albums/{album}.html')
                unlock_album(page)
                page.locator('.collection-gallery-header>a').click()
                page.wait_for_url('**/concerts/index.html#reportages')
                expect(stage).to_have_attribute('data-curtain', 'open')
            results.append('First visit animates; browser back, reload and album returns preserve access')
            for width, height in [(320, 568), (390, 844), (768, 1024), (1440, 900), (844, 390), (667, 375)]:
                page.set_viewport_size({'width': width, 'height': height})
                page.goto(base + 'concerts/index.html#reportages', wait_until='networkidle')
                page.evaluate('document.fonts.ready')
                page.evaluate('scrollTo(0,0)')
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), (width, height)
                stage = page.locator('[data-theatre]').bounding_box()
                image = page.locator('.concert-cover img')
                box = image.bounding_box()
                assert abs(box['width'] - stage['width']) < 1 and abs(box['y'] + box['height'] - stage['y'] - stage['height']) < 1, 'The hero photograph spans the scene down to its floor'
                assert image.evaluate('(img) => getComputedStyle(img).objectFit') == 'cover', 'The hero is cropped to the scene, never distorted'
                assert abs(box['y'] - stage['y']) < 1, 'The hero fills the whole scene'
                if width > height:
                    assert box['height'] >= 250, 'Landscape photos must remain large enough to appreciate'
                # Le titre est au centre de la scène, sous le menu, sans déborder de la scène.
                copy = page.locator('.concert-hero-copy').bounding_box()
                nav = page.locator('.site-nav').bounding_box()
                assert copy['y'] >= nav['y'] + nav['height'] - 1, 'The title stays below the menu'
                assert copy['y'] + copy['height'] <= stage['y'] + stage['height'] + 1, 'The title stays inside the scene'
                page.locator('.concert-ticket').first.click()
                page.wait_for_url('**/albums/concertsinfonia.html')
            page.set_viewport_size({'width': 390, 'height': 844})
            page.goto(base + 'concerts/index.html#reportages')
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
            page.evaluate('document.documentElement.style.removeProperty("font-size")')
            results.append('Six viewport formats: hero fills the scene, working tickets, text at 200% below navigation')
            context.close()

            fallback = browser.new_context(java_script_enabled=False)
            fallback.route('https://**/*', lambda route: route.abort())
            page = fallback.new_page()
            page.goto(base + 'concerts/contact.html')
            expect(page.locator('#wedding-offer-group')).to_have_count(0)
            expect(page.locator('#project')).to_have_value('concert')
            expect(page.locator('form')).to_have_attribute('method', 'POST')
            page.goto(base + 'index.html')
            expect(page.locator('#wedding-offer-group')).to_have_count(1)
            fallback.close()
            results.append('Concert contact has no wedding offers without JavaScript; general contact retains them')

            private = browser.new_context(viewport={'width': 390, 'height': 844})
            private.route('https://**/*', lambda route: route.abort())
            private.add_init_script("Object.defineProperty(window, 'sessionStorage', {get() {throw new DOMException('Unavailable', 'SecurityError')}})")
            page = private.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base + 'concerts/index.html', wait_until='domcontentloaded')
            expect(page.locator('[data-theatre]')).to_have_attribute('data-curtain', 'opening', timeout=5000)
            page.reload()
            expect(page.locator('[data-theatre]')).to_have_attribute('data-curtain', 'open')
            private.close()
            results.append('Fresh sessions keep the first entrance; blocked session storage still preserves browser history')

            retina = browser.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=3)
            retina.route('https://**/*', lambda route: route.abort())
            page = retina.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base + 'albums/concertsinfonia.html')
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
                source_width = manifest[source]['width']
                largest = min(source_width, 2560)
                needed = min(math.ceil(photo.bounding_box()['width'] * 3), largest)
                assert image.width >= needed, (image.width, needed)
                assert image.width <= largest
                native_candidate = link.get_attribute('data-viewer-srcset').split(',')[-1].strip()
                assert native_candidate.endswith(f'{largest}w') and '/images/optimized/' in native_candidate, 'The largest candidate is a web export capped at 2560px, never the master'
            if original.is_file():
                assert export.stat().st_size < original.stat().st_size * .6, 'Use a lightweight export in the viewer'
            page.keyboard.press('ArrowRight')
            expect(page.locator('#photo-counter')).to_have_text('5 / 38')
            page.keyboard.press('Escape')
            expect(page.locator('#lightbox')).not_to_be_visible()
            results.append(f'Retina view: {export.name}, {export.stat().st_size:,} bytes; sufficient physical pixels within the web export limit')
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
