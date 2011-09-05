#!/usr/bin/python2.5

import cStringIO
import unittest

from chirp.common import id3_header
from chirp.common import mp3_frame
from chirp.common import mp3_header
from chirp.common import mp3_header_test


class SplitTest(unittest.TestCase):

    def test_split(self):
        raw_hdr, hdr = mp3_header_test.VALID_MP3_HEADERS.items()[0]
        frame_data = raw_hdr.ljust(hdr.frame_size, "a")
        # Set up a fragment of a header
        partial_header = raw_hdr[:3]
        short_frame = frame_data[:25]
        assert len(short_frame) < len(frame_data)

        id3_data = id3_header.create_test_header(77).ljust(77, "b")

        # An ID3 tag with a valid frame tag stashed inside.
        evil_id3_data = id3_header.create_test_header(50) + raw_hdr
        evil_id3_data = evil_id3_data.ljust(50, "c")

        for seq in (
            [ frame_data ],
            [ frame_data, frame_data ],
            [ 'junk', frame_data ],
            [ 'junk', frame_data, frame_data ],
            [ 'junk', frame_data, frame_data, 'junk' ],
            [ 'junk', frame_data, frame_data, 'junk', frame_data ],
            # Check handling of truncated headers and frames.
            [ partial_header ],
            [ 'junk', partial_header ],
            [ 'junk', short_frame ],
            [ frame_data, partial_header ],
            [ frame_data, short_frame ],
            [ frame_data, 'junk', short_frame ],
            [ frame_data, 'junk', partial_header],
            # ID3 headers mixed in
            [ id3_data, frame_data ],
            [ frame_data, id3_data ],
            [ id3_data, frame_data ],
            [ id3_data, frame_data, id3_data ],
            [ evil_id3_data, frame_data, "junk" ],
            [ "junk", frame_data, evil_id3_data, frame_data ],
            [ "junk", frame_data, evil_id3_data, frame_data, "junk" ],
            [ "junk" + evil_id3_data, id3_data, frame_data, evil_id3_data ],
            # Some longer sequences
            500 * [ frame_data ],
            500 * [ "junk", frame_data, id3_data, frame_data ]
            ):
            data = ''.join(seq)
            stream = cStringIO.StringIO(data)
            split_stream = list(mp3_frame.split(stream))
            split_stream_from_blocks = list(mp3_frame.split_blocks(iter(seq)))
            split_stream_from_one_block = mp3_frame.split_one_block(data)
            # Make sure that the sequences of header/frame data pairs
            # returned by mp3_frame.split(), mp3_frame.split_blocks()
            # and mp3_frame.split_one_block() matche what we would
            # expect.
            self.assertEqual(len(seq), len(split_stream))
            for expected_data, (actual_hdr, data) in zip(seq, split_stream):
                self.assertEqual(expected_data, data)
                if expected_data == frame_data:
                    self.assertTrue(actual_hdr is not None)
                    self.assertTrue(actual_hdr.match(hdr))
                    self.assertEqual(hdr.frame_size, len(frame_data))
                else:
                    self.assertTrue(actual_hdr is None)

            self.assertEqual(len(seq), len(split_stream_from_blocks))
            for (hdr1, data1), (hdr2, data2) in zip(split_stream,
                                                    split_stream_from_blocks):
                self.assertEqual(str(hdr1), str(hdr2))
                self.assertEqual(data1, data2)

            self.assertEqual(len(seq), len(split_stream_from_one_block))
            for (hdr1, data1), (hdr2, data2) in zip(
                split_stream, split_stream_from_one_block):
                self.assertEqual(str(hdr1), str(hdr2))
                self.assertEqual(data1, data2)


class DeadAirTest(unittest.TestCase):

    def test_dead_air(self):
        # Request ~100ms of dead air
        data = mp3_frame.dead_air(100)
        # Split the returned data into frames.
        frames = list(mp3_frame.split_one_block(data))
        # Four MPEG frames worth of data should be returned.
        self.assertEqual(4, len(frames))
        # All frames should be of the same type.
        self.assertEqual(1, len(set(str(hdr) for hdr, _ in frames)))
        hdr = frames[0][0]
        # These should be 44.1Khz, 112Kbps frames
        self.assertEqual(44100, hdr.sampling_rate_hz)
        self.assertEqual(112, hdr.bit_rate_kbps)


if __name__ == '__main__':
    unittest.main()

