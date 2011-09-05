
import os
import time
import unittest
from chirp.common import mp3_frame
from chirp.common import mp3_header
from chirp.stream import archiver
from chirp.stream import message


class ArchiverTestCase(unittest.TestCase):

    def test_dirname_and_open(self):
        arch = archiver.Archiver(message.MessageSource())
        arch.ROOT_DIR = "/tmp/archiver_test/%d" % time.time()
        test_ms = 1262544788772  # Jan 3, 2010, 12:53pm
        dirname = arch._dirname(test_ms)
        self.assertEqual("%s/2010/01/03/" % arch.ROOT_DIR, dirname)
        writer = arch._open(test_ms)
        self.assertTrue(os.path.isdir(dirname))
        self.assertEqual(test_ms, writer._start_ms)

    def test_rollover(self):
        # Set up a test archiver.
        src = message.MessageSource()
        arch = archiver.Archiver(src)
        arch.ROOT_DIR = "/tmp/archiver_test/%d" % time.time()
        arch.loop_in_thread()
        # The archiver's rollover count should start out at zero.
        self.assertEqual(0, arch.rollover_count)
        # Construct a test frame.
        test_ms = 1262648655000  # Jan 4, 2010, 5:43pm
        msg = message.Message()
        msg.message_type = message.FRAME
        msg.payload = mp3_frame.dead_air(1)  # 1ms = 1 frame
        msg.mp3_header = mp3_header.parse(msg.payload)
        msg.start_timestamp_ms = test_ms
        msg.end_timestamp_ms = test_ms + msg.mp3_header.duration_ms
        # Add the message to our source, twice, and wait for it to be
        # processed.  We add the message twice to work around the bug
        # whereby mutagen will choke on a single-frame MP3.
        src._add_message(msg)
        src._add_message(msg)
        src.wait_until_empty()
        # The archiver's rollover count should still be zero.
        self.assertEqual(0, arch.rollover_count)
        # Now advance the timestamp by one hour and re-add the message.
        # That should trigger a rollover.
        one_hour_in_ms = 1000 * 60 * 60
        msg.start_timestamp_ms += one_hour_in_ms
        msg.end_timestamp_ms += one_hour_in_ms
        src._add_message(msg)
        src.wait_until_empty()
        # Now there should have been a rollover.
        self.assertEqual(1, arch.rollover_count)
        src._add_message(msg)  # Again, to avoid the mutagen bug.
        # Shut down the archiver's thread, then wait for it to terminate.
        src._add_stop_message()
        arch.wait()


if __name__ == "__main__":
    unittest.main()

