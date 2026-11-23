"""Exercise password-gated albums: encrypted page, encrypted image files, in-browser decryption."""
from pathlib import Path
import functools
import http.server
import json
import os
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/python'))
from playwright.sync_api import sync_playwright, expect
import re
from album_access import password_for, has_password
from test_browser import QuietHandler, check_masonry
from build import variant_key


def run():
    albums = json.loads((ROOT / 'data/albums.json').read_text(encoding='utf-8'))
    album = next(album for album in albums if album['id'] == 'noel')
    password = password_for('noel')
    source = (ROOT / 'albums/noel.html').read_text(encoding='utf-8')
    assert password not in source
    assert 'class="photo-link"' not in source, 'Gallery markup must be unavailable before unlocking'
    assert 'album-encrypted-data' in source
    covers = {a['cover'] for a in albums}
    shared = covers | {src for a in albums if not a.get('password_protected') for src in a['photos']}
    for protected in (a for a in albums if a.get('password_protected') and has_password(a['id'])):
        page_source = (ROOT / f'albums/{protected["id"]}.html').read_text(encoding='utf-8')
        assert password_for(protected['id']) not in page_source
        for src in protected['photos']:
            if src in shared:
                continue
            readable = list((ROOT / 'images/optimized').glob(variant_key(src) + '-*.webp'))
            assert not readable, f'Readable export published for a protected photograph: {readable[0].name}'
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
        functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/'
    out = ROOT / 'test-results/album-access'
    out.mkdir(exist_ok=True)
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get('CHROME_PATH',
                r'C:\Program Files\Google\Chrome\Application\chrome.exe'))
            for width in [320, 390, 1440]:
                context = browser.new_context(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
                context.route('https://**/*', lambda route: route.abort())
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                posts = []
                page.on('request', lambda request: posts.append(request.url) if request.method == 'POST' else None)
                page.goto(base + 'concerts/index.html#reportages')
                locked = page.locator('.collection-link[href="../albums/noel.html"]')
                expect(locked.locator('.album-lock')).to_have_count(1)
                expect(page.locator('.collection-link[href="../albums/concertsinfonia.html"] .album-lock')).to_have_count(0)
                if width in [390, 1440]:
                    locked.locator('img').evaluate('(img) => img.decode()')
                    locked.screenshot(path=str(out / f'locked-ticket-{width}.png'))
                locked.click()
                page.wait_for_url('**/albums/noel.html')
                dialog = page.locator('#album-access-dialog')
                expect(dialog).to_be_visible()
                expect(page.locator('#album-password')).to_be_focused()
                expect(page.locator('.photo-link')).to_have_count(0)
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                if width in [390, 1440]:
                    page.screenshot(path=str(out / f'password-dialog-{width}.png'))
                page.keyboard.press('Escape')
                expect(dialog).not_to_be_visible()
                expect(page.locator('#album-access-open')).to_be_focused()
                page.locator('#album-access-open').click()
                page.locator('#album-password').fill('incorrect-test-password')
                page.locator('#album-access-form [type=submit]').click()
                expect(page.locator('#album-access-status')).to_contain_text('incorrect')
                expect(page.locator('.photo-link')).to_have_count(0)
                page.locator('#album-password').fill(password)
                page.keyboard.press('Enter')
                expect(page.locator('.photo-link')).to_have_count(len(album['photos']))
                encrypted_image = page.locator('.photo-link').nth(1).get_attribute('href')
                assert encrypted_image.endswith('.bin'), 'Album photographs must be published encrypted'
                expect(page.locator('#contenu')).to_have_attribute('data-album-ready', 'true')
                expect(page.locator('#contenu')).not_to_have_attribute('data-image-key', re.compile('.'))
                check_masonry(page, width)
                page.wait_for_function('''() => { const image = document.querySelectorAll(".photo-link img")[1];
                    return image.src.startsWith("blob:") && image.complete && image.naturalWidth > 1; }''')
                page.wait_for_function('document.querySelector("#lightbox .lightbox-close") !== null')
                page.locator('.photo-link').nth(1).click()
                expect(page.locator('#lightbox')).to_be_visible()
                page.wait_for_function('''() => { const image = document.querySelector("#lightbox img");
                    return !image.hidden && image.src.startsWith("blob:") && image.naturalWidth > 1; }''')
                page.keyboard.press('ArrowLeft')
                page.keyboard.press('ArrowRight')
                expect(page.locator('#photo-counter')).to_have_text(f'2 / {len(album["photos"])}')
                page.keyboard.press('Escape')
                expect(page.locator('#lightbox')).not_to_be_visible()
                page.locator('.photo-link').last.scroll_into_view_if_needed()
                expect(page.locator('.back-to-top')).to_be_visible()
                page.locator('.back-to-top').click()
                expect(page.locator('#contenu')).to_be_focused()
                assert password not in page.url
                assert not posts, 'Passwords must never be submitted to a server'
                page.reload()
                expect(page.locator('#album-access-dialog')).to_be_visible()
                expect(page.locator('.photo-link')).to_have_count(0)
                page.goto(base + 'albums/concertsinfonia.html')
                expect(page.locator('.photo-link')).to_have_count(38)
                expect(page.locator('#album-access-dialog')).to_have_count(0)
                response = page.request.get(base + 'albums/' + encrypted_image)
                assert response.ok
                assert response.body()[:4] != b'RIFF' and b'WEBP' not in response.body()[:16], 'Published album images must not be readable'
                context.close()
                print(f'PASS {width}px: lock badge, dialog, wrong/correct password, gallery, decrypted thumbnails and viewer, reload, unreadable image files', flush=True)
            fallback = browser.new_context(java_script_enabled=False)
            page = fallback.new_page()
            page.goto(base + 'albums/noel.html')
            expect(page.locator('.photo-link')).to_have_count(0)
            expect(page.locator('.album-access-note')).to_contain_text('Activez JavaScript')
            expect(page.locator('.album-access-note')).to_be_visible()
            expect(page.locator('#album-access-form [type=submit]')).to_be_disabled()
            fallback.close()
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print('PASS: password absent from published HTML; gallery remains locked without JavaScript; no unexpected browser errors')


if __name__ == '__main__':
    run()
