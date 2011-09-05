#!/usr/bin/env python
import os

import cStringIO
import unittest

from chirp.common import ROOT_DIR
from chirp.library import analyzer
from chirp.library import audio_file


# TODO(trow): This is just a very crude smoke test, and should be expanded
# into a complete test of the analyzer's functionality.

class AnalyzerTest(unittest.TestCase):

    def test_basic(self):
        stream = cStringIO.StringIO('invalid data')
        au_file = audio_file.AudioFile()
        self.assertRaises(analyzer.InvalidFileError,
                          analyzer.analyze, stream, au_file)

    def test_known(self):
        f = os.path.join(ROOT_DIR,
                         "library/testdata/analyzer_test/test001.mp3")
        stream = open(f)
        au_file = audio_file.AudioFile()
        analyzer.analyze(stream, au_file)
        stream.close()

        self.assertTrue(au_file is not None)
        self.assertEqual("244227850107a0b44f1f554d5c960630e2693025",
                         au_file.fingerprint)
        self.assertEqual(150, au_file.frame_count)
        self.assertEqual(137173, au_file.frame_size)
        self.assertEqual(44100, au_file.mp3_header.sampling_rate_hz)
        self.assertAlmostEqual(280.32, au_file.mp3_header.bit_rate_kbps)  # VBR
        self.assertEqual(3918, au_file.duration_ms)
        self.assertEqual(au_file.frame_size, len(au_file.payload))

        # Volume, Deposit timestamp, Mutagen ID3 info and filename are
        # not set.
        self.assertEqual(None, au_file.volume)
        self.assertEqual(None, au_file.import_timestamp)
        self.assertEqual(None, au_file.mutagen_id3)
        self.assertEqual(None, au_file.path)


if __name__ == '__main__':
    unittest.main()

        
