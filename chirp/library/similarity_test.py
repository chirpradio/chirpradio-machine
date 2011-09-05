#!/usr/bin/env python

###
### A unit test for similarity.py.
###

import unittest
from chirp.library import similarity


class CanonicalizeStringTest(unittest.TestCase):

    def test_basic(self):
        test_cases = (
            ("", u""),
            ("   ", u""),
            (u"foo", u"foo"),
            ("foo. bar.", u"foobar"),
            ("foo &   Bar  ", u"foo&bar"),
            ("The Foo and Bar", u"foo&bar"),
            ("Foo!!!", u"foo"),
            ("!!!!", u"!!!!"),
            )
        for before, after in test_cases:
            self.assertEqual(after, similarity.canonicalize_string(before))


class LevenshteinDistanceTest(unittest.TestCase):

    def test_basic(self):
        test_cases = (
            (0, "", ""),
            (0, "same string", "same string"),
            (1, "a", "b"),
            (1, "12345", "123 45"),
            (1, "the fall", "the falll"),
            (2, "rolling stones", "roling stone"),
            (5, "", "12345"),
            (2, "1234", "123456"),
            (2, "2345", "123456"),
            (2, "3456", "123456"),
            (3, "abc", "xyz"),
            (3, "kitten", "sitting"),
            (3, "saturday", "sunday"),
            (9, "VERY", "different"))
        for expected_dist, string_1, string_2 in test_cases:
            dist = similarity.get_levenshtein_distance(string_1, string_2)
            self.assertEqual(expected_dist, dist, 
                             msg="(%s, %s)" % (string_1, string_2))
            dist = similarity.get_levenshtein_distance(string_2, string_1)
            self.assertEqual(expected_dist, dist,
                             msg="(%s, %s)" % (string_2, string_1))
            # Test setting max_value for many different values.
            for max_value in xrange(1, expected_dist+2):
                clamped_dist = similarity.get_levenshtein_distance(
                    string_1, string_2, max_value=max_value)
                self.assertEqual(min(expected_dist, max_value),
                                 clamped_dist)


class CommonPrefixTest(unittest.TestCase):

    def test_common_prefix(self):
        test_cases = (
            ("", "", ""),
            ("", "foo", ""),
            ("foo", "foo", "foo"),
            ("foo", "foo", "foobar"),
            ("foo", "fooxxx", "fooyyy"))
        for expected_prefix, string_1, string_2 in test_cases:
            self.assertEqual(expected_prefix,
                             similarity.get_common_prefix(string_1, string_2))
            self.assertEqual(expected_prefix,
                             similarity.get_common_prefix(string_2, string_1))


class GetSortKeyTest(unittest.TestCase):
    
    def test_get_sort_key(self):
        test_cases = (("", ""),
                      ("The Fall", "Fall"),
                      ("no changes", "no changes"))
        for original, expected in test_cases:
            self.assertEqual(expected, similarity.get_sort_key(original))



if __name__ == "__main__":
    unittest.main()
