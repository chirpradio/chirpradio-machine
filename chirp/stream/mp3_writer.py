"""
Writes a tagged MP3 file to disk.
"""

import errno
import hashlib
import os
import time
import mutagen.id3
import mutagen.mp3
from chirp.common import timestamp
from chirp.library import constants
from chirp.library import ufid
from chirp.stream import message


# The library volume for archived content.
# TODO(trow): This should probably live somewhere else.
_ARCHIVE_VOLUME = 0xff


class MP3Writer(object):

    def __init__(self, prefix, start_ms=None):
        self._prefix = prefix
        self._start_ms = start_ms or timestamp.now_ms()
        self._end_ms = None
        self.duration_ms = 0
        self.frame_count = 0
        self.frame_size = 0
        self._sha1_calc = hashlib.sha1()

        self.path = "%s-%s.mp3" % (
            self._prefix, timestamp.get_human_readable_ms(self._start_ms))
        # The requested file should't already exist.  If so, delete it.
        try:
            os.unlink(self.path)
        except OSError, ex:
            if ex.errno != errno.ENOENT:
                raise ex
        mutagen_id3 = self._get_id3()
        mutagen_id3.save(filename=self.path)
        # Now re-open the MP3 stub so that we can append frames to it.
        self._fh = open(self.path, "ab", 0)  # 0 = unbuffered

    def _get_id3(self):
        mutagen_id3 = mutagen.id3.ID3()
        mutagen_id3.add(mutagen.id3.TFLT(text=[u"MPG/3"]))
        mutagen_id3.add(mutagen.id3.TOWN(text=[constants.TOWN_FILE_OWNER]))
        mutagen_id3.add(mutagen.id3.TRSN(text=[u"CHIRP Radio"]))
        mutagen_id3.add(mutagen.id3.TPE1(text=[u"CHIRP Archives"]))
        mutagen_id3.add(mutagen.id3.TIT1(text=[self._get_title()]))
        talb_str =  time.strftime("%Y-%m-%d: %a %b %d, %Y",
                                  time.localtime(int(self._start_ms / 1000)))
        mutagen_id3.add(mutagen.id3.TALB(text=[talb_str]))

        # Set the default encoding on all tags.
        for tag in mutagen_id3.itervalues():
            tag.encoding = constants.DEFAULT_ID3_TEXT_ENCODING
        return mutagen_id3

    def _get_title(self):
        start = timestamp.get_human_readable_ms(self._start_ms)
        if self._end_ms is None:
            end = "?" * len(start)
        else:
            end = timestamp.get_human_readable_ms(int(self._end_ms))
        return u"%s to %s" % (start, end)

    def write(self, msg):
        # Skip anything other than an MPEG frame.
        if msg.message_type != message.FRAME:
            return
        # TODO(trow): Pad the file to account for dropouts.
        # self._fh is unbuffered, so this should land on disk immediately.
        self._fh.write(msg.payload)
        self._sha1_calc.update(msg.payload)
        self.duration_ms += msg.mp3_header.duration_ms
        self.frame_count += 1
        self.frame_size += len(msg.payload)
        self._end_ms = msg.end_timestamp_ms

    def close(self):
        if self._fh is None:
            return
        self._fh.close()
        self._fh = None
        # Now re-open the MP3 file with mutagen and fix up the tags.
        mp3 = mutagen.mp3.MP3(self.path)
        # Put in the correct length.
        mp3.tags.add(
            mutagen.id3.TLEN(text=u"%d" % self.duration_ms,
                             encoding=constants.DEFAULT_ID3_TEXT_ENCODING))
        # Store a version of the title w/ both start and end times.
        mp3["TIT1"].text = [self._get_title()]
        # Add the frame count header.
        frame_count_tag = mutagen.id3.TXXX(
            desc=constants.TXXX_FRAME_COUNT_DESCRIPTION,
            text=[unicode(self.frame_count)],
            encoding=constants.DEFAULT_ID3_TEXT_ENCODING)
        mp3.tags.add(frame_count_tag)
        # Add the frame size header.
        frame_size_tag = mutagen.id3.TXXX(
            desc=constants.TXXX_FRAME_SIZE_DESCRIPTION,
            text=[unicode(self.frame_size)],
            encoding=constants.DEFAULT_ID3_TEXT_ENCODING)
        mp3.tags.add(frame_size_tag)
        # Add a UFID tag.  We use the start_ms timestamp as an import
        # time.
        mp3.tags.add(ufid.ufid_tag(_ARCHIVE_VOLUME,
                                   int(self._start_ms/1000),
                                   self._sha1_calc.hexdigest()))
        mp3.save()
        
