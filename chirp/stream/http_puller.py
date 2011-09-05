
# A 128kbps stream = 16,000 bytes per second
# 2000 bytes per block = 8 blocks per second

import re
import socket
import time

from chirp.common import timestamp
from chirp.stream import looper
from chirp.stream import message


# A template for the HTTP request that we send to the remote
# audio source.
_HTTP_REQUEST = """GET %(path)s HTTP/1.1
User-Agent: CHIRP stream_monitor
Host: %(host)s
Accept: */*
Connection: Keep-Alive

""".replace("\n", "\r\n")

def _parse_http_headers(header_str):
    lines = header_str.split("\n")
    if not lines:
        return None, None
    first_line = lines.pop(0).strip()
    # Handle HTTP or Shoutcast
    match = re.search(r"^((HTTP/1\.[01])|(ICY)) (\d+)", first_line)
    if match:
        status_code = int(match.group(4))
    elif re.search(r"^SOURCE .* HTTP/1\.0$", first_line):
        # A hack for headers returned by the Barix.
        status_code = 200
    else:
        return None, None
    http_headers = {}
    for x in lines:
        key, val = x.split(':', 1)
        http_headers[key.strip()] = val.strip()
    return status_code, http_headers


class HttpPuller(looper.Looper, message.MessageSource):
    """Generates a stream of messages from an HTTP data stream."""

    # TODO(trow): All of these values should be tuned against the
    # eventual production environment.

    # This was previously at 0.5 and we saw lots of timeouts; the
    # Barix seems to seize up occasionally.
    READ_TIMEOUT_S = 1
    READ_SIZE = 2048
    BACKOFF_S = 0.5  # i.e. 500ms

    def __init__(self, host, post, path):
        looper.Looper.__init__(self)
        message.MessageSource.__init__(self)

        self._host = host
        self._port = post
        self._path = path
        self._pending_redirect = None

        self._looping = False
        self._sock = None
        self._connection_id = None
        self._connection_offset = 0
        self._pending_payload = None
        
    def _now_ms(self):
        """Returns the current time in integral milliseconds since the epoch.
        """
        return timestamp.now_ms()

    def _create_socket(self):
        """Returns a TCP socket to pull data from."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.READ_TIMEOUT_S)
        return sock

    def _backoff(self):
        time.sleep(self.BACKOFF_S)

    def _start_message(self):
        """Returns a new message."""
        msg = message.Message()
        msg.start_timestamp_ms = self._now_ms()
        return msg

    def _finish_message(self, msg, error_type=None, error=None):
        """Do post-processing on a finished message."""
        msg.end_timestamp_ms = self._now_ms()
        if error_type:
            msg.set_error(error_type, error)
        return msg

    def _connect(self):
        """Open a connection to the HTTP data source.

        Returns:
          Either a CONNECTED-type Message or an ERROR Message if the
          connection attempt fails.
        """
        assert self._sock is None


        msg = self._start_message()

        msg.connect_host, msg.connect_port, msg.connect_path = (
            self._pending_redirect or (self._host, self._port, self._path))
        self._pending_redirect = None

        sock = self._create_socket()
        try:
            sock.connect((msg.connect_host, msg.connect_port))
        except socket.timeout:
            return self._finish_message(msg, message.CONNECT_TIMEOUT_ERROR)
        except socket.error, err:
            return self._finish_message(msg, message.CONNECT_ERROR, err)
        # TODO(trow): Other exceptions?

        try:
            request_str = _HTTP_REQUEST % {
                'path': msg.connect_path,
                'host': ("%s:%s" % (msg.connect_host, msg.connect_port)),
                }
            sock.sendall(request_str)
        except socket.error, err:
            return self._finish_message(msg, message.REQUEST_ERROR, err)
        # TODO(trow): Other exceptions?

        msg.message_type = message.CONNECTED
        msg.connection_id = self._connection_id = self._now_ms()
        msg.connection_offset = self._connection_offset = 0
        self._sock = sock
        return self._finish_message(msg)

    def _handle_redirect(self, location):
        """Return True if we successfully can handle the redirect.""" 
        match = re.search(r"^http://([^/:]+)(:(\d+))(/.*)$", location)
        if match is None:
            return False
        if match.group(2) is None:
            port = 80
        else:
            port = int(match.group(3))
        self._pending_redirect = (match.group(1), port, match.group(4))
        self._sock = None  # Force a reconnect.
        self._pending_payload = None
        return True

    def _pull_one_block(self):
        """Read a single block of data from the stream.

        Returns:
          Either a BLOCK-type Message or an ERROR Message if the read
          attempt fails.
        """
        assert self._sock is not None

        msg = self._start_message()
        msg.connection_id = self._connection_id
        msg.connection_offset = self._connection_offset
        
        if self._pending_payload is not None:
            payload = self._pending_payload
            self._pending_payload = None
        else:
            try:
                payload = self._sock.recv(self.READ_SIZE)
            except socket.timeout:
                return self._finish_message(msg, message.READ_TIMEOUT_ERROR)
            except socket.error, err:
                return self._finish_message(msg, message.READ_ERROR, err)
            # TODO(trow): Other exceptions?

        # If this is the first block we are reading, strip off the
        # http headers and return a RESPONSE message.
        if self._connection_offset == 0:
            i = payload.find("\r\n\r\n")
            if i == -1:
                msg.payload = payload
                return self._finish_message(msg, message.MISSING_HEADERS_ERROR)
            msg.http_status_code, msg.http_headers = (
                _parse_http_headers(payload[:i]))
            if msg.http_status_code is None or msg.http_headers is None:
                msg.payload = payload[:i]
                return self._finish_message(
                    msg, message.MALFORMED_HEADERS_ERROR)
            self._pending_payload = payload[i+4:]
            self._connection_offset = i

            # Handle a redirect.
            if msg.http_status_code == 302:
                location = msg.http_headers.get('Location')
                if location is None:
                    return self._finish_message(
                        msg, message.BAD_REDIRECT_ERROR)
                if not self._handle_redirect(location):
                    return self._finish_message(
                        msg, message.BAD_REDIRECT_ERROR)
            msg.message_type = message.RESPONSE
            return self._finish_message(msg)
                        
        self._connection_offset += len(payload)
        msg.message_type = message.BLOCK
        msg.payload = payload
        return self._finish_message(msg)

    def _loop_once(self):
        """Do a unit of work against our data stream."""
        if self._sock is None:
            msg = self._connect()
        else:
            msg = self._pull_one_block()
        self._add_message(msg)
        # If we see an error, close the socket and wait a bit.
        # TODO(trow): This is probably too aggressive, we might want to
        # retry a few times before breaking off the existing connection?
        # The optimal strategy will depend on the latency of establishing
        # a connection in our eventual production environment.
        if msg.is_error():
            if self._sock:
                # TODO(trow): Can close block or raise an exception?
                self._sock.close()
                self._sock = None
            self._backoff()
        return msg  # Returned for convenience in testing

    def _done_looping(self):
        # Close and clear the socket.
        if self._sock:
            self._sock.close()
            self._sock = None
        # Send an end-of-stream error message.
        msg = self._start_message()
        msg = self._finish_message(msg, message.END_OF_STREAM_ERROR)
        self._add_message(msg)
