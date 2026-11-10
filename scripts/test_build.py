"""Vérifie les exports web et la détection des originaux dans les pages."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build
import check_site
from PIL import Image


class ConcertExports(unittest.TestCase):
    def test_narrow_photos_have_unique_candidates(self):
        for width in (320, 480, 600, 1920):
            with self.subTest(width=width), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = 'images/concert/concertsinfonia/photo.jpg'
                original = root / source
                original.parent.mkdir(parents=True)
                Image.new('RGB', (width, 200), 'gray').save(original)
                exports = root / 'images/optimized'
                exports.mkdir()
                with patch.multiple(build, ROOT=root, ASSETS=exports, CACHE={}, MANIFEST={}):
                    result = build.concert_viewer_asset(source)
                    widths = [size for _, size in result['variants']]
                    self.assertEqual(widths, sorted(set(widths)))
                    self.assertEqual(widths[-1], width)
                    for filename, size in result['variants']:
                        with Image.open(root / filename) as image:
                            self.assertEqual(image.width, size)
                    largest = Path(result['variants'][-1][0]).name
                    self.assertEqual(largest, f'concert_concertsinfonia_photo-viewer-hq-{width}.webp')
                    original.unlink()
                    build.CACHE.clear()
                    self.assertEqual(build.concert_viewer_asset(source), result)


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


if __name__ == '__main__':
    unittest.main()
