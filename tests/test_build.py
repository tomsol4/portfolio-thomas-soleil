"""Fabrication du site : exports web des photos et garde-fous sur ce qui est publié."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import support  # noqa: F401  (rend accessibles les scripts du site)
import build
import check_site
from PIL import Image


class WebExports(unittest.TestCase):
    SOURCE = 'images/concert/concertsinfonia/photo.jpg'

    def export_folder(self, directory, width):
        root = Path(directory)
        original = root / self.SOURCE
        original.parent.mkdir(parents=True)
        Image.new('RGB', (width, 200), 'gray').save(original)
        exports = root / 'images/optimized'
        exports.mkdir()
        return root, original, exports

    def test_narrow_photos_have_unique_candidates(self):
        for width in (320, 480, 600, 1920, 3000):
            with self.subTest(width=width), tempfile.TemporaryDirectory() as directory:
                root, original, exports = self.export_folder(directory, width)
                with patch.multiple(build, ROOT=root, ASSETS=exports, CACHE={}, MANIFEST={}):
                    result = build.asset(self.SOURCE, large=True)
                    widths = [size for _, size in result['variants']]
                    self.assertEqual(widths, sorted(set(widths)))
                    self.assertEqual(widths[-1], min(width, build.MAX_WIDTH))
                    for filename, size in result['variants']:
                        with Image.open(root / filename) as image:
                            self.assertEqual(image.width, size)
                    # Sans l'original (autre ordinateur), les exports existants et le manifeste suffisent.
                    original.unlink()
                    build.CACHE.clear()
                    self.assertEqual(build.asset(self.SOURCE, large=True), result)

    def test_quality_change_redoes_the_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            root, original, exports = self.export_folder(directory, 3000)
            with patch.multiple(build, ROOT=root, ASSETS=exports, CACHE={}, MANIFEST={}):
                build.asset(self.SOURCE, large=True)
                self.assertEqual(build.MANIFEST[self.SOURCE]['qualites'], {'480': 80, '960': 80, '1600': 82, '2560': 82})
                largest = exports / Path(build.CACHE[(self.SOURCE, True)]['variants'][-1][0]).name
                before = largest.stat().st_mtime_ns
                build.CACHE.clear()
                with patch.object(build, 'QUALITY_LARGE', 60):
                    build.asset(self.SOURCE, large=True)
                self.assertEqual(build.MANIFEST[self.SOURCE]['qualites']['2560'], 60)
                self.assertNotEqual(largest.stat().st_mtime_ns, before, 'La grande version est refaite')


class PublishedReferences(unittest.TestCase):
    def test_locked_page_cannot_reference_an_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'images').mkdir()
            (root / 'images/original.jpg').write_bytes(b'original')
            (root / 'data').mkdir()
            (root / 'data/albums.json').write_text('[]', encoding='utf-8')
            (root / 'data/photo-descriptions.json').write_text('{}', encoding='utf-8')
            (root / '404.html').write_text(
                '<link rel="canonical" href="https://www.tsoleil.fr/404.html">'
                '<main><h1>Album</h1><img src="images/original.jpg" alt="Photo" width="1" height="1"></main>',
                encoding='utf-8')
            (root / 'sitemap.xml').write_text(
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>', encoding='utf-8')
            output = io.StringIO()
            with patch.object(check_site, 'ROOT', root), patch.object(check_site, 'readable', return_value=None):
                with contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
                    check_site.check()
            self.assertIn('original non publié', output.getvalue())

    def test_private_photo_descriptions_stay_unpublished(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ('images', 'data', 'albums'):
                (root / folder).mkdir()
            album = {'id': 'famille', 'title': 'Famille', 'password_protected': True,
                     'cover': 'images/famille/couverture.jpg', 'photos': ['images/famille/photo.jpg']}
            (root / 'data/albums.json').write_text(json.dumps([album]), encoding='utf-8')
            (root / 'data/photo-descriptions.json').write_text(
                json.dumps({'images/famille/photo.jpg': 'Un enfant dans un salon'}), encoding='utf-8')
            (root / 'albums/famille.html').write_text('<main><h1>Famille</h1></main>', encoding='utf-8')
            (root / 'sitemap.xml').write_text(
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>', encoding='utf-8')
            output = io.StringIO()
            with patch.object(check_site, 'ROOT', root), patch.object(check_site, 'readable', return_value=None):
                with contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
                    check_site.check()
            self.assertIn('Description publiée d’une photo d’album protégé', output.getvalue())


class AlbumFolders(unittest.TestCase):
    """Un album peut donner tout un dossier au lieu de la liste de ses photos."""

    def test_folder_album(self):
        from album_list import load_albums
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'images/concert/ete'
            (folder / 'sous-dossier').mkdir(parents=True)
            for name in ['photo-10.jpg', 'photo-2.JPG', 'photo-1.webp', 'a-retirer.jpg', 'notes.txt', 'sous-dossier/autre.jpg']:
                (folder / name).write_bytes(b'')
            (root / 'data').mkdir()
            albums = [{'id': 'ete', 'dossier': 'images/concert/ete', 'sauf': ['a-retirer.jpg']},
                      {'id': 'choisi', 'cover': 'images/x.jpg', 'photos': ['images/y.jpg', 'images/x.jpg']}]
            (root / 'data/albums.json').write_text(json.dumps(albums), encoding='utf-8')
            folder_album, chosen = load_albums(root)
            self.assertEqual(folder_album['photos'], ['images/concert/ete/photo-1.webp', 'images/concert/ete/photo-2.JPG',
                                                      'images/concert/ete/photo-10.jpg'])
            self.assertEqual(folder_album['cover'], 'images/concert/ete/photo-1.webp')
            self.assertEqual(chosen['photos'], ['images/y.jpg', 'images/x.jpg'], 'Une liste écrite garde son ordre')
            self.assertEqual(chosen['cover'], 'images/x.jpg')
            # Sans les originaux (autre ordinateur), le manifeste des images donne les mêmes photos.
            manifest = {src: {'width': 1, 'height': 1} for src in folder_album['photos'] + ['images/concert/ete/a-retirer.jpg']}
            (root / 'data/image-manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            for item in sorted(folder.rglob('*'), reverse=True):
                item.rmdir() if item.is_dir() else item.unlink()
            folder.rmdir()
            self.assertEqual(load_albums(root)[0]['photos'], folder_album['photos'])


class ProtectedPhotosOnPages(unittest.TestCase):
    """Une photo d'album protégé choisie pour une page devient publique ; dans la mosaïque des concerts, son lien
    demande le mot de passe de l'album."""

    def test_page_photos_are_public(self):
        from album_list import page_photos, public_photos
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data').mkdir()
            pages = {'_aide': 'images/pas-une-photo.jpg', 'concerts': {'ouverture': 'images/noel/1.jpg',
                     'mosaique': [['images/noel/2.jpg']], 'tarifs': {'photo': 'images/noel/3.jpg', 'texte': 'Une scène'}}}
            (root / 'data/photos-des-pages.json').write_text(json.dumps(pages), encoding='utf-8')
            chosen = page_photos(root)
            self.assertEqual(chosen, {'images/noel/1.jpg', 'images/noel/2.jpg', 'images/noel/3.jpg'})
            albums = [{'id': 'noel', 'cover': 'images/noel/0.jpg', 'password_protected': True,
                       'photos': ['images/noel/0.jpg', 'images/noel/1.jpg', 'images/noel/2.jpg', 'images/noel/9.jpg']}]
            public = public_photos(albums, chosen)
            self.assertIn('images/noel/1.jpg', public)
            self.assertNotIn('images/noel/9.jpg', public, 'Une photo protégée qui n’est sur aucune page reste chiffrée')

    def test_mosaic_link_asks_for_the_password(self):
        import universes
        albums = [{'id': 'public', 'title': 'Public', 'photos': ['images/a.jpg']},
                  {'id': 'noel', 'title': 'Noël', 'password_protected': True, 'photos': ['images/b.jpg']}]
        picture = lambda src, alt, prefix, **options: f'<img alt="{alt}">'
        asset = lambda src, large=False: {'width': 3, 'height': 2, 'variants': []}
        with patch.dict(universes.PAGE_PHOTOS['concerts'], {'mosaique': [['images/a.jpg', 'images/b.jpg']]}):
            mosaic = universes.concert_mosaic(albums, picture, asset)
        self.assertIn('href="../albums/public.html">', mosaic)
        self.assertIn('href="../albums/noel.html" data-album-locked="Noël"', mosaic)


class Prices(unittest.TestCase):
    def test_prices_never_break_across_lines(self):
        from prices import euros
        self.assertEqual(euros(1000), '1 000 €')
        self.assertEqual(euros(60), '60 €')

    def test_every_template_token_is_replaced(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(build, 'ROOT', Path(directory)):
            with self.assertRaisesRegex(ValueError, 'Jeton non remplacé'):
                build.write('page.html', '<p>{{PRIX_INCONNU}}</p>')


if __name__ == '__main__':
    unittest.main()
