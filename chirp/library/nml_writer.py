"""Output an NML file cataloging a set of audio files.

NML is an XML-based file format used by Traktor.  This code generates
NML version 11, which is used by Traktor Pro.
"""

import time
import xml.sax.saxutils
# from what I've found, lxml might be faster depending on usage; might be worth trying
import xml.etree.ElementTree as ET

from chirp.common import timestamp
from chirp.common import unicode_util
from chirp.library import artists
from chirp.library import order, database
from chirp.common.conf import LIBRARY_DB

_UNKNOWN_ARTIST = "* Artist Not Known *"
_UNKNOWN_ALBUM = "* Album Not Known *"
_UNKNOWN_SONG = "* Title Not Known *"


# The following are templates used to produce NML files.

# Boilerplate that goes at the beginning of every NML file.  The one
# format parameter is an integer giving the total number of entries to
# be found in the file.
_NML_PREFIX = """<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<NML VERSION="14"><HEAD COMPANY="www.native-instruments.com" PROGRAM="Traktor - Native Instruments"></HEAD>
<MUSICFOLDERS></MUSICFOLDERS>
<COLLECTION ENTRIES="%10d">"""

# A template for producing individual song entries.
_NML_ENTRY = """<ENTRY MODIFIED_DATE=%(modified_date)s MODIFIED_TIME=%(modified_time)s TITLE=%(song)s ARTIST=%(artist)s><LOCATION DIR=%(dir)s FILE=%(file)s VOLUME=%(volume)s VOLUME_ID=""></LOCATION>
<ALBUM OF_TRACKS=%(total_num)s TITLE=%(album)s TRACK=%(order_num)s></ALBUM>
<INFO BITRATE=%(bitrate)s GENRE=%(genre)s PLAYTIME=%(duration_s)s IMPORT_DATE=%(import_date)s FILESIZE=%(size_in_kb)s></INFO>
</ENTRY>
"""

# Boilerplate that goes at the end of every NML file.
_NML_SUFFIX = """</COLLECTION>
<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="1">
<NODE TYPE="PLAYLIST" NAME="_RECORDINGS"><PLAYLIST ENTRIES="0" TYPE="LIST"></PLAYLIST>
</NODE>
</SUBNODES>
</NODE>
</PLAYLISTS>
</NML>
"""

# Custom playlist hidden on Traktor Pro to track when we last edited this file
_NML_TIMESTAMP = """<NODE TYPE="PLAYLIST" NAME="_CHIRP"><PLAYLIST ENTRIES="0" TYPE="LIST" UUID="%10d" />
</NODE>"""

def _traktor_path_quote(path):
    return path.replace("/", "/:")


