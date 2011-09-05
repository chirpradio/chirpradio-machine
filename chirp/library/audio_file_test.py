#!/usr/bin/env python

import os
import unittest

import mutagen.id3
import mutagen.mp3

from chirp.common import mp3_header, ROOT_DIR
from chirp.library import audio_file
from chirp.library import constants
from chirp.library import id3_text
from chirp.library import ufid


TESTDATA = os.path.join(ROOT_DIR, "library/testdata/audio_file_test")


# This is used in other tests.
def get_test_audio_file(n):
    """Generates a test AudioFile object.

    Args:
      n: An integer >= 0; a distinct AudioFile object is generated for
        each value of n.

    Returns:
      An AudioFile object, all of whose fields have been populated with
      test data.
    """
    au_file = audio_file.AudioFile()
    au_file.volume = n
    au_file.import_timestamp = 1229997336 + n
    au_file.fingerprint = "%016x" % n
    au_file.album_id = abs(hash("TALB %d" % n))
    au_file.frame_count = 12345 + (n % 10)
    au_file.frame_size = (8 << 20) + (n << 10)
    au_file.mp3_header = mp3_header.MP3Header(bit_rate_kbps=192+n,
                                              sampling_rate_hz=44100+n,
                                              channels=(n % 4))
    au_file.duration_ms = (180 + n) * 1000
    # Assemble fake ID3 tags.
    au_file.mutagen_id3 = mutagen.id3.ID3()
    tpe1 = mutagen.id3.TPE1(text=["TPE1 %d" % n])
    au_file.mutagen_id3.add(tpe1)
    tit2 = mutagen.id3.TIT2(text=["TIT2 %d" % n])
    au_file.mutagen_id3.add(tit2)
    talb = mutagen.id3.TALB(text=["TALB %d" % n])
    au_file.mutagen_id3.add(talb)
    trck = mutagen.id3.TRCK(text=["%d/7" % ((n % 7) + 1)])
    au_file.mutagen_id3.add(trck)
    talb = mutagen.id3.TPUB(text=["  Bad    whitespace    "])
    au_file.mutagen_id3.add(talb)
    # Finally return the thing.
    return au_file

get_test_audio_file.__test__ = False  # not a test itself


TEST_VOL = 65
TEST_TS = 1230430574
TEST_FP = "7" * 40
TEST_UFID = ufid.ufid(TEST_VOL, TEST_TS, TEST_FP)
TEST_UFID_PREFIX = ufid.ufid_prefix(TEST_VOL, TEST_TS)


