
import unittest
from chirp.stream import message


class MessageTestCase(unittest.TestCase):

    def test_sha1(self):
        msg = message.Message()
        # We should start out with no payload
        self.assertTrue(msg.payload is None)
        # No payload == no sha1
        self.assertTrue(msg.payload_sha1 is None)
        self.assertTrue(msg.payload_hex_sha1 is None)
        # Now set a payload, and make sure that we get the expected SHA1.
        # This example is from Wikipedia's page on the SHA hash functions.
        msg.payload = "The quick brown fox jumps over the lazy dog"
        expected_hex_sha1 = "2fd4e1c67a2d28fced849ee1bb76e7391b93eb12"
        # Convert the expected SHA1 from hex to binary.
        expected_sha1 = "".join([chr(int(expected_hex_sha1[2*i:2*i+2], 16))
                                 for i in xrange(len(expected_hex_sha1)/2)])
        self.assertEqual(expected_sha1, msg.payload_sha1)
        self.assertEqual(expected_hex_sha1, msg.payload_hex_sha1)

    def test_error_helpers(self):
        msg = message.Message()
        msg.message_type = message.BLOCK
        self.assertFalse(msg.is_error())
        self.assertFalse(msg.is_end_of_stream())
        msg.set_error(message.READ_ERROR, ("foo", "bar"))
        self.assertTrue(msg.is_error())
        self.assertFalse(msg.is_end_of_stream())
        msg.set_error(message.END_OF_STREAM_ERROR, ("foo", "bar"))
        self.assertTrue(msg.is_error())
        self.assertTrue(msg.is_end_of_stream())


class MessageSourceTestCase(unittest.TestCase):

    def test_basics(self):
        src = message.MessageSource()
        # The queue starts out empty.
        self.assertTrue(src.get_next_message(timeout=0.01) is None)

        # Check that we can add a test message and then get it back out.
        msg = message.Message()
        msg.message_type = message.BLOCK
        msg.payload = "My test message"
        src._add_message(msg)
        self.assertTrue(src.get_next_message() is msg)
        # The queue should now be empty.
        self.assertTrue(src.get_next_message(timeout=0.01) is None)

        # Check that we can add a stop message, then get it back out.
        src._add_stop_message()
        msg = src.get_next_message()
        self.assertTrue(msg.is_end_of_stream())
        # The queue should now be empty.
        self.assertTrue(src.get_next_message(timeout=0.01) is None)


class TestMessageConsumer(message.MessageConsumer):
    """A test message consumer that simply appends all consumed messages
    to a list."""

    all_messages = []

    def _process_message(self, msg):
        self.all_messages.append(msg)


class MessageConsumerTestCase(unittest.TestCase):

    def test_basics(self):
        # Construct a source and connect it to our test consumer.
        src = message.MessageSource()
        con = TestMessageConsumer(src)
        # Run the consumer in a separate thread.
        con.loop_in_thread()

        # Add a test message and a stop message to our source.
        msg = message.Message()
        msg.message_type = message.BLOCK
        msg.payload = "My test message"
        src._add_message(msg)
        src._add_stop_message()

        # Now wait for consumer to settle, and make sure that we
        # received both messages.
        con.wait()
        self.assertEqual(2, len(con.all_messages))
        self.assertTrue(con.all_messages[0] is msg)
        self.assertTrue(con.all_messages[1].is_end_of_stream())


class MessageTeeTestCase(unittest.TestCase):

    def test_basics(self):
        # Construct a source and connect it to a tee.
        src = message.MessageSource()
        tee = message.MessageTee(src, 3)
        # The tee should have 3 outputs.
        self.assertEqual(3, len(tee.outputs))
        # Run the tee in a separate thread.
        tee.loop_in_thread()

        # Add a test message and a stop message to our source.
        msg = message.Message()
        msg.message_type = message.BLOCK
        msg.payload = "My test message"
        src._add_message(msg)
        src._add_stop_message()

        # Wait for the tee to settle, then make sure that all of the
        # outputs contain the expected messages.
        tee.wait()
        for out in tee.outputs:
            out_msg = out.get_next_message()
            self.assertTrue(out_msg is msg)
            out_msg = out.get_next_message()
            self.assertTrue(out_msg.is_end_of_stream())
            out_msg = out.get_next_message(timeout=0.01)
            self.assertTrue(out_msg is None)

        
if __name__ == "__main__":
    unittest.main()