class NMLReadWriter(object):
    """Generates an NML file for a collection of AudioFile objects with optimizations to reduce writing."""

    def __init__(self, file_volume, root_dir, overwrite_fh, db):
        """Constructor.

        Args:
          file_volume: The SMB-style file volume containing the files.
            This volume will need to be visible to the PC running Traktor
            that the NML file will ultimately be used from.
          root_dir: The root directory of the library, as seen by the
            machine that is running Traktor.
          overwrite_fh: The file handle to write to. It can optionally
            be a previous NML file to minimize writes.
          db: An instance of the database object we will compare modified
            timestamps with
        """
        self._num_new_entries = 0
        self._file_volume = file_volume
        self._file_volume_quoted = _traktor_path_quote(file_volume)
        self._root_dir = root_dir
        self._overwrite_fh = overwrite_fh
        self._et_tree = ET.parse(overwrite_fh)
        self._db = db
        # Make sure we are at the beginning of the file.
        # self._overwrite_fh.seek(0)
        # Write out a prefix for 0 entries.
        # self._overwrite_fh.write(_NML_PREFIX % 0)
    
    def _update_timestamp(self):
        for playlist in self._et_tree.iter("PLAYLIST"):
            old_timestamp = playlist.get("UUID")
            if old_timestamp is not None:
                # TODO: update timestamp to current timestamp
                new_timestamp = timestamp.now()
                playlist.set("UUID", str(new_timestamp))
                return (old_timestamp, new_timestamp)

        # If timestamp is not found, consider every file to be new
        return (0, timestamp.now())

    def _au_file_to_nml_entry(self, au_file):
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

        # Clean up any XML-unsafe characters and wrap each value in
        # quotes.
        for k, v in list(entry_data.items()):
            new_v = xml.sax.saxutils.quoteattr(str(v))
            if new_v != v:
                entry_data[k] = new_v
        
        # TODO: make this an XML element from the start instead of using fromstring
        return ET.fromstring(_NML_ENTRY % entry_data)

    # def modify audio file
    def _modify_nml_entry(self, entry_elem, au_file):
        """Modifies a pre-existing entry in the NML file

        Args: 
          entry: An element tree element corresponding to the entry we want to modify
          au_file: The audio file with the new values we want to write in entry
        """
        # Make this in an object first so we can run the XLM quoteattr cleanup loop on it
        modified_attrs = {}

        modified_attrs["order_num"], modified_attrs["total_num"] = order.decode(
            str(au_file.mutagen_id3.get("TRCK")))
        if modified_attrs["total_num"] is None:
            modified_attrs["total_num"] = 100
        
        modified_attrs["artist"] = unicode_util.simplify(
            au_file.mutagen_id3.get("TPE1", _UNKNOWN_ARTIST))
        modified_attrs["album"] = unicode_util.simplify(
            au_file.mutagen_id3.get("TALB", _UNKNOWN_ALBUM))
        modified_attrs["song"] = unicode_util.simplify(
            au_file.mutagen_id3.get("TIT2", _UNKNOWN_SONG))
        
        modified_attrs["size_in_kb"] = int(au_file.frame_size / 1024)

        # Assuming genre field doesn't get modified

        # Not allowing dir or volume to change because all files should have the same values for these anyway

        # Not allowing file name to change because this is the fingerprint that we
        # treat as a unique key for the audio file. Changing it would cause problems

        # Not allowing bitrate or duration to be modified
        # because this would change the fingerprint which would cause problems

        modified_attrs["import_date"] = time.strftime(
            "%Y/%m/%d", time.gmtime(au_file.import_timestamp))
        modified_attrs["modified_date"] = modified_attrs["import_date"]
        
        # Modified time is a hardset value so I'm not modifying it

        # Clean up any XML-unsafe characters and wrap each value in
        # quotes.
        # for k, v in list(modified_attrs.items()):
        #     new_v = xml.sax.saxutils.quoteattr(str(v))
        #     if new_v != v:
        #         modified_attrs[k] = new_v

        entry_elem.set("ARTIST", modified_attrs["artist"])
        entry_elem.set("TITLE", modified_attrs["song"])
        entry_elem.set("MODIFIED_DATE", modified_attrs["modified_date"])

        album_elem = entry_elem.find("ALBUM")
        album_elem.set("OF_TRACKS", str(modified_attrs["total_num"]))
        album_elem.set("TRACK", str(modified_attrs["order_num"]))
        album_elem.set("TITLE", modified_attrs["album"])

        info_elem = entry_elem.find("INFO")
        info_elem.set("FILESIZE", str(modified_attrs["size_in_kb"]))
        info_elem.set("IMPORT_DATE", modified_attrs["modified_date"])

    # def test_write(self):
    #     for playlist in self._et_tree.iter("PLAYLIST"):
    #         uuid = playlist.get("UUID")
    #         if uuid:
    #             if uuid == "12345":
    #                 playlist.set("UUID", "123")
    #                 self._overwrite_fh.seek(0)
    #                 self._et_tree.write(self._overwrite_fh, "unicode")
    #                 self._overwrite_fh.truncate()
    #                 print("set the thing")
    #             else:
    #                 print("uuid number wrong")
    #         else:
    #             print("no uuid found")

    # TODO: add a function to add an individual file as opposed to auto detecting from db

    def add_new_files(self):
        (last_modified, new_timestamp) = self._update_timestamp()
        # query all audio files that have been modified since this timestamp
        # TODO: create a function, probably in database.py, that returns an iterator
            # over all fingerprints in the new table that have a modified timestamp greater
            # than the given value
        new_audio_files = self._db.get_au_files_after(last_modified) # TODO: change function name to whatever it ends up actually being

        # The plan is to loop through all audio files in the NML file and for each,
        # check if its fingerprint exists in the new_audio_files list. If it does, then modify its entry with the new data.
        # This should be faster if we store the fingerprints in a set or dict.
        # For now, I'm going with a set, but if we need to access the audio file object, a hash would be better.
        # I'm concerned that this might be a memory issue since there are a lot of audio files,
        # but I think the original writer has all files in the whole db in memory at a time so it's probably fine
        new_au_files_dict = {}
        for au_file in new_audio_files:
            new_au_files_dict[au_file.fingerprint] = au_file
        
        collection = self._et_tree.find("COLLECTION") # this might fail and might require use of iter instead of find; haven't tested
        if collection is None:
            print("Could not find collection")
            return

        for entry in collection.iter("ENTRY"):
            location = entry.find("LOCATION")
            file_name = location.get("FILE")
            if file_name is None:
                continue
            fingerprint = file_name.split(".")[0]
            au_file = new_au_files_dict.get(fingerprint)
            if au_file is not None:
                self._modify_nml_entry(entry, au_file)
                del new_au_files_dict[fingerprint]
        
        # Sort new audio files so album order is maintained
        order_nums = {}
        def get_order_key(au_file):
            order_num = order_nums.get(au_file.fingerprint)
            if order_num is None:
                order_num, _ = order.decode(str(au_file.mutagen_id3.get("TRCK")))
                order_nums[au_file.fingerprint] = order_num
            return (au_file.album_id, order_num)
        sorted_new_au_files = sorted(new_au_files_dict.values(), key=get_order_key)

        entries_to_append = list(map(self._au_file_to_nml_entry, sorted_new_au_files))
        self._num_new_entries += len(sorted_new_au_files)
        collection.extend(entries_to_append)

        return new_timestamp
    
    def close(self):
        self._overwrite_fh.seek(0)
        collection = self._et_tree.find("COLLECTION")
        if collection is not None:
            old_num_entries = int(collection.get("ENTRIES", 0).lstrip())
            collection.set("ENTRIES", str(old_num_entries + self._num_new_entries))
        self._et_tree.write(self._overwrite_fh, "unicode")
        self._overwrite_fh.truncate()

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
        for k, v in list(entry_data.items()):
            new_v = xml.sax.saxutils.quoteattr(str(v))
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
