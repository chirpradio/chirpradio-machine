#!/usr/bin/env python

import os
import unittest

from chirp.common import ROOT_DIR
from chirp.library import crawler
from chirp.library import fingerprint


TESTDATA = os.path.join(ROOT_DIR, "library/testdata/crawler_test")


class CrawlerTest(unittest.TestCase):

    def test_empty(self):
        crawl = crawler.Crawler()
        crawl.add_root(os.path.join(TESTDATA, "empty_tree"))
        self.assertEqual([], list(crawl))

    def test_crawling(self):
        crawl = crawler.Crawler()
        crawl.add_root(os.path.join(TESTDATA, "test_tree"))
        
        seen_files = set()
        for au_file in crawl:
            # Each file has the filename in TPE1.
            tpe1 = au_file.mutagen_id3["TPE1"]
            self.assertTrue(au_file.path.endswith(tpe1.text[0]))
            # There should be a header.
            self.assertTrue(au_file.mp3_header is not None)
            # Make sure the fingerprint returned by the crawler matches
            # what is returned by fingerprint.compute().
            f_in = open(au_file.path)
            computed_fp = fingerprint.compute(f_in)
            self.assertEqual(computed_fp, au_file.fingerprint)
            # Each test file has the fingerprint in a UFID tag.
            # Make sure it matches.
            ufid = au_file.mutagen_id3["UFID:test"]
            self.assertEqual(ufid.data, au_file.fingerprint)
            # TODO(trow): We should have a better test of the frame count
            # and frame size.
            self.assertTrue(au_file.frame_count > 0)
            self.assertTrue(au_file.frame_size > 0)
            # Remember the basename of each file that we see.
            seen_files.add(os.path.basename(au_file.path))
        # Make sure we've seen all of the files we expect.
        self.assertEqual(15, len(seen_files))
        for a in ("A", "B", "C"):
            for b in range(5):
                self.assertTrue("%s%d.mp3" % (a, b) in seen_files)
        # Make sure we've seen the directories we expect.
        self.assertEqual(
            [os.path.join(TESTDATA, "test_tree", x) for x in ("A", "B", "C")],
            sorted(crawl.directories_seen))
        # We should have skipped one file.
        self.assertEqual(1, len(crawl.skipped_files))
        self.assertEqual(
            os.path.join(TESTDATA, "test_tree/A/invalid_file.mp3"),
            crawl.skipped_files[0][0])


if __name__ == "__main__":
    unittest.main()
