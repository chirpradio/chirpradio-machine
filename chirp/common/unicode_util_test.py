# -*- coding: utf-8 -*-

import unittest
from chirp.common import unicode_util

from chirp.library import artists

class UnicodeUtilTest(unittest.TestCase):

    def test_simplify(self):
        CASES = (
            (u"Foo", u"Foo"),
            (u"Øåø", u"Oao"),
            (u"Allá", u"Alla"),
            (u"Björk", u"Bjork"),
            (u"Édith Piaf", u"Edith Piaf"),
            (u"Stéphane", u"Stephane"),
            (u"Maxïmo", u"Maximo"),
            (u"Hüsker Dü", u"Husker Du"),
            (u"Dâm-Funk", u"Dam-Funk"),
            (u"Françoise", "Francoise"),
            )
        for before, after in CASES:
            self.assertEqual(after, unicode_util.simplify(before))


if __name__ == "__main__":
    unittest.main()

