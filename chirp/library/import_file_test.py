
import os
import time
import unittest

import mutagen.id3

from chirp.common import mp3_header_test
from chirp.library import audio_file
from chirp.library import constants
from chirp.library import fingerprint
from chirp.library import import_file
from chirp.library import ufid


TEST_VOL = 123
TEST_TS =  1228080954

TEST_TAG_LIST = (
    mutagen.id3.TRCK(text=["3/7"], encoding=0),
    mutagen.id3.TPE1(text=["Fall, The"], encoding=0),
    mutagen.id3.TIT2(text=["Song Title [With Tag]"], encoding=0),
    )


class ImportFileTest(unittest.TestCase):

    def setUp(self):
        self.temp_dir = "/tmp/import_file_test.%d" % int(1000000 * time.time())
        os.mkdir(self.temp_dir)
        self.prefix = os.path.join(self.temp_dir, "prefix")
        os.mkdir(self.prefix)

    def tearDown(self):
        os.system("rm -rf %s" % self.temp_dir)
    
    def create_test_file(self, tag_list):
        raw_hdr, hdr = mp3_header_test.VALID_MP3_HEADERS.items()[0]
        num_frames = 1000
        frame_data = raw_hdr.ljust(hdr.frame_size, "!")
        payload = num_frames * frame_data

        mutagen_id3 = mutagen.id3.ID3()
        for tag in tag_list:
            mutagen_id3.add(tag)

        path = os.path.join(self.temp_dir,
                            "%d.mp3" % int(1000000 * time.time()))
        mutagen_id3.save(path)
        out_fh = open(path, "a")
        out_fh.write(payload)
        out_fh.close()

        return path

    create_test_file.__test__ = False  # not a test itself

    def test_read_standardize_write_file(self):
        path = self.create_test_file(TEST_TAG_LIST)
        au_file = audio_file.scan(path)
        self.assertTrue(au_file is not None)
        au_file.volume = TEST_VOL
        au_file.import_timestamp = TEST_TS
        au_file.album_id = 77777
        # Inject the necessary UFID tag.
        au_file.mutagen_id3[constants.UFID_OWNER_IDENTIFIER] = ufid.ufid_tag(
            TEST_VOL, TEST_TS, au_file.fingerprint)

        import_file.standardize_file(au_file)
        # Do some basic checks
        for tag in au_file.mutagen_id3.values():
            self.assertTrue(
                (tag.FrameID in constants.ID3_TAG_WHITELIST
                 or tag.HashKey in constants.ID3_TAG_WHITELIST))
        for frame_id in constants.ID3_TAG_REQUIRED:
            self.assertTrue(frame_id in au_file.mutagen_id3)

        # Write the standardized file out, then re-read it and make sure
        # that everything is as we expected.
        alt_prefix = os.path.join(self.prefix, "alt")
        new_path = import_file.write_file(au_file, alt_prefix)
        new_au_file = audio_file.scan(new_path)
        self.assertEqual(sorted(au_file.mutagen_id3.keys()),
                         sorted(new_au_file.mutagen_id3.keys()))
        for key in au_file.mutagen_id3.keys():
            self.assertEqual(repr(au_file.mutagen_id3[key]),
                             repr(new_au_file.mutagen_id3[key]))
        self.assertEqual(au_file.fingerprint, new_au_file.fingerprint)
        self.assertEqual(au_file.payload, new_au_file.payload)


if __name__ == "__main__":
    unittest.main()
