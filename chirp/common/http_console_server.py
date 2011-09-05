"""Implements a simple HTTP-based console for applications."""

import BaseHTTPServer
import logging
import gc
import os
import socket  # For gethostname
import sys
import threading
import time
import urllib
from chirp.common import timestamp


DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9000


class _RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    # Global dictionary of page handers, mapping paths to callables.
    page_handlers = {}
    # Global set of handlers that must be accessed via a POST.
    require_post = set()

    server_version = "Console"
    sys_version = (
        "chirpy %s" % BaseHTTPServer.BaseHTTPRequestHandler.sys_version)

    def _dispatch(self):
        # Try to response using a request handler.
        handler_fn = _RequestHandler.page_handlers.get(self.path)
        if handler_fn:
            retval = handler_fn(self)
            if retval is not None:
                self.send_html(retval)
            return
        # No matching page was found, so we return a 404.
        self.send_error(404)

    def do_GET(self):
        if self.path in _RequestHandler.require_post:
            self.send_error(405)  # Method not allowed
            return
        # In all other cases a GET and POST are treated exactly the same.
        self.do_POST()

    def do_POST(self):
        # Response to /ok with the string "ok".
        if self.path == "/ok":
            self.send_text("ok")
            return
        elif self.path == "/sysinfo":
            self.send_html(build_sysinfo_page())
            return
        self._dispatch()

    def _send_full_response(self, content_type, body):
        try:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except socket.error, (err_code, err_msg):
            sys.stderr.write("Socket error: (%d) %s\n" % (err_code, err_msg))

    def send_text(self, body):
        self._send_full_response("text/plain", body)

    def send_html(self, body):
        self._send_full_response("text/html", body)

    def log_message(self, format, *args):
        pass  # Throw away log messages for now.


def build_sysinfo_page():
    contents = ["<html><head><title>System Information</title></head><body>"]
    contents.append("<h1>System Information</h1>")
    contents.append("The current time is %s" % timestamp.get_pretty())

    def add(key, val):
        contents.append("<tr><td><i>%s</i></td><td>%s</td></tr>" % (key, val))

    contents.append("<h2>Process</h2>")
    contents.append("<table>")
    add("command line", " ".join(sys.argv))

    start_ms = timestamp.process_start_time_ms()
    age_ms = timestamp.process_age_ms()
    add("started at", timestamp.get_pretty_ms(start_ms))
    add("running for", timestamp.get_human_readable_duration(age_ms / 1000.0))

    add("process pid", os.getpid())
    gc_counts = gc.get_count()
    add("live objects", "%d (%s)" % (sum(gc_counts),
                                     " / ".join(str(x) for x in gc_counts)))

    add("live threads", threading.activeCount())

    cpu_s, sys_cpu_s = os.times()[:2]
    cpu_percent = 100 * (1000 * cpu_s) / age_ms
    sys_cpu_percent = 100 * (1000 * sys_cpu_s) / age_ms
    add("cpu utilization", "%.2f%%" % cpu_percent)
    add("system cpu", "%.2f%%" % sys_cpu_percent)


    add("Python version", sys.version)

    contents.append("</table>")
    contents.append("<h2>Machine</h2>")
    contents.append("<table>")

    add("hostname", socket.gethostname())
    add("uname", " / ".join(os.uname()))
    add("load average", " / ".join(str(x) for x in os.getloadavg()))
    add("uptime", timestamp.get_human_readable_duration(os.times()[-1]))
        
    contents.append("</table>")
    contents.append("</body></html>")
    return "\n".join(contents)


class _HttpConsoleServer(object):

    _TIMEOUT_S = 2.0

    def __init__(self, host, port):
        """Run an HTTP server at the given host and port.

        The constructor blocks until the server is able to respond
        to requests.
        """
        self._server = BaseHTTPServer.HTTPServer((host, port),
                                                 _RequestHandler)
        self._server.socket.settimeout(self._TIMEOUT_S)
        self._is_stopped = threading.Event()
        self._server_thread = threading.Thread(target=self._thread_worker)
        self._server_thread.start()

        # Now we hit the server's /ok until we get the expected response.
        # This ensures that the object is ready to handle requests
        # immediately after we return.
        self.url = "http://%s:%d" % (host, port)
        for _ in xrange(20):  # Try at most 20 times, then give up.
            try:
                response = urllib.urlopen(self.url + "/ok").read()
            except IOError:
                # Wait a bit, then try again.
                time.sleep(0.1)
                continue
            if response == "ok":
                break
            logging.error("Unexpected /ok reponse: %s", response)
        else:
            raise IOError("Couldn't start server")
        logging.info("Console server running at %s", self.url)
        
    def _thread_worker(self):
        while not self._is_stopped.isSet():
            self._server.handle_request()
        # Close the server's socket so that no new connections are possible.
        self._server.socket.close()
        logging.info("Server request handler loop ended")

    def stop(self):
        logging.info("Waiting for console server to shut down")
        self._is_stopped.set()
        self._server_thread.join()


_one_true_server = None

def start(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """Start the global HTTP console server.
    
    Args:
      host: The hostname to use when listening for connections.
      port: The port to use when listening for connections.

    Note that this function is not thread-safe.
    """
    global _one_true_server
    if _one_true_server is None:
        _one_true_server = _HttpConsoleServer(host, port)


def stop():
    """Stop the global HTTP console server.

    This blocks until the shutdown is complete.  Note that this function
    is not thread-safe.
    """
    global _one_true_server
    if _one_true_server:
        _one_true_server.stop()
        _one_true_server = None


def url(path=None):
    """Get the URL of the global HTTP console server.

    Args:
      path: An optional path component to include in the URL.

    Returns:
      The URL, or None if the server is not running.
    """
    global _one_true_server
    if _one_true_server is None:
        return None
    url = _one_true_server.url
    if path is not None:
        url += path
    return url


def register(path, handler_fn, require_post=False):
    """Register a new page handler with the global HTTP console server.

    Args:
      path: The URL path component that this handler will generate
        responses for.
      handler_fn: A callable that takes a BaseHTTPRequestHandler and
        returns either string containing HTML that should be returned to the
        client, or None if the callable takes responsibility for generating
        the response.
    """
    if path in _RequestHandler.page_handlers:
        raise ValueError("Attempt to re-register path %s" % path)
    _RequestHandler.page_handlers[path] = handler_fn
    if require_post:
        _RequestHandler.require_post.add(path)
    

if __name__ == "__main__":
    start()
    try:
        while True: time.sleep(10000)
    except KeyboardInterrupt:
        pass
    stop()
