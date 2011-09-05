"""
A MessageConsumer that archives a stream to disk, rotating the file hourly.
"""

import errno
import os
import sys
import time

from chirp.common import timestamp
from chirp.stream import message
from chirp.stream import mp3_writer


class Archiver(message.MessageConsumer):

    ROOT_DIR = "/tmp/test-archives"
    FILE_PREFIX = "chirp"

    def __init__(self, src):
        message.MessageConsumer.__init__(self, src)
        self._writer = None
        self._last_hour = None
        self.rollover_count = 0

    def _dirname(self, ts_ms):
        time_tuple = time.localtime(int(ts_ms/1000))
        return os.path.join(self.ROOT_DIR,
                            time.strftime("%Y/%m/%d/", time_tuple))

    def _open(self, ts_ms):
        # Try to create the directory for the archive file.
        dirname = self._dirname(ts_ms)
        try:
            os.makedirs(dirname)
        except OSError, ex:
            if ex.errno != errno.EEXIST:
                raise ex
        prefix = os.path.join(dirname, self.FILE_PREFIX)
        return mp3_writer.MP3Writer(prefix, ts_ms)

    def _process_message(self, msg):
        # Skip any non-FRAME messages.
        if msg.message_type != message.FRAME:
            return
        # Compute the current hour in local time.
        now_s = int(msg.start_timestamp_ms/1000)
        curr_hour = time.localtime(now_s).tm_hour
        # If necessary, roll over to a new writer.
        if self._writer is not None and curr_hour != self._last_hour:
            self._writer.close()
            self._writer = None
            self.rollover_count += 1
        # If necessary, open a new writer.
        if self._writer is None:
            self._writer = self._open(msg.start_timestamp_ms)
            self._last_hour = curr_hour
        # Pass the message to our writer.
        self._writer.write(msg)

    def _done_looping(self):
        if self._writer is not None:
            self._writer.close()
            self._writer = None
