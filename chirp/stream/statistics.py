"""
Compute statistics about a consumed sequence of messages.
"""

from chirp.common import http_console_server
from chirp.common import timestamp
from chirp.stream import message


class _ConnectionInfo(object):
    
    MAX_NUM_ERRORS = 25

    connection_id = None
    start_timestamp_ms = None
    last_timestamp_ms = None
    num_frames = 0
    size_frames = 0
    duration_frames_ms = 0
    freq_frame_kbps = None  # Initialized as {} in constructor
    first_frame_timestamp_ms = None
    last_frame_timestamp_ms = None
    num_blocks = 0
    size_blocks = 0
    last_block_timestamp_ms = None
    errors = None  # Initialized as [] in constructor

    def __init__(self):
        self.freq_frame_kbps = {}
        self.errors = []

    def process(self, msg):
        self.last_timestamp_ms = msg.end_timestamp_ms
        if msg.message_type == message.CONNECTED:
            self.connection_id = msg.connection_id
            self.start_timestamp_ms = msg.start_timestamp_ms
        elif msg.message_type == message.FRAME:
            self.num_frames += 1
            self.size_frames += len(msg.payload)
            self.duration_frames_ms += msg.mp3_header.duration_ms
            key = msg.mp3_header.bit_rate_kbps
            self.freq_frame_kbps[key] = self.freq_frame_kbps.get(key, 0) + 1
            if self.first_frame_timestamp_ms is None:
                self.first_frame_timestamp_ms = msg.start_timestamp_ms
            self.last_frame_timestamp_ms = msg.end_timestamp_ms
        elif msg.message_type == message.BLOCK:
            self.num_blocks += 1
            self.size_blocks += len(msg.payload)
            self.last_block_timestamp_ms = msg.end_timestamp_ms
        elif msg.message_type == message.ERROR:
            self.errors.append(msg)
            self.last_error_timestamp_ms = msg.start_timestamp_ms
            if len(self.errors) > self.MAX_NUM_ERRORS:
                self.errors.pop(0)

    def html(self):
        now_ms = timestamp.now_ms()
        # Note my use of nested tables.  I suck at HTML.
        contents = ["<table border=1 cellpadding=4><tr><td><table>"]
        def add(key, val):
            contents.append(
                "<tr><td><i>%s</i></td><td>%s</td></tr>" % (key, val))
        def add_since_ms(key, ts_ms):
            add(key, "%s (%s ago)" % (
                    timestamp.get_pretty_ms(ts_ms),
                    timestamp.get_human_readable_duration_ms(now_ms-ts_ms)))

        add("start time", timestamp.get_pretty_ms(self.start_timestamp_ms))

        duration_ms = self.last_timestamp_ms - self.start_timestamp_ms
        add("duration", timestamp.get_human_readable_duration_ms(duration_ms))

        if self.num_frames:
            add("frames", "%d / %.2fM" % (self.num_frames,
                                          float(self.size_frames) / (1 << 20)))

            subtable = ["<table cellpadding=2>"]
            vbr = 0
            for key, num in sorted(self.freq_frame_kbps.items()):
                perc = 100.0 * num / self.num_frames
                vbr += float(key * num) / self.num_frames
                subtable.append(
                    "<tr><td>%d kbps</td><td>%.1f%%</td><td>%d</td></tr>" %
                    (key, perc, num))
            subtable.append("</table>")
            add("frame distribution", "".join(subtable))
            add("average bit rate", "%.2f kbps" % vbr)

            since_last_ms = now_ms - self.last_frame_timestamp_ms
            add_since_ms("last frame", self.last_frame_timestamp_ms)

            frame_span_ms = (self.last_frame_timestamp_ms -
                             self.first_frame_timestamp_ms)
            add("frame deficit",
                "%.1fms" % (frame_span_ms - self.duration_frames_ms))

        if self.num_blocks:
            add("junk blocks", "%d / %db" % (
                    self.num_blocks, self.size_blocks))
            add_since_ms("last junk", self.last_block_timestamp_ms)

        if self.errors:
            error_list = [
                "%s - %s / %s / %s" % (
                    timestamp.get_pretty_ms(err.start_timestamp_ms),
                    err.error_type, err.error_code, err.error_text)
                for err in reversed(self.errors)]
            add("errors", "<br>".join(error_list))


        contents.append("</table></td></tr></table>")
        return "\n".join(contents)


class Statistics(message.MessageConsumer):

    MAX_NUM_RECENT_CONNECTIONS = 20

    def __init__(self, src):
        message.MessageConsumer.__init__(self, src)
        self._current_connection_info = None
        self._recent_connections = []
        
    def _process_message(self, msg):
        if msg.message_type == message.CONNECTED:
            if self._current_connection_info:
                self._recent_connections.append(self._current_connection_info)
                if (len(self._recent_connections)
                    > self.MAX_NUM_RECENT_CONNECTIONS):
                    self._recent_connections.pop(0)
            self._current_connection_info = _ConnectionInfo()
        if self._current_connection_info is not None:
            self._current_connection_info.process(msg)

    def _connections_html(self, unused_request):
        contents = ["<html><head><title>Connection Log</title></head><body>"]
        contents.append("<h1>Connection Log</h1>")

        contents.append("The current time is %s" % timestamp.get_pretty())

        contents.append("<h2>Current</h2>")
        if self._current_connection_info:
            contents.append(self._current_connection_info.html())
        else:
            contents.append("<i>No connections yet</i>")

        if self._recent_connections:
            contents.append("<h2>Recent</h2>")
            contents.extend(con.html()
                            for con in reversed(self._recent_connections))

        contents.append("</body></html>")
        return "\n".join(contents)

    def export(self, path=None):
        http_console_server.register("/connections", self._connections_html)
               
