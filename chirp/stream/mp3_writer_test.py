#!/usr/bin/env python

import unittest
import mutagen.id3
import mutagen.mp3
from chirp.common import mp3_frame
from chirp.common import mp3_header
from chirp.library import constants
from chirp.stream import message
from chirp.stream import mp3_writer

class MP3WriterTestCase(unittest.TestCase):

    def test_basic(self):
        # Create a test MP3Writer.
        test_prefix = "/tmp/mp3_writer_test"
        test_start_ms = 1262479500000
        writer = mp3_writer.MP3Writer(prefix=test_prefix,
                                      start_ms=test_start_ms)
        self.assertEqual("/tmp/mp3_writer_test-20100102-184500.000.mp3",
                         writer.path)

        # Set up a dummy MP3 frame (corresonding to our dead air)
        # message and repeatedly add it to the writer.
        msg = message.Message()
        msg.message_type = message.FRAME
        msg.payload = mp3_frame.dead_air(1)  # 1 ms => a single frame
        msg.mp3_header = mp3_header.parse(msg.payload)

        # Set up a dummy block message.
        block_msg = message.Message()
        block_msg.message_type = message.BLOCK
        block_msg.payload = "FOO BAR BAZ"

        # Now repeatedly add the test message to the writer.
        time_ms = test_start_ms
        for i in xrange(10):
            msg.start_timestamp_ms = time_ms
            time_ms += msg.mp3_header.duration_ms
            msg.end_timestamp_ms = time_ms
            writer.write(msg)
            # Also add the block message in.  It should be ignored.
            writer.write(block_msg)

        # At this point the duration should be 10x the individual frame
        # duration.
        self.assertAlmostEqual(10*msg.mp3_header.duration_ms,
                               writer.duration_ms)
        # We should also have the correct frame count and size.
        self.assertEqual(10, writer.frame_count)
        self.assertEqual(10*len(msg.payload), writer.frame_size)

        # The file should be fully flushed out to disk, so we should be
        # able to inspect it with mutagen and see something with the
        # expected duration and tags.
        partial_mp3 = mutagen.mp3.MP3(writer.path)
        self.assertAlmostEqual(writer.duration_ms/1000,  # mutagen uses seconds
                               partial_mp3.info.length)
        # These are only some of the tags.
        self.assertTrue("TRSN" in partial_mp3)
        self.assertEqual([u"CHIRP Radio"], partial_mp3["TRSN"].text)
        self.assertTrue("TIT1" in partial_mp3)
        self.assertEqual([u"20100102-184500.000 to ???????????????????"],
                         partial_mp3["TIT1"].text)

        # Now close the writer.  After that, we should be able to open
        # it with mutagen and see the final tags.
        writer.close()
        final_mp3 = mutagen.mp3.MP3(writer.path)
        self.assertAlmostEqual(writer.duration_ms/1000, final_mp3.info.length)
        # Check finalized title.
        self.assertEqual([u"20100102-184500.000 to 20100102-184500.261"],
                         final_mp3["TIT1"].text)
        # Check frame count.
        self.assertTrue(constants.TXXX_FRAME_COUNT_KEY in final_mp3)
        self.assertEqual([unicode(writer.frame_count)],
                         final_mp3[constants.TXXX_FRAME_COUNT_KEY].text)
        # Check frame size.
        self.assertTrue(constants.TXXX_FRAME_SIZE_KEY in final_mp3)
        self.assertEqual([unicode(writer.frame_size)],
                         final_mp3[constants.TXXX_FRAME_SIZE_KEY].text)
        # Check UFID.
        self.assertTrue(constants.MUTAGEN_UFID_KEY in final_mp3)
        self.assertEqual(
            "volff/20100102-184500/8f5bb4f4b0ded8d29baa778f121ef3063db7a3f7",
            final_mp3[constants.MUTAGEN_UFID_KEY].data)

        # It should be safe to call close twice.
        writer.close()

                            
if __name__ == "__main__":
    unittest.main()
