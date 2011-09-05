#!/usr/bin/env python

import cStringIO
import hashlib
import unittest
from chirp.common import mp3_header_test
from chirp.library import fingerprint


class FingerprintTest(unittest.TestCase):

    def test_compute(self):
        raw_hdr, hdr = mp3_header_test.VALID_MP3_HEADERS.items()[0]
        frame_data = raw_hdr + ("x" * (hdr.frame_size - len(raw_hdr)))

        for i, seq in enumerate((
            [ frame_data ],
            [ "junk", frame_data ],
            [ frame_data, "junk" ],
            [ "junk", frame_data, "junk" ],
            [ frame_data, frame_data ],
            [ "junk", frame_data, frame_data ],
            [ frame_data, "junk", frame_data ],
            [ frame_data, frame_data, "junk" ],
            [ "junk", frame_data, "junk", frame_data ],
            [ frame_data, "junk", frame_data, "junk" ],
            [ "junk", frame_data, frame_data, "junk" ],
            [ "junk", frame_data, "junk", frame_data, "junk" ],
            )):
            sha1_calc = hashlib.sha1()
            for data in seq:
                if data == frame_data:
                    sha1_calc.update(data)
            expected_fingerprint = sha1_calc.hexdigest()

            stream = cStringIO.StringIO(''.join(seq))
            actual_fingerprint = fingerprint.compute(stream)
            self.assertEqual(expected_fingerprint, actual_fingerprint,
                             msg="Case #%d failed" % i)
            self.assertTrue(fingerprint.is_valid(actual_fingerprint))

        # We return None if we cannot find any valid frames.
        stream = cStringIO.StringIO('no valid MPEG frames')
        self.assertTrue(fingerprint.compute(stream) is None)

    def test_validate(self):
        self.assertTrue(fingerprint.is_valid("7" * 40))
        self.assertTrue(fingerprint.is_valid("a" * 40))

        self.assertFalse(fingerprint.is_valid(None))
        self.assertFalse(fingerprint.is_valid(1234567890))
        self.assertFalse(fingerprint.is_valid(""))
        self.assertFalse(fingerprint.is_valid("123"))
        self.assertFalse(fingerprint.is_valid("6" * 41))
        self.assertFalse(fingerprint.is_valid("x" * 40))
        self.assertFalse(fingerprint.is_valid("A" * 40))
        self.assertFalse(fingerprint.is_valid("-" + ("1" * 39)))


if __name__ == '__main__':
    unittest.main()
