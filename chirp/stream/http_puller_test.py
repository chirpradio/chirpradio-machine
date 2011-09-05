import threading
import time
import socket
import unittest

from chirp.stream import message
from chirp.stream import http_puller


MOCK_ERROR_CODE = 12345
MOCK_ERROR_TEXT= "Mock Error"

class MockSocket(object):

    simulate_connect_timeout = False
    simulate_connect_error = False
    simulate_sendall_error = False
    simulate_read_timeout = False

    connect_called = False
    host = None
    port = None
    sendall_data = []
    recv_data = []
    close_called = False

    def connect(self, host_port_pair):
        assert not self.connect_called
        self.connect_called = True
        self.host, self.port = host_port_pair
        if self.simulate_connect_timeout:
            raise socket.timeout
        if self.simulate_connect_error:
            raise socket.error(MOCK_ERROR_CODE, MOCK_ERROR_TEXT)

    def sendall(self, payload):
        self.sendall_data.append(payload)
        if self.simulate_sendall_error:
            raise socket.error(MOCK_ERROR_CODE, MOCK_ERROR_TEXT)

    def recv(self, read_size):
        if not self.recv_data:
            if self.simulate_read_timeout:
                raise socket.timeout
            # We raise a read error if we run out of data, like a
            # closing socket would.
            raise socket.error(MOCK_ERROR_CODE, MOCK_ERROR_TEXT)
        current = self.recv_data[0]
        to_return = current[:read_size]
        if to_return == current:
            self.recv_data.pop(0)
        else:
            self.recv_data[0] = current[read_size:]
        return to_return

    def close(self):
        self.close_called = True


class MockHttpPuller(http_puller.HttpPuller):

    mock_time_ms = 100
    backoff_count = 0

    def __init__(self, *args, **kwargs):
        self.next_socket = MockSocket()
        http_puller.HttpPuller.__init__(self, *args, **kwargs)

    def _now_ms(self):
        return int(self.mock_time_ms)

    def _backoff(self):
        self.backoff_count += 1

    def advance_mock_time(self, delta_ms):
        self.mock_time_ms += delta_ms

    def _create_socket(self):
        sock = self.next_socket
        self.next_socket = MockSocket()
        return sock


