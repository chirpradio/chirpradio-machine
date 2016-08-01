#!/usr/bin/env python

import codecs
import cStringIO
import os
import sys
import unittest
from chirp.library import artists


TEST_WHITELIST = """
# A comment, followed by a blank line

Bob Dylan
The Fall
John Lee Hooker
Tom Petty & the Heartbreakers
"""

TEST_MAPPINGS = """
# A comment, followed by a blank line

John Hooker SEP John Lee Hooker
Tom Petty and his heartbreakers SEP Tom Petty & the Heartbreakers
""".replace("SEP", artists._MAPPINGS_SEP)


def _unicode_stringio(text):
    return codecs.iterdecode(cStringIO.StringIO(text.encode("utf-8")),
                             "utf-8")


class ArtistsTest(unittest.TestCase):

    def test_basics(self):
        file_obj = _unicode_stringio(TEST_WHITELIST)
        names = artists._read_artist_whitelist_from_file(file_obj)
        whitelist = artists._seq_to_whitelist(names)
        self.assertEqual(4, len(whitelist))

        file_obj = _unicode_stringio(TEST_MAPPINGS)
        mappings, raw_mappings = artists._read_artist_mappings_from_file(
            file_obj)
        self.assertEqual(2, len(mappings))
        self.assertEqual(2, len(raw_mappings))

        # Check basic matching against the whitelist.
        for the_fall in ("fall", "fall, the", " the fall", "fall, the "):
            self.assertEqual(
                "The Fall",
                artists._standardize(the_fall, whitelist, mappings))
        self.assertEqual(
            "Bob Dylan",
            artists._standardize("dylan bob", whitelist, mappings))
        self.assertEqual(
            "Tom Petty & the Heartbreakers",
            artists._standardize("tom petty and his heartbreakers",
                                 whitelist, mappings))
        self.assertEqual(
            "John Lee Hooker",
            artists._standardize("john  lee hooker", whitelist, mappings))
        self.assertEqual(None,
                         artists._standardize("unknown", whitelist, mappings))

        # Check mappings.
        self.assertEqual(
            "John Lee Hooker",
            artists._standardize("john hooker", whitelist, mappings))
        self.assertEqual(
            "John Lee Hooker",
            artists._standardize("hooker, john", whitelist, mappings))

    def test_reset_fails_on_collisions(self):
        self.assertFalse(
            artists.reset_artist_whitelist(["Fall", "The Fall"]))

    def test_standardized_none_is_none(self):
        self.assertEqual(artists.standardize(None), None)

    def test_split(self):
        test_cases = (
            # This works even though "Unknown Artist" is not in the
            # artist whitelist.
            ("Unknown Artist", "Unknown Artist", None),
            ("Unknown Artist feat. T-Pain", "Unknown Artist", "T-Pain"),
            # Since we don't use the artist whitelist, we just do the
            # simple thing w.r.t. multiple solutions and return the
            # shortest possible primary.
            ("Unknown Artist & Cher feat. T-Pain",
             "Unknown Artist", "Cher feat. T-Pain"),
            )
        for text, expected_head, expected_tail in test_cases:
            head, tail = artists.split(text)
            self.assertEqual(expected_head, head)
            self.assertEqual(expected_tail, tail)

    def test_split_and_standardize(self):
        test_cases = (
            ("Fall, The", "The Fall", None),
            ("The Fall feat. T-Pain", "The Fall", "T-Pain"),
            ("The Fall  (Featuring T-Pain  )", "The Fall", "T-Pain"),
            ("The Fall [WITH    T-Pain]", "The Fall", "T-Pain"),
            (" The Fall  w/ T-Pain", "The Fall", "T-Pain"),
            ("The Fall and T-Pain", "The Fall", "T-Pain"),
            ("Fall, The [& T-Pain]", "The Fall", "T-Pain"),
            ("The Fall feat. T-Pain & Cher", "The Fall", "T-Pain & Cher"),
            # If there are multiple places where we can split, we choose
            # the longest possible primary.
            ("Black, Frank & the Catholics",
             "Frank Black & the Catholics", None),
            ("Frank Black & T-Pain", "Frank Black", "T-Pain"),
            ("Frank Black & the Catholics feat. T-Pain",
             "Frank Black & the Catholics", "T-Pain"),
            ("Frank Black & the Catholics & T-Pain",
             "Frank Black & the Catholics", "T-Pain"),
            # The main artist has to be on our whitelist, but not the
            # secondary artist(s).
            # For these values to equal None, the artist name must not
            # be in the whitelist.
            ("Literally Unknown Artist", None, None),
            ("Literally Unknown Artist Feat. T-Pain", None, None),
            ("The Fall feat. Unknown Artist", "The Fall", "Unknown Artist"),
            )
        for text, expected_head, expected_tail in test_cases:
            head, tail = artists.split_and_standardize(text)
            self.assertEqual(expected_head, head)
            self.assertEqual(expected_tail, tail)

    def test_merge_whitelist_and_mappings(self):
        # TODO(trow): This needs to be filled in.
        pass

    def test_suggest(self):
        # Suggest should handle simple typos.
        self.assertEqual("Bob Dylan", artists.suggest("Bo Dylann"))
        self.assertEqual("Big Boys", artists.suggest("Bigg Boy"))
        # Suggest should handle simple variations.
        self.assertEqual("Booker T. & the M.G.'s",
                         artists.suggest("Booker T and the MGs"))
        self.assertEqual("N.W.A.", artists.suggest("The NWA"))
        # Something truly weird will not yield any suggestions.
        self.assertTrue(artists.suggest("x"*100) is None)

    def test_real_data(self):
        self.assertTrue(len(artists._global_whitelist) > 2000)
        self.assertTrue(len(artists._global_mappings) >= 2)

        # Check some known whitelist items.
        for expected, raw in (("Bob Dylan", "bob dylan"),
                              ("The Fall", "fall"),
                              ):
            self.assertEqual(expected, artists.standardize(raw))
        # Check a known mapping.
        for expected, raw in (("Gordon Staples", "Gordon Stapes"),
                              ):
            self.assertEqual(expected, artists.standardize(raw))

        # Repeatedly merge the global whitelist and mappings until the two
        # dicts stabilize.  If merging caused anything to change, write
        # out corrected forms of the files, print a banner and a diff
        # to stdout, and cause the test to fail.
        whitelist, mappings = artists.merge_whitelist_and_mappings(
            artists._global_whitelist, artists._global_raw_mappings)

        fixed_whitelist_filename = artists._WHITELIST_FILE + ".fixed"
        fixed_mappings_filename = artists._MAPPINGS_FILE + ".fixed"
        # Delete these files if they already exist.
        for filename in (fixed_whitelist_filename, fixed_mappings_filename):
            try:
                os.unlink(filename)
            except OSError:
                pass

        test_should_succeed = True

        if whitelist != artists._global_whitelist:
            test_should_succeed = False
            print "\n\n"
            print "*" * 70
            print "***"
            print "*** Whitelist is not properly normalized"
            print "***"
            print "*** Diff:"
            out = codecs.open(fixed_whitelist_filename, "w", "utf-8")
            for white in sorted(whitelist.values(),
                                key=artists.sort_key):
                out.write(u"%s\n" % white)
            out.close()
            diff_cmd = "diff -u %s %s" % (artists._WHITELIST_FILE,
                                          fixed_whitelist_filename)
            sys.stdout.flush()
            os.system(diff_cmd)
            sys.stdout.flush()
            print "*" * 70
            print "\n\n"

        if mappings != artists._global_raw_mappings:
            test_should_succeed = False
            print "\n\n"
            print "*" * 70
            print "***"
            print "*** Mappings are not properly normalized"
            print "***"
            print "*** Diff:"
            out = codecs.open(fixed_mappings_filename, "w", "utf-8")
            for before in sorted(mappings, key=artists.sort_key):
                out.write(u"%s %s %s\n" % (before,
                                           artists._MAPPINGS_SEP,
                                           mappings[before]))
            out.close()
            diff_cmd = "diff -u %s %s" % (artists._MAPPINGS_FILE,
                                          fixed_mappings_filename)
            sys.stdout.flush()
            os.system(diff_cmd)
            sys.stdout.flush()
            print "*" * 70
            print "\n\n"

        self.assertTrue(test_should_succeed)


if __name__ == "__main__":
    unittest.main()
