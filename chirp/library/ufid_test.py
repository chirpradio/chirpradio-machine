#!/usr/bin/env python

import unittest

from chirp.common import timestamp
from chirp.library import constants
from chirp.library import ufid


class UFIDTest(unittest.TestCase):

    def test_basic(self):
        test_vol = 11
        test_ts_human = "20090102-030405"
        test_ts = timestamp.parse_human_readable(test_ts_human)
        test_fp = "1234" * 10
        # The UFID prefix should contain the volume and timestamp info.
        self.assertEqual("vol0b/%s/" % test_ts_human,  # 0b = 11
                         ufid.ufid_prefix(test_vol, test_ts))
        # The UFID should equal the UFID prefix + the fingerprint.
        test_ufid = ufid.ufid(test_vol, test_ts, test_fp)
        self.assertEqual(ufid.ufid_prefix(test_vol, test_ts) + test_fp,
                         test_ufid)
        # We should be able to make a tag too.
        test_tag = ufid.ufid_tag(test_vol, test_ts, test_fp)
        self.assertEqual("UFID", test_tag.FrameID)
        self.assertEqual(constants.UFID_OWNER_IDENTIFIER, test_tag.owner)
        self.assertEqual(test_ufid, test_tag.data)
        # Make sure we can parse information back out of the test UFID.
        vol, ts, fp = ufid.parse(test_ufid)
        self.assertEqual(test_vol, vol)
        self.assertEqual(test_ts, ts)
        self.assertEqual(test_fp, fp)
        # Raise ValueError if we try to parse a bad UFID.
        self.assertRaises(ValueError, ufid.parse, "bad")
        self.assertRaises(ValueError, ufid.parse, 
                          "vol01/20091399-666666/" + "1"*40)
        self.assertRaises(ValueError, ufid.parse, 
                          "vol01/20991001-123456" + "1"*40)


if __name__ == "__main__":
    unittest.main()
