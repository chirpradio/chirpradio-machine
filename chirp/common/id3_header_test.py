#!/usr/bin/env python

import unittest
import mutagen.mp3
from chirp.common import id3_header
from chirp.common import mp3_header_test


class ID3HeaderTest(unittest.TestCase):

    # vmaj = 4, vrev = 0, flags = 0
    prefix = b"ID3\x04\x00\x00"

    def test_create(self):
        # Construct a test ID3 header with a few text tags.
        tpe1_utf8 = b"Von S\xc3\xbcdenfed"
        tpe1 = tpe1_utf8.decode("utf-8")

        tit2 = b"Very Long String" * 100
        talb = b"Bar"
        data = id3_header.create(((b"TPE1", str(tpe1)),
                                  (b"TIT2", tit2),
                                  (b"TALB", talb)))
        # Make sure that it starts with the expected prefix.
        self.assertTrue(data.startswith(self.prefix))
        # Ensure that utf-8 encoding is used inside of our tag.
        self.assertTrue(tpe1_utf8 in data)

        # Write our header out to disk, along with some dummy MP3 frames.
        # (We need the extra frames because mutagen refuses to read an empty
        # MP3 file.)
        test_file = "id3_header_test.data"
        fh = open(test_file, "wb")
        fh.write(data)
        raw_hdr, hdr = list(mp3_header_test.VALID_MP3_HEADERS.items())[0]
        frame_data = raw_hdr.ljust(hdr.frame_size, b"a")
        fh.write(frame_data * 2)
        fh.close()

        # Now read back the file we just wrote using mutagen.
        mp3 = mutagen.mp3.MP3(test_file)
        # Make sure that what we read has the expected tags.
        self.assertEqual(3, len(mp3))
        self.assertTrue("TPE1" in mp3)
        self.assertTrue("TIT2" in mp3)
        self.assertTrue("TALB" in mp3)
        # Everything should be encoded as utf-8.
        for val in list(mp3.values()):
            self.assertEqual(3, val.encoding)
        # All tags should have the expected values.
        self.assertEqual([tpe1], mp3["TPE1"].text)
        self.assertEqual([tit2.decode()], mp3["TIT2"].text)
        self.assertEqual([talb.decode()], mp3["TALB"].text)

    size_test_cases = ((b"\x00\x00\x00\x00", 0),
                       (b"\x00\x00\x00\x01", 1),
                       (b"\x00\x00\x01\x00", 1<<7),
                       (b"\x00\x01\x00\x00", 1<<14),
                       (b"\x01\x00\x00\x00", 1<<21),
                       )

    def test_test_header(self):
        for raw_size, cooked_size in self.size_test_cases:
            self.assertEqual(self.prefix + raw_size,
                             id3_header.create_test_header(cooked_size))

    def test_parse(self):
        self.assertEqual(None, id3_header.parse_size(b""))
        self.assertEqual(None, id3_header.parse_size(b"short"))
        self.assertEqual(None, id3_header.parse_size(b"1234567890"))

        # An ID3 header that claims to have size 0 is considered invalid.
        zero_hdr = id3_header.create_test_header(0)
        self.assertEqual(None, id3_header.parse_size(zero_hdr))

        for test_size in (1, 1<<7, 1<<14, 1<<21):
            test_hdr = id3_header.create_test_header(test_size)
            for offset in (0, 5):
                data = b"x" * offset + test_hdr
                self.assertEqual(test_size,
                                 id3_header.parse_size(data, offset=offset))

    def test_find(self):
        test_raw_size, test_cooked_size = self.size_test_cases[-1]
        header = self.prefix + test_raw_size
        padding = b"x" * 10

        self.assertEqual((None, 0), id3_header.find_size(b""))
        self.assertEqual((None, 1), id3_header.find_size(b"x"))
        self.assertEqual((None, 1), id3_header.find_size(b"xI"))
        self.assertEqual((None, 12), id3_header.find_size(b"xI" + padding))
        self.assertEqual((test_cooked_size, 0),
                         id3_header.find_size(header))
        self.assertEqual((test_cooked_size, 0),
                         id3_header.find_size(header + padding))
        self.assertEqual((test_cooked_size, 3),
                         id3_header.find_size(b"xIx" + header))
        self.assertEqual((test_cooked_size, 3),
                         id3_header.find_size(b"xIx" + header + padding))


if __name__ == "__main__":
    unittest.main()

