#!/usr/bin/env python

import unittest
import mutagen.id3

from chirp.library import constants
from chirp.library import id3_text


class ID3TextTest(unittest.TestCase):

    def test_is_vanilla_text(self):
        # These are vanilla text tags.
        self.assertTrue(id3_text.is_vanilla_text(mutagen.id3.TPE1()))
        self.assertTrue(id3_text.is_vanilla_text(mutagen.id3.TALB()))
        self.assertTrue(id3_text.is_vanilla_text(mutagen.id3.TIT2()))
        # These aren't.
        self.assertFalse(id3_text.is_vanilla_text(mutagen.id3.UFID()))
        self.assertFalse(id3_text.is_vanilla_text(mutagen.id3.TDRC()))
        self.assertFalse(id3_text.is_vanilla_text(mutagen.id3.TLEN()))

    def test_standardize(self):
        # Check basic functionality against a vanilla tag.
        tag = mutagen.id3.TPE1(encoding=1,
                               text=["Bad whitespace   ",
                                     " ",  # Empty should be stripped out
                                     "  Bad    whitespace"])
        id3_text.standardize(tag)
        self.assertEqual(constants.DEFAULT_ID3_TEXT_ENCODING, tag.encoding)
        self.assertEqual(["Bad whitespace", "Bad whitespace"], tag.text)
        # Passing in a non-text tag should be harmless.
        id3_text.standardize(mutagen.id3.UFID())

        # Check that we fix the encoding on non-vanilla tags.
        tag = mutagen.id3.TDRC(encoding=1, year=2009)
        id3_text.standardize(tag)
        self.assertEqual(constants.DEFAULT_ID3_TEXT_ENCODING, tag.encoding)
        



if __name__ == "__main__":
    unittest.main()

