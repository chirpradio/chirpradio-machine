
import unittest
from chirp.common import mp3_header
from chirp.stream import block_injector
from chirp.stream import message


class BlockInjectorTestCase(unittest.TestCase):

    def test_basic_injection(self):
        # A mock MP3 frame.
        mock_frame = message.Message()
        mock_frame.message_type = message.FRAME
        mock_frame.payload = "mock frame"
        mock_frame.mp3_header = mp3_header.MP3Header()
        mock_frame.mp3_header.duration_ms = 14000  # A 14-second-long frame

        # A mock block.
        mock_block = message.Message()
        mock_block.message_type = message.BLOCK
        mock_block.payload = "mock block"

        src = message.MessageSource()
        inj = block_injector.BlockInjector(src)
        inj.loop_in_thread()

        # Add 3 frames; since we haven't set a block payload yet, the
        # injector should just let these pass through
        for _ in xrange(3):
            src._add_message(mock_frame)
        src.wait_until_empty()
        
        # Define a block to be injected.
        injected_one = "Injected Payload"
        inj.set_block_payload(injected_one)

        # Now add 5 more frames.  A block should be injected after the first
        # (i.e. immediately) and fourth (i.e. after >30s elapse) frames.
        for _ in xrange(5):
            src._add_message(mock_frame)
        src._add_message(mock_block)
        # Also add our mock block.  Blocks should pass through the
        # injector without having any effect.
        src.wait_until_empty()

        # Define another block to be injected.
        injected_two = "Another injected payload"
        inj.set_block_payload(injected_two)

        # Now add 5 more frames.  Once again, a block should be
        # injected after the first and fourth frames.
        for _ in xrange(5):
            src._add_message(mock_frame)
        src.wait_until_empty()

        # Clear out the injected block.
        inj.set_block_payload(None)

        # Now add 10 more frames.  Since we cleared our injected block
        # payload, nothing should be injected.
        for _ in xrange(10):
            src._add_message(mock_frame)

        # Stop the source, and wait for the injector to settle.
        src._add_stop_message()
        inj.wait()

        # Now pull all of the messages out of our injector, and check that
        # we got what we expected.
        all_messages = list(inj.get_all_messages())
        # Our initial three frames, plus one more.
        for _ in xrange(4):
            self.assertTrue(all_messages.pop(0) is mock_frame)
        # Our first injected block.
        msg = all_messages.pop(0)
        self.assertEqual(message.BLOCK, msg.message_type)
        self.assertEqual(injected_one, msg.payload)
        # Three more frames.
        for _ in xrange(3):
            self.assertTrue(all_messages.pop(0) is mock_frame)
        # The next injected block.
        msg = all_messages.pop(0)
        self.assertEqual(message.BLOCK, msg.message_type)
        self.assertEqual(injected_one, msg.payload)
        # Another frame.
        self.assertTrue(all_messages.pop(0) is mock_frame)
        # Our mock block
        self.assertTrue(all_messages.pop(0) is mock_block)
        # Another frame.
        self.assertTrue(all_messages.pop(0) is mock_frame)
        # Another injected block, this time with our second payload.
        msg = all_messages.pop(0)
        self.assertEqual(message.BLOCK, msg.message_type)
        self.assertEqual(injected_two, msg.payload)
        # Three more frames.
        for _ in xrange(3):
            self.assertTrue(all_messages.pop(0) is mock_frame)
        # The next injected block.
        msg = all_messages.pop(0)
        self.assertEqual(message.BLOCK, msg.message_type)
        self.assertEqual(injected_two, msg.payload)
        # Eleven more frames.
        for _ in xrange(11):
            self.assertTrue(all_messages.pop(0) is mock_frame)
        # Finally, our end-of-stream marker.
        msg = all_messages.pop(0)
        self.assertTrue(msg.is_end_of_stream())
        # That's all folks!
        self.assertEqual(0, len(all_messages))


if __name__ == "__main__":
    unittest.main()