class AudioFileTest(unittest.TestCase):

    def test_basic(self):
        # Assemble a basic test object.
        au_file = audio_file.AudioFile()
        au_file.volume = TEST_VOL
        au_file.import_timestamp = TEST_TS
        au_file.fingerprint = TEST_FP

        # Check the generated UFID.
        self.assertEqual(TEST_UFID, au_file.ufid())
        
        # Check the generated UFID tag.
        ufid_tag = au_file.ufid_tag()
        self.assertEqual("UFID", ufid_tag.FrameID)
        self.assertEqual(constants.UFID_OWNER_IDENTIFIER, ufid_tag.owner)
        self.assertEqual(TEST_UFID, ufid_tag.data)

        # Check the generatred path and filename info.
        self.assertEqual(TEST_UFID_PREFIX,
                         au_file.canonical_directory())
        self.assertEqual("foo/" + TEST_UFID_PREFIX,
                         au_file.canonical_directory(prefix="foo"))

        self.assertTrue(TEST_FP + ".mp3", au_file.canonical_filename())

        self.assertTrue(TEST_UFID + ".mp3", au_file.canonical_path())
        self.assertTrue("foo/" + TEST_UFID + ".mp3",
                        au_file.canonical_path(prefix="foo"))

    def test_tag_accessors(self):
        test_au = audio_file.AudioFile()
        self.assertTrue(test_au.tpe1() is None)
        self.assertTrue(test_au.tit2() is None)
        self.assertTrue(test_au.talb() is None)

        test_au.mutagen_id3 = mutagen.id3.ID3()
        self.assertTrue(test_au.tpe1() is None)
        self.assertTrue(test_au.tit2() is None)
        self.assertTrue(test_au.talb() is None)

        test_au = get_test_audio_file(0)
        self.assertEqual(u"TPE1 0", test_au.tpe1())
        self.assertEqual(u"TIT2 0", test_au.tit2())
        self.assertEqual(u"TALB 0", test_au.talb())

    def test_scan_fast_tag_handling(self):
        test_mp3 = mutagen.mp3.MP3()
        class MockInfo(object): pass
        test_mp3.info = MockInfo()
        test_mp3.add_tags()
        test_mp3.tags.add(ufid.ufid_tag(TEST_VOL, TEST_TS, TEST_FP))
        test_mp3.tags.add(mutagen.id3.TLEN(text=u"11111"))
        test_mp3.tags.add(mutagen.id3.TXXX(
                desc=constants.TXXX_ALBUM_ID_DESCRIPTION,
                text=[u"222"]))
        test_mp3.tags.add(mutagen.id3.TXXX(
                desc=constants.TXXX_FRAME_COUNT_DESCRIPTION,
                text=[u"333"]))
        test_mp3.tags.add(mutagen.id3.TXXX(
                desc=constants.TXXX_FRAME_SIZE_DESCRIPTION,
                text=["444"]))
        for tag in test_mp3.tags.values():
            id3_text.standardize(tag)
        test_mp3.info.sample_rate = 5555
        test_mp3.info.bitrate = 6666
        test_mp3.info.mode = 2

        au_file = audio_file.scan_fast("/test/path",
                                       _read_id3_hook=lambda p: test_mp3)
        self.assertTrue(audio_file is not None)
        self.assertEqual("/test/path", au_file.path)
        self.assertEqual(TEST_VOL, au_file.volume)
        self.assertEqual(TEST_TS, au_file.import_timestamp)
        self.assertEqual(TEST_FP, au_file.fingerprint)
        self.assertEqual(11111, au_file.duration_ms)
        self.assertEqual(222, au_file.album_id)
        self.assertEqual(333, au_file.frame_count)
        self.assertEqual(444, au_file.frame_size)
        self.assertEqual(5555, au_file.mp3_header.sampling_rate_hz)
        self.assertEqual(6.666, au_file.mp3_header.bit_rate_kbps)
        self.assertEqual(2, au_file.mp3_header.channels)

    def test_scan_no_chirp_tags(self):
        path = os.path.join(TESTDATA, "no_chirp_tags.mp3")
        fast_au_file = audio_file.scan_fast(path)
        self.assertEqual(None, fast_au_file.volume)
        self.assertEqual(None, fast_au_file.import_timestamp)
        self.assertEqual(None, fast_au_file.fingerprint)
        self.assertEqual(None, fast_au_file.frame_count)
        self.assertEqual(None, fast_au_file.frame_size)
        # File doesn't have a TLEN tag.
        self.assertEqual(None, fast_au_file.duration_ms)
        self.assertEqual(path, fast_au_file.path)

        slow_au_file = audio_file.scan(path)
        # The file's fingerprint is stashed in the UFID:test tag.
        fp = slow_au_file.mutagen_id3.get("UFID:test").data
        self.assertEqual(None, slow_au_file.volume)
        self.assertEqual(None, slow_au_file.import_timestamp)
        self.assertEqual(fp, slow_au_file.fingerprint)
        # Test file contains 150 frames for a total of 137,173 bytes.
        self.assertEqual(150, slow_au_file.frame_count)
        self.assertEqual(137173, slow_au_file.frame_size)
        self.assertEqual(path, slow_au_file.path)

    def test_scan_has_chirp_tags(self):
        path = os.path.join(TESTDATA, "has_chirp_tags.mp3")
        fast_au_file = audio_file.scan_fast(path)
        slow_au_file = audio_file.scan(path)

        self.assertEqual(path, fast_au_file.path)
        self.assertEqual(path, slow_au_file.path)

        # This volume and timestamp is extracted from the UFID.
        self.assertEqual(123, fast_au_file.volume)
        self.assertEqual(1230519180, fast_au_file.import_timestamp)

        self.assertEqual(3918, fast_au_file.duration_ms)
        self.assertEqual(slow_au_file.duration_ms, fast_au_file.duration_ms)

        self.assertEqual(slow_au_file.fingerprint, fast_au_file.fingerprint)

        # Test file contains 150 frames for a total of 137,173 bytes.
        self.assertEqual(150, slow_au_file.frame_count)
        self.assertEqual(137173, slow_au_file.frame_size)
        self.assertEqual(path, slow_au_file.path)

        # The fast scan picks up an album ID stored in the tags,
        # the slow scan doesn't.  The test file is marked as having
        # an album ID of 123454321.
        self.assertEqual(123454321, fast_au_file.album_id)
        self.assertEqual(None, slow_au_file.album_id)


if __name__ == "__main__":
    unittest.main()