class HttpPullerTest(unittest.TestCase):

    def assertMessageError(self, error_type, msg):
        self.assertEqual(message.ERROR, msg.message_type)
        self.assertEqual(error_type, msg.error_type)
        if error_type in (message.CONNECT_TIMEOUT_ERROR,
                          message.READ_TIMEOUT_ERROR,
                          message.MISSING_HEADERS_ERROR,
                          message.END_OF_STREAM_ERROR):
            self.assertTrue(msg.error_code is None)
            self.assertTrue(msg.error_text is None)
        else:
            self.assertEqual(MOCK_ERROR_CODE, msg.error_code)
            self.assertEqual(MOCK_ERROR_TEXT, msg.error_text)

    def testConnect(self):
        # Simulate successfully connecting to the remote host.
        hp = MockHttpPuller("host", 1729, "/foo")
        sock = hp.next_socket
        hp._loop_once()
        # We should have saved the socket.
        self.assertTrue(hp._sock is sock)
        # Connect should be called with the correct host and port.
        self.assertTrue(sock.connect_called)
        self.assertEqual("host", sock.host)
        self.assertEqual(1729, sock.port)
        # Something that looks like an http request should have been
        # sent with sendall.
        self.assertEqual(1, len(sock.sendall_data))
        self.assertTrue("GET /foo" in sock.sendall_data[0])
        # This connection should have been assigned an ID based on
        # the current time, and the offset should be 0.
        self.assertEqual(hp.mock_time_ms, hp._connection_id)
        self.assertEqual(0, hp._connection_offset)
        # A CONNECTED message should be put onto the message queue.
        msg = hp.get_next_message()
        self.assertEqual(message.CONNECTED, msg.message_type)
        # The message should be stamped with the connection ID
        # and offset.
        self.assertEqual(hp._connection_id, msg.connection_id)
        self.assertEqual(hp._connection_offset, msg.connection_offset)

        # Simulate a connect timeout.
        hp = MockHttpPuller("host", 1729, "/foo")
        hp.next_socket.simulate_connect_timeout = True
        hp._loop_once()
        # The puller should not have a saved socket.
        self.assertTrue(hp._sock is None)
        # A CONNECT_TIMEOUT error message should be put onto the
        # message queue.
        msg = hp.get_next_message()
        self.assertMessageError(message.CONNECT_TIMEOUT_ERROR, msg)
        # We should have backed off after the error.
        self.assertEqual(1, hp.backoff_count)

        # Simulate a connect error.
        hp = MockHttpPuller("host", 1729, "/foo")
        hp.next_socket.simulate_connect_error = True
        hp._loop_once()
        # The puller should not have a saved socket.
        self.assertTrue(hp._sock is None)
        # A CONNECT_ERROR error message should be put onto the message
        # queue.
        msg = hp.get_next_message()
        self.assertMessageError(message.CONNECT_ERROR, msg)
        # We should have backed off after the error.
        self.assertEqual(1, hp.backoff_count)

        # Simulate a problem sending the request.
        hp = MockHttpPuller("host", 1729, "/foo")
        hp.next_socket.simulate_sendall_error = True
        hp._loop_once()
        # The puller should not have a saved socket.
        self.assertTrue(hp._sock is None)
        # A REQUEST_ERROR error message should be put onto the message
        # queue.
        msg = hp.get_next_message()
        self.assertMessageError(message.REQUEST_ERROR, msg)
        # We should have backed off after the error.
        self.assertEqual(1, hp.backoff_count)

    def get_connected_http_puller(self):
        # Simulate successfully connecting to the remote host.
        hp = MockHttpPuller("host", 1729, "/foo")
        hp._loop_once()
        msg = hp.get_next_message()
        self.assertEqual(message.CONNECTED, msg.message_type)
        return hp

    def testPull(self):
        # Simulate successfully fetching a block.
        hp = self.get_connected_http_puller()
        hp._sock.recv_data = [ "HTTP/1.1 200 OK\r\nFoo: Bar\r\n\r\nXXXXX",
                               "YYYYYY" ]
        msg = hp._loop_once()
        self.assertEqual(message.RESPONSE, msg.message_type)
        self.assertEqual(200, msg.http_status_code)
        self.assertEqual({"Foo": "Bar"}, msg.http_headers)
        msg = hp._loop_once()
        self.assertEqual(message.BLOCK, msg.message_type)
        self.assertEqual("XXXXX", msg.payload)
        # And again
        msg = hp._loop_once()
        self.assertEqual(message.BLOCK, msg.message_type)
        self.assertTrue(msg.http_headers is None)
        self.assertEqual("YYYYYY", msg.payload)

        # Simulate missing http headers
        hp = self.get_connected_http_puller()
        hp._sock.recv_data = [ "No Headers" ]
        msg = hp._loop_once()
        self.assertMessageError(message.MISSING_HEADERS_ERROR, msg)
        self.assertTrue(hp._sock is None)  # No saved socket
        self.assertEqual(1, hp.backoff_count)

        # Simulate a read error
        hp = self.get_connected_http_puller()
        hp._sock.simulate_read_timeout = True
        msg = hp._loop_once()
        self.assertMessageError(message.READ_TIMEOUT_ERROR, msg)
        self.assertTrue(hp._sock is None)  # No saved socket
        self.assertEqual(1, hp.backoff_count)

        # Simulate a read error
        hp = self.get_connected_http_puller()
        hp._sock.simulate_read_error = True
        hp._sock.recv_data = [ "HTTP/1.1 200 OK\r\n\r\nXXXXXX" ]
        _ = hp._loop_once()  # First message (RESPONSE) is OK
        _ = hp._loop_once()  # Second message (BLOCK) is OK
        msg = hp._loop_once()  # Here we blow up
        self.assertMessageError(message.READ_ERROR, msg)
        self.assertTrue(hp._sock is None)  # No saved socket
        self.assertEqual(1, hp.backoff_count)

    def testStartAndStopLooping(self):
        hp = MockHttpPuller("host", 1729, "/foo")
        # A few blocks so that we can simulate a period of success.
        hp.next_socket.recv_data = [ "XXX\r\n\r\nXXXXX" ] * 5
        hp.loop_in_thread()
        # Pull a few messages off the queue.  This shows us that the
        # work thread has spun up and is looping.
        for _ in xrange(10):
            unused_msg = hp.get_next_message()
        hp.stop()
        hp.wait()
        self.assertEqual([], hp.trapped_exceptions)
        self.assertTrue(hp._sock is None)  # No saved socket
        # The last message on the queue should be an end-of-stream.
        last_msg = None
        for msg in hp.get_all_messages():
            last_msg = msg
        self.assertMessageError(message.END_OF_STREAM_ERROR, last_msg)


if __name__ == "__main__":
    unittest.main()
