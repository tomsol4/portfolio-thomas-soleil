"""Galerie 3D des projets personnels (regards/galerie/) : tout ce qu'elle charge est publié avec le site,
et la visite fonctionne dans Chrome (vue en grand, bouton « retour », clic droit).

La galerie elle-même est refaite par scripts/musee_3d.py (dans Blender)."""
import json
import re
import unittest

import support
from support import ROOT, CHROME, expect, offline, watch_errors
from playwright.sync_api import sync_playwright

GALLERY = ROOT / 'regards/galerie'
OPTIMIZED = ROOT / 'images/optimized'


class Gallery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads((GALLERY / 'plan.json').read_text(encoding='utf-8'))
        cls.page = (GALLERY / 'index.html').read_text(encoding='utf-8')

    def test_engine_is_in_the_site(self):
        """Le moteur 3D est copié dans le site : aucune dépendance à un autre site, et chaque module est là."""
        importmap = json.loads(re.search(r'<script type="importmap">(.*?)</script>', self.page, re.S)[1])['imports']
        for name, path in importmap.items():
            with self.subTest(module=name):
                self.assertTrue(path.startswith('./'), f'{name} doit venir du site, pas de {path}')
        self.assertTrue((GALLERY / importmap['three']).is_file())
        addons = GALLERY / importmap['three/addons/']
        script = (GALLERY / 'galerie.js').read_text(encoding='utf-8')
        for addon in re.findall(r"from 'three/addons/([^']+)'", script):
            self.assertTrue((addons / addon).is_file(), addon)
        self.assertTrue((GALLERY / 'lib/LICENSE').is_file(), 'licence de three.js gardée avec le moteur')
        # aucune adresse extérieure (seul l'aperçu local est proposé quand on ouvre le fichier par un double-clic)
        self.assertNotRegex(self.page + script, r'https?://(?!www\.tsoleil\.fr|localhost:8765/)', 'aucune adresse extérieure')

    def test_every_loaded_file_exists(self):
        """Lumière de chaque surface, matières, photos et paysage de la baie : tous les fichiers existent."""
        self.assertTrue((GALLERY / 'musee.glb').is_file())
        for name, file in self.plan['lumieres'].items():
            self.assertTrue((GALLERY / file).is_file(), name)
        for name, material in self.plan['matieres'].items():
            if 'texture' in material:
                for suffix in ('', '_rugosite'):
                    ext = self.plan.get('format_matieres', '.jpg')
                    self.assertTrue((GALLERY / f"matieres/{material['texture']}{suffix}{ext}").is_file(), name)
        self.assertTrue((OPTIMIZED / f"{self.plan['matieres']['vue']['photo']}-1600.webp").is_file(), 'paysage de la baie')
        self.assertTrue((GALLERY / self.plan['ciel']).is_file(), 'ciel vu par les fenêtres')
        self.assertTrue((GALLERY / 'accueil.jpg').is_file(), 'image de l’écran de chargement')
        slots = {slot['id'] for slot in self.plan['accrochages']}
        hanging = json.loads((GALLERY / 'accrochage.json').read_text(encoding='utf-8'))
        self.assertTrue(hanging, 'des photos accrochées')
        for art in hanging:
            with self.subTest(emplacement=art['emplacement']):
                self.assertIn(art['emplacement'], slots)
                self.assertTrue(art['tailles'], 'au moins une taille de photo')
                for width in art['tailles']:
                    self.assertTrue((OPTIMIZED / f"{art['photo']}-{width}.webp").is_file(), width)

    def test_plan_has_what_the_page_needs(self):
        """Courbe de tons de Blender, hauteur de chaque salle (reflets), emplacements d'accrochage dans une salle."""
        tones = self.plan['tonalite']['valeurs']
        self.assertGreater(len(tones), 10)
        self.assertEqual(tones, sorted(tones), 'la courbe de tons monte')
        for name, room in self.plan['salles'].items():
            self.assertGreater(room['hauteur'], 2, name)
        for slot in self.plan['accrochages']:
            with self.subTest(emplacement=slot['id']):
                self.assertIn(slot['salle'], self.plan['salles'])
                self.assertGreater(slot['taille'], 0.3)

    def test_projects_page_leads_to_the_gallery(self):
        """La page Projets perso et les albums perso ont le bouton « Visite en 3D » (depuis un album, droit dans sa
        salle) ; la galerie y ramène."""
        for page, target in (('regards/index.html', 'index.html"'), ('albums/la_garde.html', 'index.html#garde"')):
            with self.subTest(page=page):
                self.assertIn(f'class="art-visit-link" href="../regards/galerie/{target}', (ROOT / page).read_text(encoding='utf-8'))
        self.assertIn('href="../index.html"', self.page)
        for room in self.plan['salles'].values():
            if 'lien' in room:
                self.assertTrue((GALLERY / room['lien']).resolve().is_file(), room['lien'])


