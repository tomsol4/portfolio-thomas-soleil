"""Albums protégés par un mot de passe : page et images chiffrées, déchiffrées dans le navigateur."""
import re
import unittest

import support
from support import ROOT, CHROME, expect, offline, check_masonry
from playwright.sync_api import sync_playwright
from album_access import password_for, has_password
from album_list import load_albums, page_photos, public_photos
from build import variant_key

# Sur chaque page : combien de fois une fenêtre modale s'est ouverte, et si la page d'accès d'un album a été affichée
# avant que l'album ne la remplace (vérifié juste avant chaque image affichée).
WATCH_GATE = '''
window.albumDialogs = 0;
window.albumGateSeen = false;
const showModal = HTMLDialogElement.prototype.showModal;
HTMLDialogElement.prototype.showModal = function () { window.albumDialogs += 1; return showModal.call(this); };
(function watch(started) {
    const gate = document.querySelector('.album-access-page');
    if (gate && getComputedStyle(gate).visibility === 'visible') window.albumGateSeen = true;
    if (!document.querySelector('[data-album-ready]') && performance.now() - started < 10000) requestAnimationFrame(() => watch(started));
})(performance.now());
'''


class AlbumAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.albums = load_albums()
        cls.album = next(album for album in cls.albums if album['id'] == 'noel')
        cls.password = password_for('noel')
        cls.public_concert = next(a for a in cls.albums if a['category'] == 'Concerts' and not a.get('password_protected'))
        cls._site = support.local_site()
        cls.base = cls._site.__enter__() + '/'
        cls._playwright = sync_playwright().start()
        cls.browser = cls._playwright.chromium.launch(executable_path=CHROME)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._playwright.stop()
        cls._site.__exit__(None, None, None)

    def new_page(self, width, errors):
        context = offline(self.browser.new_context(viewport={'width': width, 'height': 900}, reduced_motion='reduce'))
        context.add_init_script(WATCH_GATE)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        return context, page

    def test_nothing_readable_is_published(self):
        """Ni le mot de passe, ni la galerie, ni une photo lisible d'un album protégé ne sont publiés."""
        source = (ROOT / 'albums/noel.html').read_text(encoding='utf-8')
        assert self.password not in source
        assert 'class="photo-link"' not in source, 'La galerie n’existe pas avant le mot de passe'
        assert 'album-encrypted-data' in source
        # Seules restent lisibles les couvertures, les photos des albums publics et celles choisies pour les pages.
        shared = public_photos(self.albums, page_photos())
        for protected in (a for a in self.albums if a.get('password_protected') and has_password(a['id'])):
            page_source = (ROOT / f'albums/{protected["id"]}.html').read_text(encoding='utf-8')
            assert password_for(protected['id']) not in page_source
            for src in protected['photos']:
                if src in shared:
                    continue
                readable = list((ROOT / 'images/optimized').glob(variant_key(src) + '-*.webp'))
                assert not readable, f'Photo lisible publiée pour un album protégé : {readable[0].name}'

    def test_concert_list_asks_for_the_password(self):
        """Sur la liste, le clic demande le mot de passe ; sans lui, on n'arrive pas sur la page de l'album."""
        album, password = self.album, self.password
        for width in [320, 390, 1440]:
            with self.subTest(width=width):
                errors, posts = [], []
                context, page = self.new_page(width, errors)
                page.on('request', lambda request: posts.append(request.url) if request.method == 'POST' else None)
                page.goto(self.base + 'concerts/index.html#reportages')
                listing = page.url
                locked = page.locator('.collection-link[href="../albums/noel.html"]')
                expect(locked.locator('.album-lock')).to_have_count(1)
                expect(page.locator(f'.collection-link[href="../albums/{self.public_concert["id"]}.html"] .album-lock')).to_have_count(0)
                expect(locked).to_have_attribute('aria-haspopup', 'dialog')
                locked.click()
                dialog = page.locator('#album-access-dialog')
                expect(dialog).to_be_visible()
                expect(page.locator('#album-password')).to_be_focused()
                expect(page.locator('#album-access-title')).to_have_text(album['title'])
                assert page.url == listing, 'La page de l’album ne s’ouvre pas avant le mot de passe'
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                page.keyboard.press('Escape')
                expect(dialog).not_to_be_visible()
                expect(locked).to_be_focused()
                locked.click()
                page.locator('#album-password').fill('incorrect-test-password')
                page.locator('#album-access-form [type=submit]').click()
                expect(page.locator('#album-access-status')).to_contain_text('incorrect')
                assert page.url == listing, 'Un mauvais mot de passe laisse le visiteur sur la liste'
                page.locator('#album-password').fill(password)
                page.keyboard.press('Enter')
                page.wait_for_url('**/albums/noel.html')
                expect(page.locator('.photo-link')).to_have_count(len(album['photos']))
                assert page.evaluate('window.albumDialogs') == 0, 'La page de l’album ne redemande pas le mot de passe'
                assert not page.evaluate('window.albumGateSeen'), 'La page fermée ne s’affiche pas avant l’album'
                expect(page.locator('html')).not_to_have_class(re.compile(r'\balbum-opening\b'))
                encrypted_image = page.locator('.photo-link').nth(1).get_attribute('href')
                assert encrypted_image.endswith('.bin'), 'Les photos de l’album sont publiées chiffrées'
                expect(page.locator('#contenu')).to_have_attribute('data-album-ready', 'true')
                expect(page.locator('#contenu')).not_to_have_attribute('data-image-key', re.compile('.'))
                check_masonry(page)
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
                # Page rechargée dans le même onglet : l'onglet a retenu l'album, il s'ouvre sans redemander le mot de passe.
                page.reload()
                expect(page.locator('.photo-link')).to_have_count(len(album['photos']))
                expect(page.locator('#contenu')).to_have_attribute('data-album-ready', 'true')
                assert page.evaluate('window.albumDialogs') == 0, 'Recharger la page ne redemande pas le mot de passe'
                assert not page.evaluate('window.albumGateSeen'), 'La page fermée ne s’affiche pas avant l’album'
                # Lien direct dans un autre onglet : la page de l'album demande elle-même le mot de passe.
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('request', lambda request: posts.append(request.url) if request.method == 'POST' else None)
                page.goto(self.base + 'albums/noel.html')
                dialog = page.locator('#album-access-dialog')
                expect(dialog).to_be_visible()
                expect(page.locator('#album-password')).to_be_focused()
                expect(page.locator('.photo-link')).to_have_count(0)
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
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
                assert not posts, 'Le mot de passe n’est jamais envoyé à un serveur'
                page.goto(self.base + f'albums/{self.public_concert["id"]}.html')
                expect(page.locator('.photo-link')).to_have_count(len(self.public_concert['photos']))
                expect(page.locator('#album-access-dialog')).to_have_count(0)
                response = page.request.get(self.base + 'albums/' + encrypted_image)
                assert response.ok
                assert response.body()[:4] != b'RIFF' and b'WEBP' not in response.body()[:16], 'Les images publiées sont illisibles'
                context.close()
                assert not errors, errors

    def test_wedding_list_asks_for_the_password(self):
        """Les deux liens du baptême demandent le mot de passe ; le bouton Précédent referme la fenêtre ;
        ensuite, l'onglet rouvre l'album sans le redemander."""
        wedding = next((a for a in self.albums if a['id'] == 'bapteme'), None)
        if not (wedding and has_password('bapteme')):
            self.skipTest('mot de passe du baptême absent de cet ordinateur')
        for width in [390, 1440]:
            with self.subTest(width=width):
                errors = []
                context, page = self.new_page(width, errors)
                page.goto(self.base + 'instants-de-vie/index.html#reportages')
                listing = page.url
                button = page.locator('.life-story-open[href="../albums/bapteme.html"]')
                button.click()
                expect(page.locator('#album-access-dialog')).to_be_visible()
                expect(page.locator('#album-access-title')).to_have_text(wedding['title'])
                assert page.url == listing, 'La page de l’album ne s’ouvre pas avant le mot de passe'
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                page.locator('#album-password').fill('incorrect-test-password')
                page.keyboard.press('Enter')
                expect(page.locator('#album-access-status')).to_contain_text('incorrect')
                page.keyboard.press('Escape')
                expect(button).to_be_focused()
                page.locator('.collection-link[href="../albums/bapteme.html"]').click()
                expect(page.locator('#album-access-status')).to_be_empty()
                page.locator('#album-password').fill(password_for('bapteme'))
                page.keyboard.press('Enter')
                page.wait_for_url('**/albums/bapteme.html')
                expect(page.locator('.photo-link')).to_have_count(len(wedding['photos']))
                assert page.evaluate('window.albumDialogs') == 0, 'La page de l’album ne redemande pas le mot de passe'
                assert not page.evaluate('window.albumGateSeen'), 'La page fermée ne s’affiche pas avant l’album'
                page.go_back()
                page.wait_for_url(listing)
                expect(page.locator('#album-access-dialog')).not_to_be_visible()
                button.click()
                page.wait_for_url('**/albums/bapteme.html')
                expect(page.locator('.photo-link')).to_have_count(len(wedding['photos']))
                assert page.evaluate('window.albumDialogs') == 0, 'Un album déjà ouvert dans l’onglet ne redemande pas le mot de passe'
                context.close()
                assert not errors, errors

    def test_without_javascript_the_album_stays_closed(self):
        fallback = self.browser.new_context(java_script_enabled=False, reduced_motion='reduce')
        page = fallback.new_page()
        page.goto(self.base + 'concerts/index.html#reportages')
        expect(page.locator('#album-access-dialog')).not_to_be_visible()
        page.locator('.collection-link[href="../albums/noel.html"]').click()
        page.wait_for_url('**/albums/noel.html')
        expect(page.locator('.photo-link')).to_have_count(0)
        expect(page.locator('.album-access-note')).to_contain_text('Activez JavaScript')
        expect(page.locator('.album-access-note')).to_be_visible()
        expect(page.locator('#album-access-form [type=submit]')).to_be_disabled()
        fallback.close()


if __name__ == '__main__':
    unittest.main()
