"""Real-browser regressions. All Formspree requests are mocked; no message is sent."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/python'))
import os, json, http.server, functools, threading
from playwright.sync_api import sync_playwright, expect

OUT = ROOT / 'test-results'
OUT.mkdir(exist_ok=True)
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        try: super().do_GET()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError): pass

def run():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    albums = json.loads((ROOT / 'data/albums.json').read_text(encoding='utf-8'))
    rugby_photos = next(a['photos'] for a in albums if a['id'] == 'co_mhr')
    rugby_count = len(rugby_photos)
    results, errors = [], []
    with sync_playwright() as p:
        chrome = os.environ.get('CHROME_PATH', r'C:\Program Files\Google\Chrome\Application\chrome.exe')
        browser = p.chromium.launch(executable_path=chrome, headless=True)
        context = browser.new_context(reduced_motion='reduce')
        # External requests are blocked even if a regression introduces one.
        context.route('https://**/*', lambda route: route.abort())
        page = context.new_page()
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.on('response', lambda response: errors.append(f'{response.status}: {response.url}') if response.status >= 400 and response.url.startswith(base) else None)
        paths = ['index.html','prestations.html','a-propos.html','contact.html','mentions.html','galerie.html','404.html'] + [f'albums/{a["id"]}.html' for a in albums]
        check_paths = ['index.html'] if '--interactions-only' in sys.argv else paths
        for width in [320, 390, 768, 1440]:
            page.set_viewport_size({'width': width, 'height': 900})
            for path in check_paths:
                page.goto(base + '/' + path, wait_until='networkidle')
                overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                assert not overflow, f'Horizontal overflow: {path} at {width}px'
                expect(page.locator('h1')).to_have_count(1)
                if width in [390, 1440] and path in ['index.html','prestations.html','contact.html']:
                    page.screenshot(path=str(OUT / f'{path[:-5]}-{width}.png'), full_page=True)
            results.append(f'{len(check_paths)} pages without overflow at {width}px')
            print(results[-1], flush=True)

        page.set_viewport_size({'width': 390, 'height': 844})
        page.goto(base + '/index.html')
        menu = page.locator('.menu-toggle')
        menu.focus();page.keyboard.press('Enter')
        expect(menu).to_have_attribute('aria-expanded', 'true')
        assert not page.locator('#navigation').evaluate('(el) => el.inert')
        page.keyboard.press('Escape')
        expect(menu).to_be_focused()
        assert page.locator('#navigation').evaluate('(el) => el.inert')
        page.set_viewport_size({'width': 1440, 'height': 900})
        assert not page.locator('#navigation').evaluate('(el) => el.inert')
        results.append('Mobile menu: keyboard, Escape, focus and desktop resize')

        for album in albums:
            page.goto(base + '/albums/' + album['id'] + '.html')
            expect(page.locator('.photo-link')).to_have_count(len(album['photos']))
        page.goto(base + '/albums/co_mhr.html')
        first = page.locator('.photo-link').first
        first.focus();page.keyboard.press('Enter')
        expect(page.get_by_role('dialog')).to_be_visible()
        expect(page.get_by_role('button', name='Fermer la photo')).to_be_focused()
        steps = min(32, rugby_count - 1)
        for _ in range(steps): page.keyboard.press('ArrowRight')
        expect(page.locator('#photo-counter')).to_have_text(f'{steps + 1} / {rugby_count}')
        page.keyboard.press('Escape');expect(first).to_be_focused()
        page.locator('.photo-link').last.click()
        expect(page.locator('#photo-counter')).to_have_text(f'{rugby_count} / {rugby_count}')
        page.keyboard.press('ArrowRight');expect(page.locator('#photo-counter')).to_have_text(f'1 / {rugby_count}')
        page.keyboard.press('ArrowLeft');expect(page.locator('#photo-counter')).to_have_text(f'{rugby_count} / {rugby_count}')
        for width in [320,390,768,1440]:
            page.set_viewport_size({'width':width,'height':844})
            for control in ['.lightbox-prev','.lightbox-next','.lightbox-close']:
                box=page.locator(control).bounding_box()
                assert box and box['x']>=0 and box['x']+box['width']<=width, (width,control,box)
            for _ in range(8):
                page.keyboard.press('Tab')
                assert page.evaluate('document.getElementById("lightbox").contains(document.activeElement)')
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(OUT/'lightbox-390.png'))
        page.keyboard.press('Escape')
        expect(page.locator('.photo-link').last).to_be_focused()
        results.append('Gallery: complete navigation, wrapping, keyboard, modal focus, responsive controls')

        # Load failure stays recoverable and does not close or trap the gallery.
        original = '**/' + rugby_photos[0]
        page.route(original, lambda route: route.fulfill(status=404,body='not available'))
        page.goto(base + '/albums/co_mhr.html')
        page.locator('.photo-link').first.click()
        expect(page.locator('#photo-status')).to_contain_text('ne peut pas être chargée')
        page.keyboard.press('ArrowRight')
        expect(page.locator('#lightbox img')).to_be_visible()
        page.keyboard.press('Escape');page.unroute(original)
        # Remove only the deliberately simulated error.
        errors[:] = [err for err in errors if '/' + rugby_photos[0] not in err]
        for ident in ['co_mhr','Argentique','mariage']:
            page.goto(base + '/galerie.html?id=' + ident)
            page.wait_for_url('**/albums/' + ident + '.html')
        page.goto(base + '/galerie.html?id=unknown')
        expect(page.locator('h1')).to_have_text('Album introuvable')
        page.goto(base + '/galerie.html')
        expect(page.locator('h1')).to_have_text('Choisissez un reportage')
        results.append('Legacy URLs, absent/invalid album and photo-load failure')

        page.goto(base + '/contact.html?projet=mariage')
        expect(page.locator('#project')).to_have_value('mariage')
        page.locator('#name').fill('Test local')
        page.locator('#email').fill('test@example.invalid')
        page.locator('#message').fill('Message de test intercepté, sans envoi réel.')
        endpoint='https://formspree.io/f/xblwgnop'
        page.route(endpoint, lambda route: route.fulfill(status=422,headers={'Access-Control-Allow-Origin':'*'},content_type='application/json',body='{"errors":[]}'))
        page.get_by_role('button',name='Envoyer ma demande').click()
        expect(page.locator('#form-status')).to_contain_text('n’a pas pu être confirmé')
        expect(page.locator('#message')).not_to_have_value('')
        expect(page.get_by_role('button',name='Envoyer ma demande')).to_be_enabled()
        page.unroute(endpoint)
        held=[]
        page.route(endpoint,lambda route: held.append(route))
        page.evaluate('document.getElementById("contact-form").requestSubmit(); document.getElementById("contact-form").requestSubmit()')
        expect(page.get_by_role('button',name='Envoi en cours…')).to_be_disabled()
        page.wait_for_timeout(100)
        assert len(held)==1, 'Duplicate request'
        held[0].fulfill(status=200,headers={'Access-Control-Allow-Origin':'*'},content_type='application/json',body='{"ok":true}')
        expect(page.locator('#form-status')).to_contain_text('bien été envoyé')
        expect(page.locator('#message')).to_have_value('')
        results.append('Form: project preset, mocked failure/success, preserved message, duplicate prevention')

        nojs=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
        nojs.route('https://**/*',lambda route:route.abort())
        fallback=nojs.new_page()
        fallback.goto(base+'/albums/co_mhr.html')
        expect(fallback.locator('.photo-link')).to_have_count(rugby_count)
        expect(fallback.locator('#navigation a').first).to_be_visible()
        fallback.goto(base+'/contact.html')
        expect(fallback.locator('form')).to_have_attribute('method','POST')
        results.append('Without JavaScript: album links, navigation and native form fallback')
        fresh=browser.new_context(viewport={'width':390,'height':844})
        fresh.route('https://**/*',lambda route:route.abort())
        landing=fresh.new_page()
        landing.goto(base+'/index.html',wait_until='networkidle')
        resources=landing.evaluate('performance.getEntriesByType("resource").map(r=>({url:r.name,bytes:r.transferSize}))')
        initial_bytes=sum(r['bytes'] for r in resources)
        assert initial_bytes<1000000, f'Homepage resource budget exceeded: {initial_bytes}'
        assert all('/images/portrait.jpg' not in r['url'] for r in resources)
        (OUT/'homepage-resources.json').write_text(json.dumps({'viewport':390,'resourceBytes':initial_bytes,'resources':resources},indent=2),encoding='utf-8')
        results.append(f'Homepage mobile: {initial_bytes} resource bytes on a fresh local browser context')
        assert not errors, '\n'.join(errors)
        browser.close()
    server.shutdown()
    (OUT/'results.json').write_text(json.dumps({'passed':results,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS: '+str(len(results))+' groups of browser checks; no unexpected console or HTTP errors.')

if __name__=='__main__':run()
