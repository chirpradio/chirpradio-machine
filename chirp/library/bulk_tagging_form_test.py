#!/usr/bin/env python

import codecs
import cStringIO
import unittest

from chirp.library import bulk_tagging_form


TEST_FORM_1 = """
00123--------- A Perfect Circle
a7314af4 [ 1 ] 192 12 Mer de Noms
e2ebb0f2 [ 1 ] 128 12 Mer de Noms
55d1c5a4 [   ] 192 12 Thirteenth Step
A line to skip
1234abcd [ x ] 192 10 To Be Deleted
abcd1234 [ ? ] 222  7 What You Talkin' About Willis?

00665--------- Audioslave
00085fb1 [ 1 ] 128 14 Audioslave
660414cd [ 1 ] 192 14 Audioslave
52c55fc7 [   ] 228 12 Out of Exile
11111111 [ 2 ] 228 13 TALB
22222222 [ 2 ] 228 13 MISMATCH
"""

EXPECTED_RESULTS_1 = {
    "a7314af4": (bulk_tagging_form.VERIFIED,
                 "A Perfect Circle", "Mer de Noms"),
    "e2ebb0f2": (bulk_tagging_form.DUPLICATE, 
                 "A Perfect Circle", "Mer de Noms"),
    "55d1c5a4": (bulk_tagging_form.VERIFIED,
                 "A Perfect Circle", "Thirteenth Step"),
    "1234abcd": (bulk_tagging_form.DELETE,
                 "A Perfect Circle", "To Be Deleted"),
    "abcd1234": (bulk_tagging_form.QUESTION, 
                 "A Perfect Circle", "What You Talkin' About Willis?"),
    "00085fb1": (bulk_tagging_form.DUPLICATE,
                 "Audioslave", "Audioslave"),
    "660414cd": (bulk_tagging_form.VERIFIED,
                 "Audioslave", "Audioslave"),
    "52c55fc7": (bulk_tagging_form.VERIFIED, 
                 "Audioslave", "Out of Exile"),
    "11111111": (bulk_tagging_form.TALB_MISMATCH, 
                 "Audioslave", "TALB", '"MISMATCH" vs. "TALB"'),
    "22222222": (bulk_tagging_form.TALB_MISMATCH,
                 "Audioslave", "MISMATCH", '"MISMATCH" vs. "TALB"'),
}


class BulkTaggingFormTest(unittest.TestCase):

    def test_re(self):
        test_cases = (
            ("50a0e546 [ 4 ] 192 12 The First Conspiracy",
             ("50a0e546", " 4 ", "192", "The First Conspiracy")),
            ("50a0e546 [] 192 12 The First Conspiracy",
             ("50a0e546", "", "192", "The First Conspiracy")),
            )
        for test_str, expected_groups in test_cases:
            match = bulk_tagging_form.LINE_RE.search(test_str)
            self.assertTrue(match is not None)
            self.assertEqual(expected_groups, match.groups())

        non_matching_test_cases = (
            "",
            "foo",
            "50a0e546 [ ] 192 12",
            "50a0e54 [ x ] 192 12 The First Conspiracy",
            "50a**546 [ x ] 192 12 The First Conspiracy",
            "50a0e546 []] 192 The First Conspiracy",
            "50a0e546 []] The First Conspiracy",
            )
        for test_str in non_matching_test_cases:
            match = bulk_tagging_form.LINE_RE.search(test_str)
            self.assertTrue(match is None)

    def test_parser(self):
        # Check that we can parse an empty file.
        parsed_0 = bulk_tagging_form.parse_file(cStringIO.StringIO(""))
        self.assertEqual({}, parsed_0)

        # Check that we can parse a simple test form.
        parsed_1 = bulk_tagging_form.parse_file(
            cStringIO.StringIO(TEST_FORM_1))
        self.assertEqual(EXPECTED_RESULTS_1, parsed_1)


if __name__ == "__main__":
    unittest.main()