class GalleryInBrowser(unittest.TestCase):
    """La visite dans Chrome sans fenêtre (la 3D tourne sans carte graphique, plus lentement)."""

    @classmethod
    def setUpClass(cls):
        cls._site = support.local_site()
        cls.base = cls._site.__enter__()
        cls._playwright = sync_playwright().start()
        cls.browser = cls._playwright.chromium.launch(executable_path=CHROME, args=['--enable-unsafe-swiftshader'])
        cls.plan = json.loads((GALLERY / 'plan.json').read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._playwright.stop()
        cls._site.__exit__(None, None, None)

    def test_visit_and_photo_in_large(self):
        """La visite s'ouvre sans erreur ; une photo en hauteur se voit entière en grand, sans le titre dessus ;
        le clic droit ne propose pas de l'enregistrer ; « retour » ferme la photo sans quitter la galerie."""
        context = offline(self.browser.new_context(viewport={'width': 1280, 'height': 720}))
        page = context.new_page()
        errors = []
        watch_errors(page, self.base, errors)
        page.on('console', lambda message: message.type == 'error' and errors.append(message.text))
        page.goto(self.base + '/regards/index.html')
        page.goto(self.base + '/regards/galerie/index.html')
        page.wait_for_function("performance.getEntriesByName('galerie-prete').length > 0", timeout=120000)

        artworks = page.evaluate('window.__galerie.oeuvres()')
        tall = next(i for i, art in enumerate(artworks) if art['cadre'][1] > art['cadre'][0])
        page.evaluate(f'window.__galerie.art({tall}, true)')
        image = page.locator('#viewer-img')
        expect(page.locator('#viewer')).to_be_visible()
        page.wait_for_function("document.getElementById('viewer-img').complete && document.getElementById('viewer-img').naturalWidth > 0")
        box, footer = image.bounding_box(), page.locator('.viewer footer').bounding_box()
        self.assertGreaterEqual(box['y'], 0)
        self.assertLessEqual(box['y'] + box['height'], footer['y'] + 1, 'photo entière, au-dessus de son titre')

        for target in ('#viewer-img', 'canvas'):
            blocked = page.locator(target).evaluate(
                'el => !el.dispatchEvent(new MouseEvent("contextmenu", {bubbles: true, cancelable: true}))')
            self.assertTrue(blocked, f'clic droit bloqué sur {target}')

        page.evaluate('history.back()')
        expect(page.locator('#viewer')).to_be_hidden()
        self.assertIn('/regards/galerie/index.html', page.url)
        context.close()
        self.assertFalse(errors, errors)

    def test_link_to_a_room(self):
        """« index.html#garde » ouvre la visite directement dans la salle La Garde."""
        context = offline(self.browser.new_context(viewport={'width': 1280, 'height': 720}))
        page = context.new_page()
        errors = []
        watch_errors(page, self.base, errors)
        page.goto(self.base + '/regards/galerie/index.html#garde')
        page.wait_for_function("performance.getEntriesByName('galerie-prete').length > 0", timeout=120000)
        expect(page.locator('#room-title')).to_have_text(self.plan['salles']['garde']['titre'])
        context.close()
        self.assertFalse(errors, errors)

    def test_walk_like_a_game(self):
        """Comme dans un jeu : la touche Z (W en QWERTY) fait marcher, on s'arrête en douceur en la lâchant,
        on ne traverse pas le banc du hall ; seules les photos de la salle où l'on est passent en grand."""
        context = offline(self.browser.new_context(viewport={'width': 1280, 'height': 720}))
        page = context.new_page()
        errors = []
        watch_errors(page, self.base, errors)
        page.goto(self.base + '/regards/galerie/index.html')
        page.wait_for_function("performance.getEntriesByName('galerie-prete').length > 0", timeout=120000)
        start = page.evaluate('window.__galerie.pose.pos.z')
        page.keyboard.down('KeyW')
        page.wait_for_function(f'window.__galerie.pose.pos.z < {start} - 0.5', timeout=20000)
        page.wait_for_timeout(4000)   # assez pour arriver au banc, s'il n'arrêtait pas
        page.keyboard.up('KeyW')
        page.wait_for_function('window.__galerie.vel.length() === 0', timeout=20000)
        bench = next(o for o in self.plan['obstacles'] if o[0] < 0 < o[1] and o[2] < start)
        self.assertGreater(page.evaluate('window.__galerie.pose.pos.z'), bench[3], 'arrêté devant le banc')
        urls = {art['salle']: art['url'] for art in page.evaluate('window.__galerie.oeuvres()')}
        self.assertNotIn('-480.webp', urls['hall'], 'photos du hall en grand')
        self.assertIn('-480.webp', urls['messe'], 'photos des autres salles encore légères')
        context.close()
        self.assertFalse(errors, errors)


if __name__ == '__main__':
    unittest.main()
