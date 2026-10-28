"""Check the theatre entrance, motion preference and navigation in a real browser."""
from pathlib import Path
import functools
import http.server
import os
import re
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/python'))
from playwright.sync_api import sync_playwright, expect
from test_browser import QuietHandler


def run():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
        functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/concerts/index.html'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get('CHROME_PATH',
                r'C:\Program Files\Google\Chrome\Application\chrome.exe'))
            for width in [390, 1440]:
                context = browser.new_context(viewport={'width': width, 'height': 900},
                                              reduced_motion='no-preference')
                context.route('https://**/*', lambda route: route.abort())
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(url)
                stage = page.locator('[data-theatre]')
                nav = page.locator('.site-nav')
                drape = nav.locator('.theatre-nav-drape')
                expect(nav).to_have_css('background-color', 'rgba(0, 0, 0, 0)')
                expect(drape).to_have_attribute('aria-hidden', 'true')
                expect(drape).to_be_visible()
                expect(drape).to_have_css('opacity', '1')
                expect(page.locator('.theatre-valance')).to_have_count(0)
                drape_box = drape.bounding_box()
                nav_box = nav.bounding_box()
                assert abs(drape_box['y']) < 1, 'The navigation is the upper curtain'
                assert 10 <= drape_box['height'] - nav_box['height'] <= 40, 'The velvet hem extends below the menu'
                assert abs(stage.bounding_box()['y']) < 1, 'The scene starts behind the velvet menu'
                expect(stage).to_have_class(re.compile(r'\btheatre-ready\b'))
                expect(stage).to_have_class(re.compile(r'\btheatre-closed\b'))
                expect(page.locator('.theatre-enter')).to_be_visible()
                assert stage.locator('.concert-stage-content').evaluate('(el) => el.inert')
                curtains = page.locator('.theatre-curtain').all()
                closed_clips = []
                for curtain in curtains:
                    assert abs(curtain.evaluate('(el) => new DOMMatrix(getComputedStyle(el).transform).m11') - 1) < .01
                    assert curtain.evaluate('(el) => el.getAnimations().length') == 0, 'No automatic entrance'
                    closed_clips.append(curtain.evaluate('(el) => getComputedStyle(el).clipPath'))
                page.locator('.theatre-enter').click()
                page.evaluate('''document.querySelectorAll('.theatre-curtain').forEach(curtain => {
                    curtain.getAnimations().forEach(animation => {
                        animation.pause();
                        animation.currentTime = Number(animation.effect.getTiming().duration) * .45;
                    });
                })''')
                for curtain, closed_clip in zip(curtains, closed_clips):
                    assert curtain.evaluate('''(el) => {
                        const style = getComputedStyle(el);
                        const gathered = parseFloat(style.getPropertyValue('--curtain-gather'));
                        const scale = new DOMMatrix(style.transform).m11;
                        return scale > gathered && scale < 1;
                    }'''), 'Opening fabric should gather gradually rather than slide as a panel'
                    assert curtain.evaluate('(el) => getComputedStyle(el).clipPath') != closed_clip, 'The moving inner edge should bow as the fabric gathers'
                page.evaluate('''document.querySelectorAll('.theatre-curtain').forEach(curtain => {
                    curtain.getAnimations().forEach(animation => animation.play());
                })''')
                expect(stage).to_have_class(re.compile(r'\bis-open\b'))
                for curtain in curtains:
                    curtain_width = curtain.bounding_box()['width']
                    assert 16 <= curtain_width <= width * .12, 'Gathered curtains remain visible at the sides without hiding the scene'
                page.locator('.theatre-replay').click()
                expect(stage).not_to_have_class(re.compile(r'\bis-open\b'))
                expect(page.locator('.theatre-replay')).to_be_disabled()
                # Both curtains must fully close before reopening, even on a fast device.
                page.evaluate('''document.querySelectorAll('.theatre-curtain').forEach(curtain => {
                    curtain.getAnimations().forEach(animation => {
                        animation.pause();
                        animation.currentTime = 1200;
                    });
                })''')
                for curtain in curtains:
                    assert abs(curtain.evaluate('(el) => new DOMMatrix(getComputedStyle(el).transform).m11') - 1) < .01, 'Replay must fully close both curtains before reopening'
                page.evaluate('''document.querySelectorAll('.theatre-curtain').forEach(curtain => {
                    curtain.getAnimations().forEach(animation => animation.finish());
                })''')
                expect(stage).to_have_class(re.compile(r'\bis-open\b'))
                expect(page.locator('.theatre-replay')).to_be_enabled()
                assert stage.bounding_box()['height'] <= 901, 'The entire opening fits the viewport'
                previous_bottom = drape.bounding_box()['y'] + drape.bounding_box()['height']
                for selector in ['.concert-title-row', '.concert-cover', '.concert-opening-actions']:
                    box = page.locator(selector).bounding_box()
                    assert box['y'] >= previous_bottom - 1, f'{selector} must not overlap the upper curtain or other scene controls'
                    assert box['y'] + box['height'] <= 901, selector
                    previous_bottom = box['y'] + box['height']
                if width == 1440:
                    page.mouse.move(700, 400)
                    page.wait_for_function('''document.querySelector('.theatre-glow')
                        .style.getPropertyValue('--glow-x') !== '' ''')
                page.evaluate('scrollTo(0, 150)')
                expect(nav).to_have_css('background-color', 'rgb(17, 11, 14)')
                expect(drape).to_have_css('opacity', '0')
                page.evaluate('scrollTo(0, 0)')
                expect(nav).to_have_css('background-color', 'rgba(0, 0, 0, 0)')
                expect(drape).to_have_css('opacity', '1')
                if width == 390:
                    page.locator('.menu-toggle').click()
                    expect(nav).to_have_css('background-color', 'rgb(17, 11, 14)')
                    expect(drape).to_have_css('opacity', '0')
                    page.keyboard.press('Escape')
                    expect(nav).to_have_css('background-color', 'rgba(0, 0, 0, 0)')
                    expect(drape).to_have_css('opacity', '1')
                first = page.locator('.concert-reportages .collection-link').first
                first.scroll_into_view_if_needed()
                expect(first).to_have_class(re.compile(r'\bis-visible\b'))
                first.click()
                page.wait_for_url('**/albums/concertsinfonia.html')
                page.goto(url + '#reportages')
                expect(stage).to_have_class(re.compile(r'\bis-open\b'))
                page.locator('.theatre-replay').click()
                page.evaluate('document.querySelector(".theatre-curtain").getAnimations()[0].cancel()')
                expect(stage).to_have_class(re.compile(r'\bis-open\b'))
                assert not stage.locator('.concert-stage-content').evaluate('(el) => el.inert'), 'Cancelled animations must release the scene'
                page.locator('.theatre-replay').click()
                page.set_viewport_size({'width':1024 if width == 390 else 390,'height':700})
                expect(stage).to_have_class(re.compile(r'\bis-open\b'))
                assert page.locator('.theatre-curtain').first.evaluate('(el) => el.getAnimations().length') == 0, 'Resize finishes the entrance without a breakpoint jump'
                page.set_viewport_size({'width':width,'height':900})
                page.locator('.theatre-replay').click()
                expect(page.locator('.theatre-replay')).to_be_disabled()
                page.emulate_media(reduced_motion='reduce')
                expect(stage).not_to_have_class(re.compile(r'\btheatre-ready\b'))
                expect(page.locator('.theatre-replay')).to_be_hidden()
                expect(page.locator('.theatre-reveal')).to_have_count(0)
                assert page.locator('.theatre-curtain').first.evaluate('(el) => el.getAnimations().length') == 0
                assert not errors, errors
                context.close()
                print(f'PASS {width}px: entrance, replay, reveal, album link and reduced motion', flush=True)
            fallback = browser.new_context(java_script_enabled=False,
                                          viewport={'width': 390, 'height': 844})
            fallback.route('https://**/*', lambda route: route.abort())
            page = fallback.new_page()
            page.goto(url)
            expect(page.locator('.theatre-replay')).to_be_hidden()
            expect(page.locator('.concert-reportages .collection-link')).to_have_count(2)
            expect(page.locator('.concert-reportages .collection-link').first).to_have_css('opacity', '1')
            page.locator('.concert-scroll').click()
            page.wait_for_url('**/concerts/index.html#reportages')
            print('PASS: reportages and navigation remain accessible without JavaScript', flush=True)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    run()
