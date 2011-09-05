"""
The Message class, and a few helpful related base classes.
"""

import hashlib
import Queue
import time
from chirp.stream import looper

# Message Types
CONNECTED = "Connected"        # New connection initiated.
RESPONSE = "Response"          # HTTP response received.
BLOCK = "Block"                # A chunk of raw data.
FRAME = "Frame"                # An MP3 frame.
ERROR = "Error"                # An error.

# Error Types
CONNECT_TIMEOUT_ERROR = "Connect Timeout Error"
CONNECT_ERROR = "Connect Error"
REQUEST_ERROR = "Request Error"
READ_TIMEOUT_ERROR = "Read Timeout Error"
READ_ERROR = "Read Error"
MISSING_HEADERS_ERROR = "Missing HTTP Headers Error"
MALFORMED_HEADERS_ERROR = "Malformed HTTP Headers Error"
BAD_REDIRECT_ERROR = "Bad Redirect Error"
END_OF_STREAM_ERROR = "End of Stream Error"


class Message(object):
    """Represents a chunk of information produced by a connection to a
    data stream.  It can either represent data extracted from the stream,
    or a change to the underlying connection.
    """
    message_type = None

    # Error information.  Only set on ERROR messages.
    error_type = None
    error_code = None  # If appropriate, an Unix errno.
    error_text = None  # A human-readable error message.

    # An identifier for the data stream connection that produced this
    # message.
    connection_id = None
    # Our offset in the data stream when this message was generated.
    connection_offset = None

    # The interval of time that spanned the production of this
    # message.
    start_timestamp_ms = None
    end_timestamp_ms = None

    # The host, port and path we connected to.
    # Only set for CONNECT messages.
    connect_host = None
    connect_port = None
    connect_path = None

    # The raw data associated with this message.
    # Only set for BLOCK and FRAME messages.
    payload = None

    # The SHA1 of the raw data associated with this message.
    # Only set for BLOCK or FRAME messages.
    @property
    def payload_sha1(self):
        if self.payload is None:
            return None
        if self._cached_payload_sha1 is None:
            self._cached_payload_sha1 = hashlib.sha1(self.payload).digest()
        return self._cached_payload_sha1

    _cached_payload_sha1 = None

    @property
    def payload_hex_sha1(self):
        sha1 = self.payload_sha1
        if sha1 is None:
            return None
        return ''.join('%02x' % ord(x) for x in sha1)

    # The integral HTTP response code.
    # This is set only on RESPONSE messages.
    http_status_code = None

    # The HTTP headers returned upon connecting to the data source.
    # This is set only on RESPONSE messages.
    http_headers = None

    # MP3 frame header information.  This is only set on FRAME
    # objects.
    mp3_header = None

    def __str__(self):
        info = [self.message_type]
        if self.message_type == ERROR:
            info.extend([self.error_type,
                         str(self.error_code or ""),
                         self.error_text or ""])
        if self.payload:
            info.append("len=%d" % len(self.payload))
        return "[Msg %s]" % "/".join(info)

    def set_error(self, error_type, err):
        """Initialize this object as an error message."""
        self.message_type = ERROR
        self.error_type = error_type
        if err:
            self.error_code, self.error_text = err

    def is_error(self):
        return self.message_type == ERROR

    def is_end_of_stream(self):
        return self.is_error() and self.error_type == END_OF_STREAM_ERROR


class MessageSource(object):
    """Base class for an object that produces a stream of Message objects.

    This works by maintaining an internal queue of messages.
    """

    def __init__(self):
        self._message_queue = Queue.Queue()

    def _add_message(self, msg):
        """Add a new message onto the end of the stream."""
        self._message_queue.put(msg)

    def _add_stop_message(self):
        """Add a new end-of-stream message onto the end of the stream."""
        msg = Message()
        msg.message_type = ERROR
        msg.error_type = END_OF_STREAM_ERROR
        self._add_message(msg)

    def get_next_message(self, timeout=None):
        """Block until the next message is available, then return it.

        Args:
          timeout: An optional timeout, in seconds.

        Returns:
          The next Message object, or None if we time out.
        """
        try:
            return self._message_queue.get(timeout=timeout)
        except Queue.Empty:
            return None

    def get_all_messages(self):
        """Try to yield all messages in the queue.

        Note that this is not thread-safe.  For best results, only call
        this after you know that no more messages will be added and that
        you are the only reader.
        """
        while not self._message_queue.empty():
            yield self._message_queue.get()

    def wait_until_empty(self):
        """Wait for all messages to be drained from the queue.

        Note that this is not thread-safe and not reliable.  For best
        results, only call this from the same thread that is adding
        messages to this MessageSource.  This should only be used in
        unit tests.
        """
        while not self._message_queue.empty():
            time.sleep(0.05)  # Wait for 50ms


class MessageConsumer(looper.Looper):
    """Base class for an object that consumes a stream of Message objects.

    The consumption of the messages is driven by a Looper.  The loop
    terminates when the stream ends.
    """

    def __init__(self, src):
        """Constructor.
        
        Args:
          src: A MessageSource object that will produce the stream of
            Messages for this object to consume.
        """
        looper.Looper.__init__(self)
        self._message_source = src

    def _process_message(self, msg):
        """Derived classes need to implement this."""
        raise NotImplementedError

    def _loop_once(self):
        msg = self._message_source.get_next_message()
        self._process_message(msg)
        if msg.error_type == END_OF_STREAM_ERROR:
            self.stop()


class MessageTee(MessageConsumer):
    """Forwards messages to set of output sources.

    Attributes:
      outputs: A tuple of MessageSource objects, each of which will emit
        the same messages as this consumer's input source.
    """

    def __init__(self, input_src, num_outputs):
        """Constructor.

        Args:
          input_src: This consumer's source.
          num_outputs: An integer, the number of MessageSource objects to
            create.
        """
        MessageConsumer.__init__(self, input_src)
        self.outputs = tuple(MessageSource() for _ in xrange(num_outputs))

    def _process_message(self, msg):
        for out in self.outputs:
            out._add_message(msg)

        
