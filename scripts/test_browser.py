"""Real-browser regressions. All Formspree requests are mocked; no message is sent."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/python'))
import os, json, http.server, functools, threading, hashlib, io, re
from PIL import Image
from playwright.sync_api import sync_playwright, expect
from album_access import password_for

OUT = ROOT / 'test-results'
OUT.mkdir(exist_ok=True)
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        try: super().do_GET()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError): pass

def contrast_ratio(first, second):
    def luminance(rgb):
        values = [v/255 for v in rgb[:3]]
        values = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in values]
        return sum(v*w for v,w in zip(values, [.2126,.7152,.0722]))
    light,dark = sorted([luminance(first),luminance(second)], reverse=True)
    return (light+.05)/(dark+.05)

def unlock_album(page):
    payload = page.locator('#album-encrypted-data')
    if not payload.count():
        return
    album_id = payload.evaluate('(el) => JSON.parse(el.textContent).id')
    page.locator('#album-password').fill(password_for(album_id))
    page.locator('#album-access-form [type=submit]').click()
    expect(page.locator('.photo-grid')).to_be_visible()
    expect(page.locator('#contenu')).to_have_attribute('data-album-ready', 'true')


def check_masonry(page, viewport_width):
    grid = page.locator('.photo-grid')
    expect(grid).to_have_class(re.compile(r'\bis-masonry\b'))
    expected_columns = 2 if viewport_width <= 760 else 3
    geometry = grid.evaluate('''grid => {
        const bounds = grid.getBoundingClientRect();
        return {width: bounds.width, height: bounds.height,
            gap: parseFloat(getComputedStyle(grid).getPropertyValue('--gallery-gap')),
            photos: Array.from(grid.children).map(item => {
                const box = item.getBoundingClientRect();
                const image = item.querySelector('img');
                const photo = image.getBoundingClientRect();
                return {x:box.left-bounds.left, y:box.top-bounds.top,
                    width:box.width, height:box.height,
                    imageWidth:photo.width, imageHeight:photo.height,
                    ratio:Number(image.getAttribute('width'))/Number(image.getAttribute('height'))};
            })};
    }''')
    columns = sorted({round(photo['x'], 2) for photo in geometry['photos']})
    assert len(columns) == expected_columns, (viewport_width, columns)
    previous_bottom = {}
    previous_top = -1
    for photo in geometry['photos']:
        column = round(photo['x'], 2)
        assert photo['width'] > 0 and photo['x'] >= -.1
        assert photo['x'] + photo['width'] <= geometry['width'] + 1
        assert photo['y'] >= previous_top - .1, 'Masonry must preserve top-to-bottom publication order'
        expected_top = previous_bottom.get(column, -geometry['gap']) + geometry['gap']
        assert abs(photo['y'] - expected_top) <= 1.5, 'No overlapping photos or empty row-sized gaps'
        assert abs(photo['imageHeight'] - photo['imageWidth'] / photo['ratio']) <= 1.5, 'Keep complete photo proportions'
        previous_bottom[column] = photo['y'] + photo['height']
        previous_top = photo['y']
    assert abs(max(previous_bottom.values()) - geometry['height']) <= 1.5, 'Reserve the full gallery height before the footer'

def check_french_heading_font(page):
    # Check the font that actually draws each glyph, rather than only CSS's
    # requested family: missing accents can silently fall back to Georgia.
    sample = 'Cérémonie Événements Baptême Fiançailles À bientôt Noël cœur Œuvre Ça ù ï ÿ Æ æ 1 000 €'
    cdp = page.context.new_cdp_session(page)
    cdp.send('DOM.enable')
    cdp.send('CSS.enable')
    try:
        for style in ['normal', 'italic']:
            page.evaluate('''({sample, style}) => {
                let probe = document.getElementById('french-font-probe');
                if (!probe) {
                    probe = document.createElement('h2');
                    probe.id = 'french-font-probe';
                    probe.style.position = 'fixed';
                    probe.style.left = '-10000px';
                    document.querySelector('main').appendChild(probe);
                }
                probe.textContent = sample;
                probe.style.fontStyle = style;
                probe.getBoundingClientRect();
            }''', {'sample': sample, 'style': style})
            page.evaluate('document.fonts.ready')
            document = cdp.send('DOM.getDocument')['root']['nodeId']
            node = cdp.send('DOM.querySelector', {'nodeId': document, 'selector': '#french-font-probe'})['nodeId']
            fonts = cdp.send('CSS.getPlatformFontsForNode', {'nodeId': node})['fonts']
            assert fonts and all(font['isCustomFont'] and 'Cormorant Garamond' in font['familyName']
                                 for font in fonts if font['glyphCount']), (style, fonts)
    finally:
        page.evaluate('document.getElementById("french-font-probe")?.remove()')
        cdp.detach()


def run():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    albums = json.loads((ROOT / 'data/albums.json').read_text(encoding='utf-8'))
    rugby_photos = next(a['photos'] for a in albums if a['id'] == 'co_mhr')
    rugby_count = len(rugby_photos)
    portrait_digest = hashlib.sha256((ROOT / 'images/portrait.jpg').read_bytes()).hexdigest()[:12]
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
        paths = ['index.html','rugby/index.html','rugby/contact.html','rugby/a-propos.html','rugby/tarifs.html','instants-de-vie/index.html','instants-de-vie/a-propos.html','instants-de-vie/prestations.html','instants-de-vie/contact.html','concerts/index.html','concerts/tarifs.html','concerts/contact.html','regards/index.html','regards/tirages.html','a-propos.html','contact.html','mentions.html','404.html'] + [f'albums/{a["id"]}.html' for a in albums]
        check_paths = ['index.html', 'regards/index.html', 'instants-de-vie/index.html', 'instants-de-vie/a-propos.html', 'instants-de-vie/prestations.html'] if '--interactions-only' in sys.argv else paths
        for width in [320, 390, 768, 1440]:
            page.set_viewport_size({'width': width, 'height': 900})
            for path in check_paths:
                page.goto(base + '/' + path, wait_until='networkidle')
                overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                if overflow:
                    print(page.evaluate('Array.from(document.querySelectorAll("body *")).filter(el => { const b=el.getBoundingClientRect(); return b.width && b.right > innerWidth + 1; }).slice(0,12).map(el => ({tag:el.tagName,css:el.className,width:el.getBoundingClientRect().width,right:el.getBoundingClientRect().right}))'), flush=True)
                    page.screenshot(path=str(OUT / f'overflow-{width}.png'), full_page=True)
                assert not overflow, f'Horizontal overflow: {path} at {width}px'
                expect(page.locator('h1')).to_have_count(1)
                if path.startswith('albums/'):
                    unlock_album(page)
                    check_masonry(page, width)
                if path == 'instants-de-vie/index.html':
                    for photo in page.locator('.life-stories img, #presentation img').all():
                        photo.scroll_into_view_if_needed()
                        page.wait_for_function('(image) => image.complete && image.naturalWidth > 0', arg=photo.element_handle())
                        assert photo.evaluate('(image) => Math.abs(image.clientWidth / image.clientHeight - image.naturalWidth / image.naturalHeight) < .025'), 'Wedding images must preserve their complete framing'
                    hero = page.locator('.life-hero')
                    assert hero.locator('img').count() == 1, 'The wedding opening uses one full-screen photograph'
                    hero_box = hero.bounding_box()
                    assert abs(hero_box['width'] - width) < 1, 'Wedding cover spans the viewport width'
                    assert abs(hero_box['height'] - 900) <= 2, 'Wedding cover fills the viewport behind navigation'
                    page.evaluate('scrollTo(0, 0)')
                    nav = page.locator('.site-nav')
                    expect(nav).not_to_have_class(re.compile(r'\bscrolled\b'))
                    assert nav.evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgba(0, 0, 0, 0)', 'Wedding navigation starts transparent'
                    page.evaluate('scrollTo(0, 150)')
                    expect(nav).to_have_class(re.compile(r'\bscrolled\b'))
                    assert nav.evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(247, 245, 240)', 'Wedding navigation becomes opaque on scroll'
                    for story in page.locator('.life-stories .collection-link').all():
                        assert story.locator('img').count() == 1, 'Each wedding reportage has a single cover photograph'
                        heading = story.locator('h3').bounding_box()
                        cover = story.locator('.collection-image').bounding_box()
                        assert heading['y'] + heading['height'] <= cover['y'], 'The wedding title belongs above its photographs'
                    page.evaluate('scrollTo(0, 0)')
                if path == 'instants-de-vie/prestations.html':
                    expect(page.locator('.life-price-row')).to_have_count(3)
                    expect(page.locator('#bapteme img')).to_have_count(2)
                    expect(page.locator('.life-faq, .booking-process')).to_have_count(0)
                    for photo in page.locator('#bapteme img').all():
                        photo.scroll_into_view_if_needed()
                        page.wait_for_function('(image) => image.complete && image.naturalWidth > 0', arg=photo.element_handle())
                        assert photo.evaluate('(image) => Math.abs(image.clientWidth / image.clientHeight - image.naturalWidth / image.naturalHeight) < .025')
                    if width >= 1000:
                        boxes = [card.bounding_box() for card in page.locator('.life-price-row').all()]
                        assert max(box['y'] for box in boxes) - min(box['y'] for box in boxes) <= 1
                    page.evaluate('scrollTo(0, 0)')
                if path == 'regards/index.html':
                    expect(page.locator('h1')).to_have_class('sr-only')
                    expect(page.locator('.art-series-work')).to_have_count(3)
                    expect(page.locator('.art-work')).to_have_count(8)
                    expect(page.locator('.art-slide:visible')).to_have_count(1)
                    assert page.evaluate('document.documentElement.scrollHeight <= innerHeight + 1')
                    # Check every slide: individual photographs also use the
                    # shared gallery styles, which must not override this frame.
                    for _ in range(page.locator('.art-slide').count()):
                        photo = page.locator('.art-slide:visible img')
                        page.wait_for_function('(image) => image.complete && image.naturalWidth > 0', arg=photo.element_handle())
                        assert photo.evaluate('(image) => getComputedStyle(image).objectFit') == 'contain'
                        box=photo.bounding_box()
                        frame=page.locator('.art-slide:visible .art-image-link').bounding_box()
                        assert abs(box['height'] - frame['height']) <= 1, 'Photograph must stay within the slide frame'
                        assert abs(box['width'] - frame['width']) <= 1, 'Photograph must fit the slide width'
                        assert box['y']>=page.locator('.art-navigation').bounding_box()['height']
                        assert box['y']+box['height']<=900
                        if width in [390, 1440] and page.locator('.art-slide:visible').get_attribute('data-kind') == 'photo':
                            number=page.locator('.art-slide:visible').get_attribute('data-title').split()[-1]
                            page.screenshot(path=str(OUT / f'regards-photo-{number}-{width}.png'))
                        page.locator('.art-next').click()
                if path == 'concerts/index.html':
                    expect(page.locator('h1')).to_have_css('font-weight', '400')
                    expect(page.locator('.concert-cover img')).to_have_css('filter', 'none')
                    expect(page.locator('.concert-cover')).to_have_css('animation-name', 'none')
                    expect(page.locator('#presentation .personal-portrait img')).to_have_count(1)
                    for photo in page.locator('.concert-cover img, .concert-reportages img').all():
                        assert photo.bounding_box()['width'] <= int(photo.get_attribute('width')) + 1, 'Concert photographs must not be stretched beyond their source width'
                        assert '../images/concert/' in photo.get_attribute('srcset'), 'Large concert images must offer their source file'
                    cards = page.locator('.concert-reportages .collection-link')
                    if cards.count() > 1:
                        first, second = cards.nth(0).bounding_box(), cards.nth(1).bounding_box()
                        assert second['y'] >= first['y'] + first['height'], 'Concert reportages must follow one another vertically'
                if width in [390, 1440] and path in ['index.html', 'rugby/index.html', 'instants-de-vie/index.html', 'concerts/index.html']:
                    # Load the below-the-fold selection before making the review artifact.
                    for photo in page.locator('.universe-door img, .life-hero-image img, .life-stories img, #presentation img, .concert-reportages img').all():
                        photo.scroll_into_view_if_needed()
                        page.wait_for_function('(image) => image.complete && image.naturalWidth > 0', arg=photo.element_handle())
                    if path in ['rugby/index.html', 'instants-de-vie/index.html', 'concerts/index.html']:
                        page.locator('#presentation').screenshot(path=str(OUT / f'{path.split("/")[0]}-presentation-{width}.png'))
                    page.evaluate('scrollTo(0, 0)')
                if width in [390, 1440] and path in ['index.html','contact.html']:
                    page.screenshot(path=str(OUT / f'{path[:-5]}-{width}.png'), full_page=True)
                    if path == 'index.html':
                        page.screenshot(path=str(OUT / f'cover-{width}.png'))
                if width in [390, 1440] and path == 'rugby/index.html':
                    page.screenshot(path=str(OUT / f'rugby-{width}.png'), full_page=True)
                if width in [390, 1440] and path in ['instants-de-vie/index.html', 'concerts/index.html', 'regards/index.html']:
                    page.screenshot(path=str(OUT / f'{path.split("/")[0]}-{width}.png'), full_page=not path.startswith('regards/'))
                if width in [390, 1440] and path in ['rugby/a-propos.html','instants-de-vie/a-propos.html','instants-de-vie/prestations.html','instants-de-vie/contact.html']:
                    page.screenshot(path=str(OUT / f'{path[:-5].replace("/", "-")}-{width}.png'), full_page=True)
                if width in [390, 1440] and path.endswith('/tarifs.html'):
                    page.screenshot(path=str(OUT / f'{path[:-5].replace("/", "-")}-{width}.png'), full_page=True)
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
        # The portal keeps its hamburger menu on desktop as well as mobile.
        expect(menu).to_be_visible()
        expect(menu).to_have_attribute('aria-expanded', 'false')
        assert page.locator('#navigation').evaluate('(el) => el.inert')
        menu.click()
        expect(menu).to_have_attribute('aria-expanded', 'true')
        assert not page.locator('#navigation').evaluate('(el) => el.inert')
        page.keyboard.press('Escape')
        expect(menu).to_be_focused()
        page.goto(base + '/rugby/index.html')
        expect(page.locator('.menu-toggle')).to_be_hidden()
        expect(page.locator('#navigation')).to_be_visible()
        assert not page.locator('#navigation').evaluate('(el) => el.inert')
        results.append('Menus: mobile keyboard/focus, desktop portal toggle and desktop universe navigation')

        page.goto(base + '/index.html')
        hero = page.locator('.portal-hero')
        assert abs(hero.bounding_box()['height'] - 900) < 1
        expect(hero.locator('h1')).to_have_text('Thomas Soleil')
        expect(hero.locator('.portal-hero-copy p').first).to_have_text('Photographe')
        expect(hero.locator('.portal-location')).to_have_text('Toulouse & Castres')
        assert 'hero-photo-accueil_2.webp' in hero.evaluate('(el) => getComputedStyle(el).backgroundImage')
        assert 'gradient' not in hero.evaluate('(el) => getComputedStyle(el).backgroundImage')
        assert hero.evaluate('(el) => getComputedStyle(el).filter') == 'none'
        expect(page.locator('.site-nav img')).to_have_count(1)
        assert page.locator('body').evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(0, 0, 0)'
        expect(page.locator('#presentation')).to_have_count(0)
        page.locator('.portal-hero-discover').click()
        expect(page.locator('.universe-door')).to_have_count(4)
        destinations = [door.get_attribute('href') for door in page.locator('.universe-door').all()]
        assert len(set(destinations)) == 4
        for door in page.locator('.universe-door').all():
            href = door.get_attribute('href')
            assert page.request.get(base + '/' + href.split('#')[0]).ok, href
        page.locator('.door-sport').click()
        page.wait_for_url('**/rugby/index.html')
        expect(page.locator('body')).to_have_class('rugby-page')
        hero_photo = page.locator('.rugby-hero>img')
        assert hero_photo.bounding_box()['width'] <= int(hero_photo.get_attribute('width')) + 1
        expect(page.locator('.rugby-reportage')).to_have_count(sum(a['category'] == 'Rugby' for a in albums))
        page.locator('.rugby-reportage').first.click()
        page.wait_for_url('**/albums/co_mhr.html')
        expect(page.locator('body')).to_have_class('rugby-page')
        page.locator('.gallery-end .button').click()
        page.wait_for_url('**/rugby/contact.html')
        expect(page.locator('body')).to_have_class('rugby-page')
        expect(page.locator('#project')).to_have_value('sport')
        expect(page.locator('#wedding-offer-group')).to_be_hidden()
        page.set_viewport_size({'width': 390, 'height': 844})
        page.locator('.menu-toggle').click()
        page.locator('#navigation a').filter(has_text='Tous les univers').click()
        page.wait_for_url('**/index.html#haut')
        assert page.evaluate('scrollY') <= 1, 'Sport return must show the top of the cover'
        results.append('Four universe links; Rugby landing, album, preset contact and return to portal')

        for door, destination, category in [('door-life', 'instants-de-vie', 'Mariage'), ('door-concert', 'concerts', 'Concerts')]:
            page.goto(base + '/index.html')
            page.locator('.' + door).click()
            page.wait_for_url('**/' + destination + '/index.html')
            expected = [a for a in albums if a['category'] == category]
            expect(page.locator('.collection-link')).to_have_count(len(expected))
            page.locator('.collection-link').first.click()
            page.wait_for_url('**/albums/' + expected[0]['id'] + '.html')
            expect(page.locator('body')).to_have_class(destination + '-page')
            page.locator('.photo-link').first.click()
            expect(page.get_by_role('dialog')).to_be_visible()
            page.keyboard.press('Escape')
            if page.locator('.menu-toggle').is_visible():
                page.locator('.menu-toggle').click()
            page.locator('#navigation a[href$="index.html#haut"]').click()
            page.wait_for_url('**/index.html#haut')
            assert page.evaluate('scrollY') <= 1, destination
        page.goto(base + '/regards/index.html')
        art_albums = [a for a in albums if a['category'] in ('Argentique', 'Autres regards') and a.get('presentation') != 'individual']
        independent_photos = [src for a in albums if a.get('presentation') == 'individual' for src in a['photos']]
        art_count = len(art_albums) + len(independent_photos)
        expect(page.locator('.art-series-work')).to_have_count(len(art_albums))
        expect(page.locator('.art-work')).to_have_count(len(independent_photos))
        expect(page.locator('.art-photo-link')).to_have_count(len(independent_photos))
        expect(page.locator('.art-feature img')).to_have_attribute('src', re.compile('argentiqueNB-15'))
        assert not page.locator('a[href$="albums/autres.html"]').count(), 'Individual photographs must not open a series'
        expect(page.locator('.art-slide:visible')).to_have_count(1)
        expect(page.locator('.art-controls')).to_be_visible()
        expect(page.locator('.art-progress')).to_have_text(f'01 / {art_count:02d}')
        expect(page.locator('.site-nav, .site-footer, .collection-caption')).to_have_count(0)
        expect(page.locator('#presentation')).to_have_count(0)
        expect(page.locator('h1')).to_have_class('sr-only')
        page.locator('.art-prev').click()
        expect(page.locator('.art-progress')).to_have_text(f'{art_count:02d} / {art_count:02d}')
        page.locator('.art-photo-link').last.click()
        expect(page.get_by_role('dialog')).to_be_visible()
        expect(page.locator('#photo-counter')).to_have_text(f'{len(independent_photos)} / {len(independent_photos)}')
        page.keyboard.press('ArrowRight')
        expect(page.locator('#photo-counter')).to_have_text(f'1 / {len(independent_photos)}')
        expect(page.locator('.art-progress')).to_have_text(f'{art_count:02d} / {art_count:02d}')
        page.keyboard.press('Escape')
        expect(page.locator('.art-photo-link').last).to_be_focused()
        page.keyboard.press('ArrowRight')
        expect(page.locator('.art-progress')).to_have_text(f'01 / {art_count:02d}')
        page.keyboard.press('ArrowRight')
        page.locator('.art-series-link').nth(1).click()
        page.wait_for_url('**/albums/' + art_albums[1]['id'] + '.html')
        expect(page.locator('body')).to_have_class('regards-page')
        expect(page.locator('.photo-link')).to_have_count(len(art_albums[1]['photos']))
        expect(page.locator('.site-nav, .site-footer, #presentation')).to_have_count(0)
        page.locator('.photo-link').first.click()
        expect(page.get_by_role('dialog')).to_be_visible()
        page.keyboard.press('Escape')
        page.locator('.art-return').click()
        page.wait_for_url('**/regards/index.html')
        page.locator('.art-return').click()
        page.wait_for_url('**/index.html#haut')
        assert page.evaluate('scrollY') <= 1, 'Artistic return must show the top of the cover'
        results.append('Personal slideshow: Couvent cover 15, one image at a time, modal keyboard/focus and series navigation')
        page.goto(base + '/regards/index.html')
        expect(page.locator('.art-playback, .art-tariffs, a[href*="tarifs"]')).to_have_count(0)
        expect(page.locator('.art-logo img')).to_have_attribute('src', '../images/logo.png')
        expect(page.locator('.art-logo')).to_have_attribute('href', '../index.html#haut')
        page.clock.install()
        page.clock.fast_forward(60000)
        expect(page.locator('.art-slide:visible .art-series-title')).to_have_text('Couvent')
        page.clock.resume()
        results.append('Artistic slideshow: manual only, original logo and no tariffs link')

        page.set_viewport_size({'width': 1440, 'height': 900})
        page.goto(base + '/concerts/index.html')
        page.locator('#navigation a').filter(has_text='À propos').click()
        page.wait_for_url('**/concerts/index.html#presentation')
        expect(page.locator('#presentation .personal-copy')).to_contain_text('Sinfonia Garonna')
        expect(page.locator('#presentation .personal-portrait img')).to_be_visible()
        assert '/portrait-' + portrait_digest + '-' in page.locator('#presentation img').get_attribute('src')
        page.locator('.concert-invitation .button').click()
        page.wait_for_url('**/concerts/contact.html')
        expect(page.locator('body')).to_have_class('concerts-page')
        expect(page.locator('#project')).to_have_value('concert')
        results.append('Concert presentation: current portrait, navigation anchor and contact preset')
        page.goto(base + '/index.html')
        for selector in ['h1', '.universe-door h2', '.nav-links a']:
            assert all(el.evaluate('(el) => getComputedStyle(el).fontWeight') == '400' for el in page.locator(selector).all()), selector
        page.goto(base + '/rugby/index.html')
        for selector in ['h1', 'h2', 'h3']:
            assert all(el.evaluate('(el) => getComputedStyle(el).fontWeight') == '900' for el in page.locator(selector).all()), selector
        page.locator('#navigation a').filter(has_text='À propos').click()
        page.wait_for_url('**/rugby/index.html#presentation')
        expect(page.locator('#presentation .personal-portrait img')).to_be_visible()
        expect(page.locator('#presentation h2')).to_contain_text('terrain')
        assert '/portrait-' + portrait_digest + '-' in page.locator('#presentation img').get_attribute('src')
        expect(page.locator('h1')).to_have_count(1)
        page.locator('.personal-actions .button').click()
        page.wait_for_url('**/rugby/contact.html')
        page.goto(base + '/instants-de-vie/index.html')
        expect(page.locator('.life-hero-image img')).to_be_visible()
        wedding_photo = page.locator('.life-hero-image img')
        assert wedding_photo.bounding_box()['width'] <= int(wedding_photo.get_attribute('width')) + 1
        page.locator('#navigation a').filter(has_text='À propos').click()
        page.wait_for_url('**/instants-de-vie/index.html#presentation')
        expect(page.locator('#presentation .personal-copy')).to_contain_text('discrétion')
        expect(page.locator('#presentation .personal-copy')).not_to_contain_text('mariage d’un ami')
        expect(page.locator('#presentation .personal-copy')).not_to_contain_text('argentique')
        expect(page.locator('#presentation .personal-portrait img')).to_be_visible()
        assert '/portrait-' + portrait_digest + '-' in page.locator('#presentation img').get_attribute('src')
        expect(page.locator('h1')).to_have_count(1)
        page.locator('#navigation a').filter(has_text='Tarifs').click()
        page.wait_for_url('**/instants-de-vie/prestations.html')
        check_french_heading_font(page)
        results.append('French title accents and italic use the local font without character fallback')
        expect(page.locator('.life-price')).to_have_text(['600 €', '850 €', '1 000 €'])
        for project in ['bapteme', 'fiancailles', 'couple', 'famille', 'evenement']:
            page.goto(base + '/instants-de-vie/prestations.html')
            page.locator('.life-services-page a[href$="projet=' + project + '"]').click()
            page.wait_for_url('**/instants-de-vie/contact.html?projet=' + project)
            expect(page.locator('#project')).to_have_value(project)
            expect(page.locator('#wedding-offer-group')).to_be_hidden()
        for index, offer in enumerate(['ceremonie', 'cocktail', 'complet']):
            page.goto(base + '/instants-de-vie/prestations.html')
            page.locator('.life-price-row').nth(index).locator('a').click()
            page.wait_for_url('**/instants-de-vie/contact.html?projet=mariage&offre=' + offer)
            expect(page.locator('#project')).to_have_value('mariage')
            expect(page.locator('#wedding-offer')).to_have_value(offer)
            expect(page.locator('#wedding-offer-group')).to_be_visible()
        expect(page.locator('body')).to_have_class('instants-de-vie-page')
        results.append('Regular portal and bold Sport; inline presentations with current portrait; Wedding prices and contact presets')

        for universe, contact_path, project in [('rugby', '/rugby/contact.html', 'sport'), ('concerts', '/concerts/contact.html', 'concert')]:
            page.goto(base + '/' + universe + '/index.html')
            link = page.locator('#navigation a').filter(has_text='Tarifs')
            link.click()
            page.wait_for_url('**/' + universe + '/tarifs.html')
            if universe == 'rugby':
                expect(page.locator('.rugby-pricing-intro')).to_contain_text('sur devis')
                expect(page.locator('.rugby-pricing-card')).to_have_count(3)
                expect(page.locator('main a[href="contact.html"]')).to_have_count(1)
                expect(page.locator('.booking-process')).to_have_count(0)
                request_link = page.locator('.rugby-pricing-summary .button')
            else:
                expect(page.locator('.tariff-quote')).to_have_text('Sur devis')
                request_link = page.locator('.tariff-feature .button')
            assert '600' not in page.locator('main').inner_text(), universe
            request_link.click()
            page.wait_for_url('**' + contact_path)
            expect(page.locator('#project')).to_have_value(project)
        results.append('Separate Sport and Concert prices; contextual contact links')

        for album in albums:
            page.goto(base + '/albums/' + album['id'] + '.html')
            unlock_album(page)
            expect(page.locator('.photo-link')).to_have_count(len(album['photos']))
            expect(page.locator('.gallery-description')).to_have_text(album['description'])
            links = page.locator('.photo-link').evaluate_all('(links)=>links.map(link=>decodeURI(new URL(link.href).pathname.slice(1)))')
            assert links == album['photos'], 'The original photo selection and order must be preserved'
            schema = page.locator('script[type="application/ld+json"]').text_content()
            assert any(node['@type'] == 'CollectionPage' for node in json.loads(schema)['@graph'])
            check_masonry(page, page.viewport_size['width'])
        for width in [320, 1440, 768, 390]:
            page.set_viewport_size({'width':width, 'height':844})
            page.wait_for_function('(columns) => getComputedStyle(document.querySelector(".photo-grid")).getPropertyValue("--gallery-columns").trim() === String(columns)', arg=2 if width <= 760 else 3)
            # Layout is scheduled in an animation frame after ResizeObserver.
            page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
            check_masonry(page, width)
        results.append('Albums: selected photo order, descriptions, structured data and Masonry without gaps or overlaps across resizing')
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

        # Saving deterrents must not break the viewer or ordinary text/form menus.
        for path in ['index.html', 'a-propos.html', 'regards/index.html', 'albums/Argentique.html']:
            page.goto(base + '/' + path)
            photo = page.locator('main img').first
            expect(photo).to_have_attribute('draggable', 'false')
            for event_name in ['contextmenu', 'dragstart']:
                assert photo.evaluate('(el, name) => !el.dispatchEvent(new MouseEvent(name, {bubbles:true, cancelable:true}))', event_name), (path, event_name)
            expect(photo).to_have_css('user-select', 'none')
            assert page.locator('h1').evaluate('(el) => el.dispatchEvent(new MouseEvent("contextmenu", {bubbles:true, cancelable:true}))'), path
            expect(page.locator('#photo-original')).to_have_count(0)
        first = page.locator('.photo-link').first
        first.click(modifiers=['Control'])
        expect(page.get_by_role('dialog')).to_be_visible()
        expect(page.locator('#lightbox img')).to_be_visible()
        assert page.locator('#lightbox img').evaluate('(el) => !el.dispatchEvent(new MouseEvent("contextmenu", {bubbles:true, cancelable:true}))')
        page.keyboard.press('ArrowRight')
        expect(page.locator('#photo-counter')).to_have_text('2 / 10')
        page.keyboard.press('Escape')
        expect(first).to_be_focused()
        assert first.evaluate('(el) => !el.dispatchEvent(new MouseEvent("auxclick", {bubbles:true, cancelable:true, button:1}))')
        results.append('Photo saving deterrents: image menus/dragging, no original button, modified clicks and working viewer')

        # Load failure stays recoverable and does not close or trap the gallery.
        page.goto(base + '/albums/co_mhr.html')
        failed_paths = [part.strip().split()[0].removeprefix('../') for part in page.locator('.photo-link').first.get_attribute('data-viewer-srcset').split(',')]
        for path in failed_paths:
            page.route('**/'+path, lambda route: route.fulfill(status=404,body='not available'))
        page.goto(base + '/albums/co_mhr.html')
        page.locator('.photo-link').first.click()
        expect(page.locator('#photo-status')).to_contain_text('ne peut pas être chargée')
        page.keyboard.press('ArrowRight')
        expect(page.locator('#lightbox img')).to_be_visible()
        page.keyboard.press('Escape')
        for path in failed_paths: page.unroute('**/'+path)
        # Remove only the deliberately simulated error.
        errors[:] = [err for err in errors if not any('/'+path in err for path in failed_paths)]
        results.append('Gallery photo-load failure remains recoverable')

        page.goto(base + '/contact.html?projet=mariage')
        expect(page.locator('#project')).to_have_value('mariage')
        assert page.locator('#message').evaluate('(el) => el.dispatchEvent(new MouseEvent("contextmenu", {bubbles:true, cancelable:true}))')
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
        expect(page.locator('#project')).to_have_value('mariage')
        results.append('Form: project preset, mocked failure/success, preserved message, duplicate prevention')

        held.clear()
        page.locator('#name').fill('Test de modification')
        page.locator('#email').fill('test@example.invalid')
        page.locator('#message').fill('Message envoyé')
        page.get_by_role('button',name='Envoyer ma demande').click()
        expect(page.get_by_role('button',name='Envoi en cours…')).to_be_disabled()
        page.locator('#message').fill('Nouveau texte pendant l’envoi')
        page.wait_for_function('document.querySelector("#contact-form").getAttribute("aria-busy") === "true"')
        assert len(held) == 1
        held[0].fulfill(status=200,headers={'Access-Control-Allow-Origin':'*'},content_type='application/json',body='{"ok":true}')
        expect(page.locator('#form-status')).to_contain_text('Vos modifications récentes sont conservées')
        expect(page.locator('#message')).to_have_value('Nouveau texte pendant l’envoi')
        expect(page.locator('#message')).to_be_focused()
        results.append('Form: preserve edits and input focus while a submitted request completes')

        page.set_viewport_size({'width':390,'height':320})
        for path in ['rugby/index.html','instants-de-vie/index.html','concerts/index.html','contact.html']:
            page.goto(base + '/' + path)
            page.locator('.menu-toggle').click()
            menu = page.locator('#navigation')
            menu_box = menu.bounding_box()
            assert menu_box['y'] + menu_box['height'] <= 320, f'Mobile menu leaves the viewport: {path}'
            last = menu.locator('a').last
            last.scroll_into_view_if_needed()
            last_box = last.bounding_box()
            assert last_box['y'] >= menu_box['y'] and last_box['y'] + last_box['height'] <= 320, path
            assert abs(last_box['x'] - menu.locator('a').first.bounding_box()['x']) < 1, 'Mobile links stay in one scrollable column'
            page.keyboard.press('Escape')
            expect(menu).to_be_hidden()
        results.append('Short mobile screens: every navigation link remains reachable')

        nojs=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
        nojs.route('https://**/*',lambda route:route.abort())
        fallback=nojs.new_page()
        fallback.goto(base+'/regards/index.html')
        expect(fallback.locator('.art-series-work:visible, .art-work:visible')).to_have_count(art_count)
        expect(fallback.locator('.art-controls')).to_be_hidden()
        fallback.locator('.art-series-link').first.click()
        expect(fallback.locator('.photo-link')).to_have_count(len(art_albums[0]['photos']))
        expect(fallback.locator('.photo-grid')).to_have_css('display', 'grid')
        expect(fallback.locator('.photo-grid')).not_to_have_class(re.compile(r'\bis-masonry\b'))
        fallback.goto(base+'/albums/co_mhr.html')
        expect(fallback.locator('.photo-link')).to_have_count(rugby_count)
        expect(fallback.locator('#navigation a').first).to_be_visible()
        fallback.goto(base+'/contact.html')
        expect(fallback.locator('form')).to_have_attribute('method','POST')
        results.append('Without JavaScript: album links, navigation and native form fallback')
        page.set_viewport_size({'width':390,'height':844})
        page.goto(base+'/index.html',wait_until='networkidle')
        bar = page.locator('.menu-toggle span').first
        bar_box = bar.bounding_box()
        bar_color = tuple(map(int,re.findall(r'\d+',bar.evaluate('(el)=>getComputedStyle(el).backgroundColor'))[:3]))
        pixels = Image.open(io.BytesIO(page.screenshot())).convert('RGB')
        background = pixels.getpixel((int(bar_box['x'])-3,int(bar_box['y'])))
        assert contrast_ratio(bar_color,background) >= 3, 'Homepage menu lacks contrast over the cover'
        expect(page.locator('.menu-toggle')).to_have_accessible_name('Ouvrir le menu')
        for path in ['index.html','instants-de-vie/index.html','concerts/index.html']:
            page.goto(base+'/'+path)
            for element in page.locator('.kicker, .life-specialties, .site-footer a, .nav-links a').all():
                assert element.evaluate('(el)=>parseFloat(getComputedStyle(el).fontSize)') >= 12
        for path in ['rugby/tarifs.html','concerts/tarifs.html','instants-de-vie/prestations.html']:
            page.goto(base+'/'+path)
            if path == 'instants-de-vie/prestations.html':
                expect(page.locator('.life-offer-notes')).to_contain_text('Déplacements : à votre charge')
            elif path == 'rugby/tarifs.html':
                expect(page.locator('.rugby-pricing-note')).to_contain_text('Frais de déplacement à votre charge')
            else:
                expect(page.locator('.booking-process')).to_contain_text('Les frais de déplacement sont à votre charge')
        page.goto(base+'/albums/co_mhr.html')
        page.locator('.photo-link').last.scroll_into_view_if_needed()
        expect(page.locator('.back-to-top')).to_be_visible()
        page.locator('.back-to-top').click()
        expect(page.locator('main')).to_be_focused()
        results.append('Audit regressions: menu contrast, readable secondary copy, travel terms and keyboard return to top')
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
    (OUT/'results.json').write_text(json.dumps({'status':'passed','passed':results,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS: '+str(len(results))+' groups of browser checks; no unexpected console or HTTP errors.')

if __name__=='__main__':
    report = OUT / 'results.json'
    report.write_text(json.dumps({'status':'running'}), encoding='utf-8')
    try:
        run()
    except Exception as error:
        # Do not leave an earlier successful report behind after a failed run.
        report.write_text(json.dumps({'status':'failed','error':str(error)},ensure_ascii=False,indent=2),encoding='utf-8')
        raise
