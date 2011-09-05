"""
Simple HTTP Proxying for streams.

This code is strictly experimental, and should not be used in production.
"""

import Queue
import socket
import SocketServer
import threading

from chirp.stream import looper
from chirp.stream import message


class _OurTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    """The TCP server to use when listening for new connections."""
    allow_reuse_address = True


# We always respond with these headers.
_RESPONSE_HEADERS = "\r\n".join([
        "ICY 200 OK",
        "content-type:audio/mpeg",
        "icy-name:CHIRP stream_monitor proxy",
        "icy-genre:N/A",
        "icy-pub:1",
        "icy-br:0",
        "", ""])


def _send_all(sock, data):
    """Transmit all of 'data' via the socket 'sock'."""
    i = sock.send(data)
    while i < len(data):
        i += sock.send(data[i:])


class _ConnectionHandler(SocketServer.BaseRequestHandler):
    """A handler for incoming requests."""

    def setup(self):
        self._data_queue = Queue.Queue()

    def send(self, data):
        """Queue up raw data to be sent to the connected client."""
        self._data_queue.put(data)

    def handle(self):
        self.server.proxy.connections += 1
        # Read the HTTP headers sent by the newly-connected client.
        while True:
            request_str = self.request.recv(1024)
            if not request_str:
                return
            print request_str
            if "\r\n\r\n" in request_str:
                break
        # Queue up the response headers that we will send back.
        self.send(_RESPONSE_HEADERS)
        # Register to receieve messages from the HttpProxy object.
        self.server.proxy.register(self)
        # Now pull data from the queue and send it back to the
        # newly-connected client.
        while True:
            data = self._data_queue.get()
            # 'None' is a sentinal value that tells us the server is
            # shutting down.
            if data is None:
                break
            try:
                _send_all(self.request, data)
            except socket.error, err:
                # Drop the connection on an error.
                self.server.proxy.dropped_connections += 1
                return


class _ServerLooper(looper.Looper):
    """A looper for handling incoming requests to a server."""

    _TIMEOUT_S = 0.5

    def __init__(self, host, port):
        looper.Looper.__init__(self)
        self.server = _OurTCPServer((host, port), _ConnectionHandler)
        self.server.socket.settimeout(self._TIMEOUT_S)

    def _loop_once(self):
        self.server.handle_request()


class HttpProxy(message.MessageConsumer):
    """An HTTP proxy that forwards messages."""

    def __init__(self, src, host, port):
        message.MessageConsumer.__init__(self, src)
        self._server = _ServerLooper(host, port)
        self._server.server.proxy = self
        self._server.loop_in_thread()
        self._all_connections = {}
        self.connections = 0
        self.dropped_connections = 0

    def register(self, obj):
        """Begin pushing incoming messages to 'obj'."""
        self._all_connections[repr(obj)] = obj

    def unregister(self, obj):
        """Stop pushing incoming messages to 'obj'."""
        del self._all_connections[repr(obj)]

    def _process_message(self, msg):
        if msg.payload is not None:
            for connection in self._all_connections.itervalues():
                connection.send(msg.payload)

    def _done_looping(self):
        # Send 'None' to all connections to make them shut down.
        for connection in self._all_connections.itervalues():
            connection.send(None)
        self._server.stop()
        self._server.wait()
        print "Connections = %d" % self.connections
        print "Dropped connections = %d" % self.dropped_connections
        

    
