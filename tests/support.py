"""Outils communs aux tests : chemins du projet, petit serveur local, Chrome et vérifications partagées.

Lancer tous les tests depuis la racine du projet :  python -m unittest discover -s tests -v
Un seul fichier :                                   python tests/test_browser.py
Les tests ouvrent le site dans Chrome sans fenêtre ; Internet est coupé pour eux : aucun message n'est envoyé.
Ils vérifient que le site marche et protège ce qui doit l'être, pas son apparence.
Captures d'écran pour relecture (dans test-results/) : seulement sur demande, avec la variable CAPTURES=1
(PowerShell : $env:CAPTURES = 1 avant de lancer les tests).
"""
from contextlib import contextmanager
import functools
import http.server
import os
from pathlib import Path
import re
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / '.tools/python', ROOT / 'scripts'):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from playwright.sync_api import expect  # noqa: E402
from album_access import password_for  # noqa: E402

CHROME = os.environ.get('CHROME_PATH', r'C:\Program Files\Google\Chrome\Application\chrome.exe')
# Captures d'écran et relevés des tests (jamais publiés, voir .gitignore).
OUT = ROOT / 'test-results'
OUT.mkdir(exist_ok=True)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        try:
            super().do_GET()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass


@contextmanager
def local_site():
    """Sert le site sur un port libre de cet ordinateur ; donne son adresse, sans « / » final."""
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()


def offline(context):
    """Coupe Internet pour ce navigateur : Formspree, Instagram et tout site extérieur restent injoignables."""
    context.route('https://**/*', lambda route: route.abort())
    return context


def watch_errors(page, base, errors):
    """Note les erreurs JavaScript de la page et les fichiers du site introuvables."""
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('response', lambda response: errors.append(f'{response.status}: {response.url}')
            if response.status >= 400 and response.url.startswith(base) else None)


def contrast_ratio(first, second):
    def luminance(rgb):
        values = [v / 255 for v in rgb[:3]]
        values = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(v * w for v, w in zip(values, [.2126, .7152, .0722]))
    light, dark = sorted([luminance(first), luminance(second)], reverse=True)
    return (light + .05) / (dark + .05)


def unlock_album(page):
    """Ouvre un album protégé avec son mot de passe (gardé sur cet ordinateur) ; ne fait rien pour un album public.

    Un album déjà ouvert dans le même onglet s'ouvre tout seul : on attend alors seulement qu'il soit prêt."""
    if not page.locator('#album-encrypted-data, #contenu[data-album-ready]').count():
        return
    page.wait_for_function('document.querySelector("#contenu[data-album-ready], #album-access-dialog[open]") !== null')
    if page.locator('#album-access-dialog[open]').count():
        album_id = page.locator('#album-encrypted-data').evaluate('(el) => JSON.parse(el.textContent).id')
        page.locator('#album-password').fill(password_for(album_id))
        page.locator('#album-access-form [type=submit]').click()
    expect(page.locator('.photo-grid')).to_be_visible()
    expect(page.locator('#contenu')).to_have_attribute('data-album-ready', 'true')


def check_masonry(page):
    """La mosaïque d'un album : ni trou ni chevauchement, l'ordre et les proportions gardés.

    Le nombre de colonnes est celui que règle la feuille de style (--gallery-columns), quel qu'il soit."""
    grid = page.locator('.photo-grid')
    expect(grid).to_have_class(re.compile(r'\bis-masonry\b'))
    # On attend que la mosaïque ait fini de se ranger pour la largeur actuelle (après un changement de taille d'écran).
    page.wait_for_function('''() => {
        const grid = document.querySelector('.photo-grid');
        const bounds = grid.getBoundingClientRect();
        const items = Array.from(grid.children, item => item.getBoundingClientRect());
        const wanted = Math.min(parseInt(getComputedStyle(grid).getPropertyValue('--gallery-columns'), 10), items.length);
        return new Set(items.map(box => Math.round(box.left))).size === wanted
            && items.every(box => box.right <= bounds.right + 1);
    }''')
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
    previous_bottom = {}
    previous_top = -1
    for photo in geometry['photos']:
        column = round(photo['x'], 2)
        assert photo['width'] > 0 and photo['x'] >= -.1
        assert photo['x'] + photo['width'] <= geometry['width'] + 1
        assert photo['y'] >= previous_top - .1, 'La mosaïque garde l’ordre de publication, de haut en bas'
        expected_top = previous_bottom.get(column, -geometry['gap']) + geometry['gap']
        assert abs(photo['y'] - expected_top) <= 1.5, 'Ni chevauchement ni trou dans la mosaïque'
        assert abs(photo['imageHeight'] - photo['imageWidth'] / photo['ratio']) <= 1.5, 'Les photos gardent leurs proportions'
        previous_bottom[column] = photo['y'] + photo['height']
        previous_top = photo['y']
    assert abs(max(previous_bottom.values()) - geometry['height']) <= 1.5, 'La mosaïque réserve toute sa hauteur avant le pied de page'
