"""Output an NML file cataloging a set of audio files.

NML is an XML-based file format used by Traktor.  This code generates
NML version 11, which is used by Traktor Pro.
"""

import time
import copy
import os
import xml.sax.saxutils
# import xml.etree.ElementTree as ET
from lxml import etree as ET
import mmap
import re
import io

from chirp.common import timestamp
from chirp.common import unicode_util
from chirp.common.printing import cprint
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
        
        Methods:
          add_new_files: If a previous file is given, automatically detect
            new files based on timestamps and add them to the file in album/track order.
            If no previous file is given, generate a new NML file with all
            audio files from the database in album/track order.
          add_manual: Takes a list of audio files and adds them directly to the
            given NML file or creates a new NML file with these audio files.
            Doesn't do automatic timestamp detection or sorting.
            Currently untested, but also not used anywhere.
          close: Must call this to actually see changes in the file. Saves
            in-memory changes to the NML file in permanent storage.
        """
        self._num_modified_entries = 0
        self._num_new_entries = 0
        self._new_entries = []
        self._file_volume = file_volume
        self._file_volume_quoted = _traktor_path_quote(file_volume)
        self._root_dir = root_dir
        self._overwrite_fh = overwrite_fh
        self._db = db
        self._overwrite_fh.seek(0)
        try:
            self._is_file_empty = self._overwrite_fh.read(1) == ''
        except io.UnsupportedOperation:
            self._is_file_empty = True
        self._overwrite_fh.seek(0)
        if self._is_file_empty:
            self._et_tree = None
        else:
            try:
                self._et_tree = ET.parse(overwrite_fh)
            except ET.ParseError as err:
                raise ValueError(
                    f'File format: XML Parse error with code {err.code} and position {err.position}'
                )
    
    def _update_timestamp(self):
        subnodes_elem = self._et_tree.find("PLAYLISTS/NODE/SUBNODES")
        if subnodes_elem is None:
            raise ValueError('File format: SUBNODES element not found')

        for node_elem in subnodes_elem.iter("NODE"):
            if node_elem.get("NAME") != "_CHIRP":
                continue
            
            playlist_elem = node_elem.find("PLAYLIST")
            if playlist_elem is None:
                continue

            old_timestamp = playlist_elem.get("UUID")
            if old_timestamp is not None:
                new_timestamp = timestamp.now()
                playlist_elem.set("UUID", str(new_timestamp))
                return (old_timestamp, new_timestamp)

        # If timestamp is not found, add it to the NML file and consider all au files new
        node_elem = ET.SubElement(subnodes_elem, "NODE", {
            "TYPE": "PLAYLIST",
            "NAME": "_CHIRP",
        })
        ET.SubElement(node_elem, "PLAYLIST", {
            "ENTRIES": "0",
            "TYPE": "LIST",
            "UUID": str(timestamp.now()),
        })
        return (0, timestamp.now())

    def _au_file_to_nml_entry(self, au_file):
        import_date = time.strftime(
            "%Y/%m/%d", time.gmtime(au_file.import_timestamp))
        (order_num, total_num) = order.decode(str(au_file.mutagen_id3.get("TRCK")))

        entry_elem = ET.Element("ENTRY", {
            "MODIFIED_DATE": import_date,
            "MODIFIED_TIME": "35364",
            "TITLE": unicode_util.simplify(
                au_file.mutagen_id3.get("TIT2", _UNKNOWN_SONG)),
            "ARTIST": unicode_util.simplify(
                au_file.mutagen_id3.get("TPE1", _UNKNOWN_ARTIST)),
        })
        ET.SubElement(entry_elem, "LOCATION", {
            "DIR": _traktor_path_quote(
                au_file.canonical_directory(prefix=self._root_dir)),
            "FILE": au_file.canonical_filename(),
            "VOLUME": self._file_volume_quoted,
            "VOLUME_ID": "",
        })
        ET.SubElement(entry_elem, "ALBUM", {
            "OF_TRACKS": str(total_num),
            "TITLE": unicode_util.simplify(
                au_file.mutagen_id3.get("TALB", _UNKNOWN_ALBUM)),
            "TRACK": str(order_num),
        })
        ET.SubElement(entry_elem, "INFO", {
            "BITRATE": str(int(au_file.mp3_header.bit_rate_kbps * 1000)),
            "GENRE": "Unknown",
            "PLAYTIME": str(int(au_file.duration_ms / 1000)),
            "IMPORT_DATE": import_date,
            "FILESIZE": str(int(au_file.frame_size / 1024)),
        })
        return entry_elem

    def _modify_nml_entry(self, entry_elem, au_file):
        """Modifies a pre-existing entry in the NML file

        Args: 
          entry: An element tree element corresponding to the entry we want to modify
          au_file: The audio file with the new values we want to write in entry
        """
        modified_attrs = {}

        # Fields that are not modified:
            # Genre
            # Dir
            # Volume
            # File name - changing this would affect the unique fingerprint identifier we depend on
            # Bitrate - changing this would affect fingerprint
            # Duration - changing this would affect fingerprint
            # Modified time - is a hardset value in other places currently

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

        modified_attrs["import_date"] = time.strftime(
            "%Y/%m/%d", time.gmtime(au_file.import_timestamp))
        modified_attrs["modified_date"] = modified_attrs["import_date"]

        entry_elem.set("ARTIST", modified_attrs["artist"])
        entry_elem.set("TITLE", modified_attrs["song"])
        entry_elem.set("MODIFIED_DATE", modified_attrs["modified_date"])

        album_elem = entry_elem.find("ALBUM")
        if album_elem is None:
            raise ValueError(f'File format: No ALBUM subelement found in ENTRY element with fingerprint {au_file.fingerprint}')
        album_elem.set("OF_TRACKS", str(modified_attrs["total_num"]))
        album_elem.set("TRACK", str(modified_attrs["order_num"]))
        album_elem.set("TITLE", modified_attrs["album"])

        info_elem = entry_elem.find("INFO")
        if info_elem is None:
            raise ValueError(f'File format: No INFO subelement found in ENTRY element with fingerprint {au_file.fingerprint}')
        info_elem.set("FILESIZE", str(modified_attrs["size_in_kb"]))
        info_elem.set("IMPORT_DATE", modified_attrs["modified_date"])

    def _get_ordered_nml_entries(self, audio_files):
        # Sort new audio files so album order is maintained
        order_nums = {}
        def get_order_key(au_file):
            order_num = order_nums.get(au_file.fingerprint)
            if order_num is None:
                order_num, _ = order.decode(str(au_file.mutagen_id3.get("TRCK")))
                order_nums[au_file.fingerprint] = order_num
            return (au_file.album_id, order_num)
        sorted_new_au_files = sorted(audio_files, key=get_order_key)
        cprint("Finalizing NML...")
        return map(self._au_file_to_nml_entry, sorted_new_au_files)
    
    def _create_tree_prefix_suffix(self, import_timestamp):
        # create prefix
        root_elem = ET.Element("NML", { "VERSION": "14" })
        ET.SubElement(root_elem, "HEAD", {
            "COMPANY": "www.native-instruments.com",
            "PROGRAM": "Traktor - Native Instruments",
        })
        ET.SubElement(root_elem, "MUSICFOLDERS")
        collection_elem = ET.SubElement(root_elem, "COLLECTION", { "ENTRIES": "%10d" % 0})

        # create suffix
        playlists_elem = ET.SubElement(root_elem, "PLAYLISTS")
        folder_node_elem = ET.SubElement(playlists_elem, "NODE", {
            "TYPE": "FOLDER",
            "NAME": "$ROOT",
        })
        subnodes_elem = ET.SubElement(folder_node_elem, "SUBNODES", { "COUNT": "2"})
        recordings_node_elem = ET.SubElement(subnodes_elem, "NODE", {
            "TYPE": "PLAYLIST",
            "NAME": "_RECORDINGS",
        })
        ET.SubElement(recordings_node_elem, "PLAYLIST", {
            "ENTRIES": "0",
            "TYPE": "LIST",
        })
        timestamp_node_elem = ET.SubElement(subnodes_elem, "NODE", {
            "TYPE": "PLAYLIST",
            "NAME": "_CHIRP",
        })
        ET.SubElement(timestamp_node_elem, "PLAYLIST", {
            "ENTRIES": "0",
            "TYPE": "LIST",
            "UUID": str(import_timestamp),
        })

        return (root_elem, collection_elem)

    def _add_from_scratch(self):
        cprint("Creating new NML catalog from scratch...")
        new_timestamp = timestamp.now()
        (root_elem, collection_elem) = self._create_tree_prefix_suffix(new_timestamp)

        # Add each entry in the database
        new_entries = list(self._get_ordered_nml_entries(self._db.get_all()))
        collection_elem.extend(new_entries)
        # Update count of entries
        self._num_new_entries += len(new_entries)

        self._et_tree = ET.ElementTree(root_elem)

        return new_timestamp

    def _add_from_pre_existing(self):
        cprint("Updating existing NML catalog...")
        (last_modified, new_timestamp) = self._update_timestamp()

        try:
            new_audio_files = self._db.get_since_less_queries(int(last_modified))
        except ValueError as err:
            # The delimiter was found in one of the tags' values, making the
            # concatenated data impossible to parse
            print(f"{err}\n"
                  "Switching to slower database function.\n"
                  "We recommend you change the TAG_SEPARATOR value to avoid this.")
            new_audio_files = self._db.get_since(int(last_modified))

        # Store fingerprints and audio files of all files to add in a dictionary
        # so we can check if we have to modify them as we iterate through the file
        new_au_files_dict = {}
        for au_file in new_audio_files:
            new_au_files_dict[au_file.fingerprint] = au_file
        cprint("Found %s new or modified audio %s" % (len(new_au_files_dict), "file" if len(new_au_files_dict) == 1 else "files"))
        
        collection = self._et_tree.find("COLLECTION")
        if collection is None:
            raise ValueError("File format: No COLLECTION element found")

        for entry in collection.iter("ENTRY"):
            location = entry.find("LOCATION")
            if location is None:
                continue
            file_name = location.get("FILE")
            if file_name is None:
                continue
            fingerprint = file_name.split(".")[0]
            au_file = new_au_files_dict.get(fingerprint)
            if au_file is not None:
                self._modify_nml_entry(entry, au_file)
                self._num_modified_entries += 1
                del new_au_files_dict[fingerprint]

        entries_to_append = list(self._get_ordered_nml_entries(new_au_files_dict.values()))
        self._num_new_entries += len(entries_to_append)
        self._new_entries += entries_to_append

        return new_timestamp

    def add_new_files(self):
        if self._et_tree is None:
            return self._add_from_scratch()
        else:
            return self._add_from_pre_existing()
    
    # Option to add files manually without timestamp detection or sorting
    def add_manual(self, au_files):
        new_timestamp = time.now()
        if self._et_tree is None:
            (self._et_tree, collection_elem) = self._create_tree_prefix_suffix(new_timestamp)
        else:
            collection_elem = self._et_tree.find("COLLECTION")
            if collection_elem is None:
                raise ValueError("File format: No COLLECTION element found")
        
        new_entries = list(map(self._au_file_to_nml_entry, au_files))
        self._new_entries += new_entries

        return new_timestamp
    
    def _close_append_only(self):
        try:
            mapped_file = mmap.mmap(self._overwrite_fh.fileno(), 0)
        except:
            return False
        mapped_file.seek(0)
        matches = list(re.finditer(
            (br'<((\s*COLLECTION\s*ENTRIES\s*=\s*".{10}"\s*>)|'
             br'(/\s*ENTRY\s*>\s*</\s*COLLECTION\s*>[\S\s]*<\s*PLAYLISTS\s*>[\S\s]*</\s*PLAYLISTS\s*>))'),
            mapped_file
        ))
        if len(matches) != 2:
            return False

        entries_val_offset = matches[0].group().find(b'"')
        collection_tag_offset = matches[1].group().find(b'>') + 1
        playlist_match = re.search(br'<\s*PLAYLISTS', matches[1].group())
        if playlist_match is None:
            return False
        playlists_tag_offset = playlist_match.start()
        is_valid_matches = entries_val_offset != -1 and playlists_tag_offset != -1
        if not is_valid_matches:
            return False

        # Update entries attribute in COLLECTION tag
        entries_seek_pos = matches[0].start() + entries_val_offset + 1
        self._overwrite_fh.seek(entries_seek_pos)
        num_old_entries = int(self._overwrite_fh.read(10))
        num_total_entries = num_old_entries + self._num_new_entries

        self._overwrite_fh.seek(entries_seek_pos)
        self._overwrite_fh.write("%10d" % num_total_entries)

        # Append new entries and update timestamp
        playlists_match = matches[1]
        suffix_seek_start = playlists_match.start() + collection_tag_offset
        dist_btwn_suffix_playlists = playlists_tag_offset - collection_tag_offset
        playlists_seek_end = playlists_match.end()

        self._overwrite_fh.seek(suffix_seek_start)
        before_playlists_str = self._overwrite_fh.read(dist_btwn_suffix_playlists)
        self._overwrite_fh.seek(playlists_seek_end)
        after_playlists_str = self._overwrite_fh.read()

        playlists_str = playlists_match.group()[playlists_tag_offset:]
        playlists_elem = ET.fromstring(playlists_str)
        is_timestamp_present = False
        for node_elem in playlists_elem.iter("NODE"):
            node_type = node_elem.get("TYPE")
            node_name = node_elem.get("NAME")
            if node_type != "PLAYLIST" or node_name != "_CHIRP":
                continue
            playlist_elem = node_elem.find("PLAYLIST")
            if playlist_elem is None:
                continue
            playlist_elem.set("UUID", str(timestamp.now()))
            is_timestamp_present = True

        if not is_timestamp_present:
            subnodes_elem = playlists_elem.find("NODE/SUBNODES")
            if subnodes_elem is None:
                raise ValueError("File format: No SUBNODES element found")
            node_elem = ET.SubElement(subnodes_elem, "NODE", {
                "TYPE": "PLAYLIST",
                "NAME": "_CHIRP",
            })
            ET.SubElement(node_elem, "PLAYLIST", {
                "ENTRIES": "0",
                "TYPE": "LIST",
                "UUID": str(timestamp.now()),
            })

        append_str = ""

        for entry in self._new_entries:
            entry_str = ET.tostring(entry, encoding='unicode')
            append_str += entry_str + "\n"

        append_str += before_playlists_str

        append_str += ET.tostring(playlists_elem, encoding='unicode')

        append_str += after_playlists_str

        self._overwrite_fh.seek(suffix_seek_start)
        self._overwrite_fh.write(append_str)

        self._overwrite_fh.truncate()

        return True
    
    def close(self):
        if self._num_modified_entries == 0 and not self._is_file_empty\
            and self._close_append_only(): #_close_append_only returns True if it succeeds
                return

        collection = self._et_tree.find("COLLECTION")
        if collection is None:
            raise ValueError("File format: No COLLECTION element found")
        num_old_entries = int(collection.get("ENTRIES", 0))
        collection.set("ENTRIES", "%10d" % (num_old_entries + self._num_new_entries))
        collection.extend(self._new_entries)
        self._overwrite_fh.seek(0)
        self._overwrite_fh.write(ET.tostring(self._et_tree, encoding='unicode'))
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
