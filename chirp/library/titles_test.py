#!/usr/bin/env python

import unittest
from chirp.library import titles


class TitlesTest(unittest.TestCase):

    def test_standardize(self):
        for raw_text, expected_standardization in (
            ("Foo", "Foo"),
            # Check whitespace cleanup
            ("  Foo   ", "Foo"),
            ("Foo \t Bar", "Foo Bar"),
            ("Foo [  Tag ]", "Foo [Tag]"),
            ("Foo [Tag][Tag]", "Foo [Tag] [Tag]"),
            ("Foo[Tag]", "Foo [Tag]"),
            # Check quote handling
            (u"Don\u2019t Worry", "Don't Worry"),
            ("Name [7'']", 'Name [7"]'),
            (u"Name [7\u201d]", 'Name [7"]'),
            ):
            self.assertEqual(expected_standardization,
                             titles.standardize(raw_text))

        # Check that we reject malformed text.
        for bad_text in (
            "Unbalanced [", "Unbalanced ]",
            "Unbalanced [Foo", "Unbalanced [Foo] Bar]",
            "Nested [Foo [Bar]]",
            "Empty Tag []",
            "Foo [No Interior Tags] Bar",
            ):
            self.assertEqual(None, titles.standardize(bad_text))

    def test_append(self):
        for orig_text, to_append, expected_text in (
            ("Foo", "Bar", "FooBar"),
            ("Foo [Tag]", "Bar", "FooBar [Tag]"),
            ):
            self.assertEqual(expected_text,
                             titles.append(orig_text, to_append))

    def test_split_tags(self):
        self.assertEqual(("Foo", []),
                         titles.split_tags("Foo"))
        self.assertEqual(("Foo", ["Bar"]),
                         titles.split_tags("Foo [Bar]"))


if __name__ == "__main__":
    unittest.main()

