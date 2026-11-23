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
