# -*- coding: utf-8 -*-

import unittest
from chirp.common import unicode_util

from chirp.library import artists

class UnicodeUtilTest(unittest.TestCase):

    def test_simplify(self):
        CASES = (
            ("Foo", "Foo"),
            ("Øåø", "Oao"),
            ("Allá", "Alla"),
            ("Björk", "Bjork"),
            ("Édith Piaf", "Edith Piaf"),
            ("Stéphane", "Stephane"),
            ("Maxïmo", "Maximo"),
            ("Hüsker Dü", "Husker Du"),
            ("Dâm-Funk", "Dam-Funk"),
            ("Françoise", "Francoise"),
            )
        for before, after in CASES:
            self.assertEqual(after, unicode_util.simplify(before))


if __name__ == "__main__":
    unittest.main()

