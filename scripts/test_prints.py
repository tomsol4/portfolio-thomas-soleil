"""Check the informational print page and simulate contact submissions."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/python'))
import functools, http.server, threading, os, re
from playwright.sync_api import sync_playwright, expect
from test_browser import QuietHandler


def run():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get('CHROME_PATH', r'C:\Program Files\Google\Chrome\Application\chrome.exe'), headless=True)
            context = browser.new_context(reduced_motion='reduce')
            context.route('https://**/*', lambda route: route.abort())
            page = context.new_page()
            page.on('pageerror', lambda err: errors.append(str(err)))
            page.on('response', lambda r: errors.append(f'{r.status}: {r.url}') if r.url.startswith(base) and r.status >= 400 else None)
            for width in [320, 390, 768, 1440]:
                page.set_viewport_size({'width': width, 'height': 900})
                page.goto(base + '/regards/tirages.html', wait_until='networkidle')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), width
                expect(page.locator('main img')).to_have_count(1)
                expect(page.locator('.prints-example img')).to_have_attribute('src', re.compile('argentiqueNB-15'))
                assert page.locator('.prints-example img').evaluate('(img) => img.complete && img.naturalWidth > 0')
                expect(page.locator('#demande')).to_be_visible()
                page.get_by_role('link', name='Parlons de votre tirage').click()
                assert page.evaluate('location.hash') == '#demande'
                if width in [390, 1440]:
                    page.evaluate('scrollTo(0, 0)')
                    page.screenshot(path=str(ROOT / f'test-results/tirages-simple-{width}.png'), full_page=True)
                print(f'PASS: one example and accessible contact form at {width}px.', flush=True)
            page.locator('#name').fill('Test tirage local')
            page.locator('#email').fill('test@example.invalid')
            page.locator('#message').fill('Je souhaite un tirage du Couvent.')
            endpoint = 'https://formspree.io/f/xblwgnop'
            page.route(endpoint, lambda route: route.fulfill(status=422, content_type='application/json', body='{}'))
            page.get_by_role('button', name='Envoyer ma demande').click()
            expect(page.locator('#form-status')).to_contain_text('n’a pas pu être confirmé')
            expect(page.locator('#message')).to_have_value('Je souhaite un tirage du Couvent.')
            page.unroute(endpoint)
            payload = []
            def accepted(route):
                payload.append(route.request.post_data)
                route.fulfill(status=200, content_type='application/json', body='{}')
            page.route(endpoint, accepted)
            page.get_by_role('button', name='Envoyer ma demande').click()
            expect(page.locator('#form-status')).to_contain_text('demande de tirage a été envoyée')
            assert len(payload) == 1 and 'tirage' in payload[0] and 'Couvent' in payload[0]
            expect(page.locator('#message')).to_have_value('')
            page.goto(base + '/regards/index.html')
            page.locator('.art-shop-link').click()
            page.wait_for_url('**/regards/tirages.html')
            nojs = browser.new_context(java_script_enabled=False)
            nojs.route('https://**/*', lambda route: route.abort())
            fallback = nojs.new_page()
            fallback.goto(base + '/regards/tirages.html')
            expect(fallback.locator('#demande')).to_be_visible()
            expect(fallback.locator('form')).to_have_attribute('method', 'POST')
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
    print('PASS: simple print page, simulated contact failure/success and no-JS fallback. No real message sent.')


if __name__ == '__main__':
    run()
