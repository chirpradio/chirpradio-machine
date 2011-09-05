
import unittest
from chirp.common import mp3_header_test
from chirp.stream import frame_splitter
from chirp.stream import message


class FrameSplitterTestCase(unittest.TestCase):

    def data_to_messages(self, data, block_size=137):
        message_list = []
        offset = 0
        while data:
            msg = message.Message()
            msg.payload, data = data[:block_size], data[block_size:]
            msg.message_type = message.BLOCK
            msg.connection_id = 123
            msg.connection_offset = offset
            msg.start_timestamp_ms = 100000  # Dummy start time
            msg.end_timestamp_ms = 100050  # Dummy end time
            offset += len(msg.payload)
            message_list.append(msg)
        return message_list

    def test_basic(self):
        # Find a header with the right frequency and build a dummy frame.
        for raw_hdr, hdr in mp3_header_test.VALID_MP3_HEADERS.items():
            if (hdr.sampling_rate_hz
                == frame_splitter.FrameSplitter.sampling_rate_hz):
                break
        frame_data = raw_hdr.ljust(hdr.frame_size, "a")

        # Make sure that some sequences of frames are properly split
        # into messages.
        for seq in (
            [ frame_data ],
            [ frame_data, frame_data ],
            [ frame_data, "junk", frame_data ],
            173 * [ frame_data ],
            173 * [ "junk", frame_data ],
            ):
            src = message.MessageSource()
            for msg in self.data_to_messages(''.join(seq)):
                src._add_message(msg)
            src._add_stop_message()

            fs = frame_splitter.FrameSplitter(src)
            fs.loop()
            for block in seq:
                msg = fs.get_next_message()
                self.assertFalse(msg.is_end_of_stream())
                if block == frame_data:
                    self.assertEqual(message.FRAME, msg.message_type)
                    self.assertEqual(frame_data, msg.payload)
                    self.assertEqual(str(msg.mp3_header), str(hdr))
                else:
                    self.assertEqual(message.BLOCK, msg.message_type)
                    self.assertEqual(block, msg.payload)
            remaining_messages = list(fs.get_all_messages())
            self.assertEqual(1, len(remaining_messages))
            self.assertTrue(remaining_messages[0].is_end_of_stream())


if __name__ == "__main__":
    unittest.main()

