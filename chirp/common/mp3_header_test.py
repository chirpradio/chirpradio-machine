#!/usr/bin/env python

###
### A unit test for mp3_header.py
###

import unittest
import sys
import mutagen.mp3
from chirp.common import mp3_header


VALID_MP3_HEADERS = {
    '\xff\xfb\x90\x64':
        mp3_header.MP3Header(bit_rate_kbps=128, sampling_rate_hz=44100,
                             channels=mp3_header.JOINT_STEREO,
                             padding=False, protected=False),
    '\xff\xfb\xb0\x00': 
        mp3_header.MP3Header(bit_rate_kbps=192, sampling_rate_hz=44100,
                             channels=mp3_header.STEREO,
                             padding=False, protected=False),
    '\xff\xfb\xb2\x00': 
        mp3_header.MP3Header(bit_rate_kbps=192, sampling_rate_hz=44100,
                             channels=mp3_header.STEREO,
                             padding=True, protected=False),
    }
    

INVALID_MP3_HEADERS = (
    '',
    'GARBAGE',
    '\xff\xf0\0\0',
    '\xff', '\xff' * 2, '\xff' * 3, '\xff' * 4,
    )


class ParseHeaderTest(unittest.TestCase):

    def test_is_complete(self):
        # All headers are specified in this header.
        hdr = mp3_header.MP3Header(sampling_rate_hz=44100,
                                   bit_rate_kbps=128,
                                   padding=False,
                                   protected=True,
                                   channels=mp3_header.JOINT_STEREO)
        self.assertTrue(hdr.is_complete())
        # This is an incomplete header.
        hdr = mp3_header.MP3Header(sampling_rate_hz=44100)
        self.assertFalse(hdr.is_complete())

    def test_parse(self):
        for valid, expected_hdr in VALID_MP3_HEADERS.items():
            hdr = mp3_header.parse(valid)
            self.assertTrue(hdr)
            self.assertTrue(hdr.is_complete())
            self.assertTrue(hdr.match(expected_hdr))
            # Now try with a non-zero offset.
            hdr = mp3_header.parse("xxxx" + valid + "xxxx", offset=4)
            self.assertTrue(hdr)
            self.assertTrue(hdr.is_complete())
            self.assertTrue(hdr.match(expected_hdr))

        for invalid in INVALID_MP3_HEADERS:
            self.assertTrue(mp3_header.parse(invalid) is None)

    def test_match(self):
        a = mp3_header.MP3Header(sampling_rate_hz=44100,
                                 bit_rate_kbps=128)
        self.assertTrue(a.match(a))
        self.assertTrue(a.match(mp3_header.MP3Header(sampling_rate_hz=44100)))
        self.assertFalse(a.match(mp3_header.MP3Header(bit_rate_kbps=192)))

    def test_find(self):
        # Check header-free data.
        self.assertEqual((None, 0), mp3_header.find(''))
        self.assertEqual((None, 5), mp3_header.find('12345'))
        self.assertEqual((None, 8), mp3_header.find('123\xff5678'))

        # Check data that might end with a truncated header
        self.assertEqual((None, 0), mp3_header.find('\xff'))
        self.assertEqual((None, 3), mp3_header.find('123\xff'))

        # Check that we can find a valid header that occurs near
        # a bogus 0xff synch byte.
        for raw_hdr, hdr in VALID_MP3_HEADERS.items():
            for test_data in (
                raw_hdr,
                '\xff' + raw_hdr,
                '123\xff\xff' + raw_hdr,
                '123\xff123\xff' + raw_hdr,
                raw_hdr + '\xff',
                ):
                found_hdr, offset = mp3_header.find(test_data)
                self.assertEqual(test_data.find(raw_hdr), offset)
                self.assertTrue(found_hdr is not None)
                self.assertTrue(hdr.match(found_hdr))

    def test_from_mutagen(self):
        mp3 = mutagen.mp3.MP3()

        class MockInfo(mutagen.mp3.MPEGInfo):
            def __init__(self):
                pass

        mp3.info = MockInfo()
        mp3.info.sample_rate = 12345
        mp3.info.bitrate = 123456
        mp3.info.mode = mp3_header.STEREO

        hdr = mp3_header.from_mutagen(mp3)
        self.assertEqual(12345, hdr.sampling_rate_hz)
        self.assertEqual(123.456, hdr.bit_rate_kbps)
        self.assertEqual(mp3_header.STEREO, hdr.channels)
        self.assertEqual("stereo", hdr.channels_str)

        self.assertEqual(None, hdr.protected)
        self.assertEqual(None, hdr.padding)


if __name__ == '__main__':
    unittest.main()
