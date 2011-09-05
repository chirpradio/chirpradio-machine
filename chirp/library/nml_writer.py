"""Output an NML file cataloging a set of audio files.

NML is an XML-based file format used by Traktor.  This code generates
NML version 11, which is used by Traktor Pro.
"""

import time
import xml.sax.saxutils

from chirp.common import timestamp
from chirp.common import unicode_util
from chirp.library import artists
from chirp.library import order


_UNKNOWN_ARTIST = "* Artist Not Known *"
_UNKNOWN_ALBUM = "* Album Not Known *"
_UNKNOWN_SONG = "* Title Not Known *"


# The following are templates used to produce NML files.

# Boilerplate that goes at the beginning of every NML file.  The one
# format parameter is an integer giving the total number of entries to
# be found in the file.
_NML_PREFIX = u"""<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<NML VERSION="14"><HEAD COMPANY="www.native-instruments.com" PROGRAM="Traktor - Native Instruments"></HEAD>
<MUSICFOLDERS></MUSICFOLDERS>
<COLLECTION ENTRIES="%10d">"""

# A template for producing individual song entries.
_NML_ENTRY = u"""<ENTRY MODIFIED_DATE=%(modified_date)s MODIFIED_TIME=%(modified_time)s TITLE=%(song)s ARTIST=%(artist)s><LOCATION DIR=%(dir)s FILE=%(file)s VOLUME=%(volume)s VOLUME_ID=""></LOCATION>
<ALBUM OF_TRACKS=%(total_num)s TITLE=%(album)s TRACK=%(order_num)s></ALBUM>
<INFO BITRATE=%(bitrate)s GENRE=%(genre)s PLAYTIME=%(duration_s)s IMPORT_DATE=%(import_date)s FILESIZE=%(size_in_kb)s></INFO>
</ENTRY>
"""

# Boilerplate that goes at the end of every NML file.
_NML_SUFFIX = u"""</COLLECTION>
<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="1">
<NODE TYPE="PLAYLIST" NAME="_RECORDINGS"><PLAYLIST ENTRIES="0" TYPE="LIST"></PLAYLIST>
</NODE>
</SUBNODES>
</NODE>
</PLAYLISTS>
</NML>
"""

def _traktor_path_quote(path):
    return path.replace("/", "/:")


class NMLWriter(object):
    """Generates an NML file for a collection of AudioFile objects."""

    def __init__(self, file_volume, root_dir, out_fh):
        """Constructor.

        Args:
          file_volume: The SMB-style file volume containing the files.
            This volume will need to be visible to the PC running Traktor
            that the NML file will ultimately be used from.
          root_dir: The root directory of the library, as seen by the
            machine that is running Traktor.
          out_fh: The file handle to write to.
        """
        self.num_entries = 0
        self._file_volume = file_volume
        self._file_volume_quoted = _traktor_path_quote(file_volume)
        self._root_dir = root_dir
        self._out_fh = out_fh
        # Make sure we are at the beginning of the file.
        self._out_fh.seek(0)
        # Write out a prefix for 0 entries.
        self._out_fh.write(_NML_PREFIX % 0)
        self._all_entries = []

    def write(self, au_file):
        """Adds a an audio file to the collection.

        Args:
          au_file: An AudioFile object to add to the collection.
        """
        entry_data = {}

        entry_data["order_num"], entry_data["total_num"] = order.decode(
            str(au_file.mutagen_id3.get("TRCK")))
        if entry_data["total_num"] is None:
            entry_data["total_num"] = 100

        entry_data["artist"] = unicode_util.simplify(
            au_file.mutagen_id3.get("TPE1", _UNKNOWN_ARTIST))
        entry_data["album"] = unicode_util.simplify(
            au_file.mutagen_id3.get("TALB", _UNKNOWN_ALBUM))
        entry_data["song"] = unicode_util.simplify(
            au_file.mutagen_id3.get("TIT2", _UNKNOWN_SONG))
        
        # TODO(trow): Set this somehow.
        entry_data["genre"] = "Unknown"

        entry_data["dir"] = _traktor_path_quote(
            au_file.canonical_directory(prefix=self._root_dir))
        entry_data["file"] = au_file.canonical_filename()
        entry_data["volume"] = self._file_volume_quoted

        entry_data["bitrate"] = int(
            au_file.mp3_header.bit_rate_kbps * 1000)
        entry_data["size_in_kb"] = int(au_file.frame_size / 1024)
        entry_data["duration_s"] = int(au_file.duration_ms / 1000)
            
        entry_data["import_date"] = time.strftime(
            "%Y/%m/%d", time.gmtime(au_file.import_timestamp))
        entry_data["modified_date"] = entry_data["import_date"]
        entry_data["modified_time"] = "35364"

        order_num = int(entry_data["order_num"])

        # Clean up any XML-unsafe characters and wrap each value in
        # quotes.
        for k, v in entry_data.items():
            new_v = xml.sax.saxutils.quoteattr(unicode(v))
            if new_v != v:
                entry_data[k] = new_v

        # TODO(trow): For now, we build a list of all entries so that
        # we can fix the ordering --- that is because Traktor
        # idiotically chooses to order tracks based on the order they
        # appear in the NML file, not based on the track numbering.
        entry_key = (au_file.album_id, order_num)
        self._all_entries.append((entry_key, entry_data))

        # TODO(trow): This is how we should do it!
        #self._out_fh.write(_NML_ENTRY % entry_data)

        self.num_entries += 1

    def close(self):
        # TODO(trow): We shouldn't need to build up a big in-memory
        # data structure here!
        self._all_entries.sort()
        for _, entry_data in self._all_entries:
            self._out_fh.write(_NML_ENTRY % entry_data)

        # Write out the suffix.
        self._out_fh.write(_NML_SUFFIX)
        # Write out the prefix with the correct number of entries.
        self._out_fh.seek(0)
        self._out_fh.write(_NML_PREFIX % self.num_entries)
        # Note: does not close the underlying file object!
