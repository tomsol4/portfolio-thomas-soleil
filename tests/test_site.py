"""Le vérificateur du site (scripts/check_site.py) : pages, liens, descriptions, plan du site."""
import contextlib
import io
import unittest

import support  # noqa: F401  (rend accessibles les scripts du site)
import check_site


class SiteCheck(unittest.TestCase):
    def test_pages_links_and_descriptions(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            try:
                check_site.check()
            except SystemExit:
                self.fail('Le vérificateur a trouvé des problèmes :\n' + output.getvalue())


if __name__ == '__main__':
    unittest.main()
