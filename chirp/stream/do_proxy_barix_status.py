
import BaseHTTPServer
import logging
import os
import sys
import threading
import time

from chirp.common.conf import (BARIX_STATUS_HOST, BARIX_STATUS_PORT,
                                   BARIX_HOST, BARIX_PORT)
from chirp.stream import barix


_TIMEOUT_S = 2
_POLLING_FREQUENCY_S = 5

_STATUS_PAGE = """<html><head>
<title>Barix Status</title>
<meta http-equiv=refresh content="10; url=.">
</head><body>
<h1>Barix Status</h1>
<small><i>This page will automatically update every 10 seconds.</i></small><br>
<small><i>Levels are averaged over the last %(level_avg_window_minutes)d
minutes.</i></small><br>
<br><br>
As of %(status_time)s:
<table>
<tr><td>Status</td><td>%(status)s</td></tr>
<tr><td>Left Level</td><td>%(left_level)s (avg %(left_level_avg)s)</td></tr>
<tr><td>Right Level</td><td>%(right_level)s (avg %(right_level_avg)s)</td></tr>
<tr><td>Live365?</td><td>%(live365_connected)s</td></tr>
<tr><td>Archiver?</td><td>%(archiver_connected)s</td></tr>
</table>
</body></html>
"""

# If we poll every 5s, 360 samples = 30 minutes
LEVEL_HISTORY_MAX_SIZE = 360
level_history = []


class _RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_GET(self):
        b_obj = self.barix
        NOT_CONNECTED = "<b>NOT CONNECTED</b>"

        left_level_avg = 0
        right_level_avg = 0
        level_avg_window_minutes = 0

        if level_history:
            N = len(level_history)
            left_level_avg = sum(L for L, _ in level_history) / N
            right_level_avg = sum(R for _, R in level_history) / N
            level_avg_window_minutes = N * _POLLING_FREQUENCY_S / 60

        barix_info = {
            "status_time": b_obj.last_update_time_str,
            "status": b_obj.status,
            "left_level": b_obj.left_level,
            "right_level": b_obj.right_level,
            "left_level_avg": int(left_level_avg),
            "right_level_avg": int(right_level_avg),
            "level_avg_window_minutes": int(level_avg_window_minutes),
            "live365_connected": NOT_CONNECTED,
            "archiver_connected": NOT_CONNECTED,
            }

        # TODO(trow): Check IP address.
        if "12345" in b_obj.clients:
            barix_info["live365_connected"] = "connected"
        # TODO(trow): Check IP address.
        if "12346" in b_obj.clients:
            barix_info["archiver_connected"] = "connected"

        response_str = _STATUS_PAGE % barix_info
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(response_str)))
        self.end_headers()
        self.wfile.write(response_str)
        
    def log_message(self, format, *args):
        pass  # Throw away log messages for now.


def handle_requests(srv, done):
    while not done.isSet():
        try:
            srv.handle_request()
        except Exception, err:
            logging.exception("Swallowed exception")


def poll_barix(b_obj, log_fh):
    try:
        if not b_obj.ping():
            return

        level_history.append(
            (float(b_obj.left_level), float(b_obj.right_level)))
        if len(level_history) > LEVEL_HISTORY_MAX_SIZE:
            level_history.pop(0)

        if log_fh:
            now = int(b_obj.last_update_time)
            ip, far_port = b_obj.clients.get("12345", ("None", 0))
            log_info = "%d %04x %s\n" % (now, int(far_port), ip)
            log_fh.write(log_info)
            log_fh.flush()

    except Exception, err:
        logging.exception("Swallowed exception")


def main():

    log_path = os.path.join(os.environ["HOME"], "live365_connection.log")
    log_fh = open(log_path, "a")

    _RequestHandler.barix = barix.Barix(BARIX_HOST, BARIX_PORT)

    srv = BaseHTTPServer.HTTPServer((BARIX_STATUS_HOST, BARIX_STATUS_PORT),
                                    _RequestHandler)
    srv.socket.settimeout(_TIMEOUT_S)
    done = threading.Event()
    th = threading.Thread(target=handle_requests, args=(srv, done))
    th.start()

    while True:
        try:
            poll_barix(_RequestHandler.barix, log_fh)
            time.sleep(_POLLING_FREQUENCY_S)
        except KeyboardInterrupt:
            break
        except Exception:
            logging.exception("Swallowed exception")

    if log_fh:
        log_fh.close()
    done.set()
    th.join()  # Wait for the serving thread to settle.


if __name__ == "__main__":
    main()
