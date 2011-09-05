"""
A BlockInjector periodically inserts a BLOCK message into the
message sequence.  It is typically used to insert ID3 tags into
a stream.
"""

import threading
from chirp.stream import message


class BlockInjector(message.MessageConsumer, message.MessageSource):

    # This defined how often (in milliseconds) to inject the block.
    injection_frequency_ms = 30000  # = 30s

    def __init__(self, src):
        message.MessageConsumer.__init__(self, src)
        message.MessageSource.__init__(self)
        self._lock = threading.Lock()
        # The lock guards these two attributes.
        self._message_to_inject = None
        self._countdown_ms = 0

    def _process_message(self, msg):
        self._add_message(msg)
        if msg.message_type == message.FRAME:
            self._lock.acquire()
            try:
                # If we have a message to inject, decrement the countdown
                # by the length of the previous frame.
                if self._message_to_inject is not None:
                    self._countdown_ms -= msg.mp3_header.duration_ms
                    # If our countdown has reached zero, inject the
                    # message and then reset the countdown.
                    if self._countdown_ms <= 0:
                        self._add_message(self._message_to_inject)
                        self._countdown_ms = self.injection_frequency_ms
            finally:
                self._lock.release()

    def set_block_payload(self, block_payload):
        """Sets the payload of the block to periodically add to the stream.

        Args:
          block_payload: A string, or None to clear the injected block.
        """
        self._lock.acquire()
        try:
            if block_payload is None:
                self._message_to_inject = None
                # TODO(trow): Can we inject something into the stream to
                # clear the previously streamed tags?
                return
            # If the same payload gets set twice, do nothing
            if (self._message_to_inject is not None
                and self._message_to_inject.payload == block_payload):
                return
            msg = message.Message()
            msg.message_type = message.BLOCK
            msg.payload = block_payload
            self._message_to_inject = msg
            # Reset the countdown; this ensures that the new block will
            # be injected immediately.
            self._countdown_ms = 0
        finally:
            self._lock.release()
            
