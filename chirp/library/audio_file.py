"""Holds information about a single audio file."""

import os
import struct

import mutagen.id3
import mutagen.mp3

from chirp.common import mp3_header
from chirp.common import timestamp
from chirp.library import analyzer
from chirp.library import constants
from chirp.library import id3_text
from chirp.library import ufid


class AudioFile(object):
    """A container for holding data related to an audio file.
    
    Attributes:
      volume: An integer volume number for this file within our library.
      import_timestamp: The timestamp associated with the introduction
        of this file into our library.
      fingerprint: The file's fingerprint.
      album_id: An integer that uniquely identifies the album this track
        comes from.  Note that the album_id is not human-readable, and is
        not intrinsic to the file --- it must be initially set during the
        import process.
      frame_count: The number of MP3 frames in the file.
      frame_size: The total size of all MP3 frames, in bytes.
      mp3_header: A representative MP3 header.
      duration_ms: The total duration of the audio, represented as an
        integral number of milliseconds.
      mutagen_id3: A Mutagen-produced dict-like object containing ID3 tags
        for this file.
      path: The file's path, or None if the path is not known
        (or is not defined because of our context).
    """
    volume = None
    import_timestamp = None
    fingerprint = None

    album_id = None

    frame_count = None
    frame_size = None
    mp3_header = None
    duration_ms = None

    mutagen_id3 = None
    path = None
    
    payload = None

    def __eq__(self, other):
        def _mutagen_id3_set(obj):
            return set(repr(x) for x in obj.mutagen_id3.itervalues())
        return (self.volume == other.volume
                and self.import_timestamp == other.import_timestamp
                and self.fingerprint == other.fingerprint
                and self.album_id == other.album_id
                and self.frame_count == other.frame_count
                and self.frame_size == other.frame_size
                and str(self.mp3_header) == str(other.mp3_header)
                and self.duration_ms == other.duration_ms
                and _mutagen_id3_set(self) == _mutagen_id3_set(other)
                and self.path == other.path
                and self.payload == other.payload)

    def has_ufid(self):
        """Return True if we have enough info to construct a complete UFID."""
        return (self.volume is not None
                and self.import_timestamp is not None
                and self.fingerprint is not None)

    def ufid(self):
        """Returns this file's unique identifier.

        This call will fail if has_ufid() returns False.
        """
        return ufid.ufid(self.volume, self.import_timestamp, self.fingerprint)

    def ufid_tag(self):
        """Returns this file's mutagen.id3.UFID tag.

        This call will fail if has_ufid() returns False.
        """
        return ufid.ufid_tag(self.volume, self.import_timestamp,
                             self.fingerprint)

    def tpe1(self):
        """Returns this file's TPE1 tag as a unicode string, or None."""
        if self.mutagen_id3 is None:
            return None
        tpe1_tag = self.mutagen_id3.get("TPE1")
        if tpe1_tag is None:
            return None
        return unicode(tpe1_tag)

    def talb(self):
        """Returns this file's TALB tag as a unicode string, or None."""
        if self.mutagen_id3 is None:
            return None
        talb_tag = self.mutagen_id3.get("TALB")
        if talb_tag is None:
            return None
        return unicode(talb_tag)

    def tit2(self):
        """Returns this file's TIT2 tag as a unicode string, or None."""
        if self.mutagen_id3 is None:
            return None
        tit2_tag = self.mutagen_id3.get("TIT2")
        if tit2_tag is None:
            return None
        return unicode(tit2_tag)

    def canonical_directory(self, prefix=""):
        """Returns the storage directory for this file.

        This call will fail if has_ufid() returns False.

        Args:
          prefix: The directory prefix to use.

        Returns:
          The directory containing this file inside the storage tree
          rooted at 'prefix'.
        """
        return os.path.join(prefix,
                            ufid.ufid_prefix(self.volume,
                                             self.import_timestamp))

    def canonical_filename(self):
        """Returns the storage filename for this file.
        
        This call will fail if the fingerprint attribute is not set.
        """
        return "%s.mp3" % self.fingerprint

    def canonical_path(self, prefix=""):
        """Returns the full storage path for this file.

        This call will fail if has_ufid() returns False.

        Args:
          prefix: The directory prefix to use.

        Returns:
          The path to this file inside the storage tree rooted at 'prefix'.
        """
        return os.path.join(self.canonical_directory(prefix),
                            self.canonical_filename())


def _get_mp3(path):
    try:
        mp3 = mutagen.mp3.MP3(path)
    # TODO(trow): We might need to catch other exceptions too.
    except (mutagen.mp3.HeaderNotFoundError,
            # The frame-parsing code in mutagen/mp3.py does not
            # do strict-enough error checking, and can raise
            # struct.error when trying to parse a malformed file.
            struct.error):
        return None
    # Automatically clean up the text tags.
    for tag in mp3.itervalues():
        id3_text.standardize(tag)
    return mp3


def _tag_to_int(au_file, tag_key):
    tag = au_file.mutagen_id3.get(tag_key)
    if tag is None:
        return None
    try:
        return int(tag.text[0])
    except ValueError:
        return None


def scan_fast(path, _read_id3_hook=None):
    """Quickly produce an AudioFile object for the file at 'path'.

    This function avoids expensive calculations by assuming that the
    file is fully and correctly tagged.  It never sets the 'payload'
    field.  The 'duration_ms' field will be set based on the TLEN tag,
    if present.  The 'frame_count' and 'frame_size' will be set based
    on the CHIRP-specific TXXX tags, if present.

    Args:
      path: The path to an MP3 file.
      _read_id3_hook: An optional callable that takes a path and
        returns mutagen ID3 data.  Passing in None (the default) uses
        a default implementation.  This argument should only be used
        for testing.

    Returns:
      An AudioFile object describing the file at 'path', or None if it does
      not appear to be a valid MPEG file.
    """
    au_file = AudioFile()
    au_file.path = path
    au_file.mutagen_id3 = (_read_id3_hook or _get_mp3)(path)
    if au_file.mutagen_id3 is None:
        return None

    this_ufid = au_file.mutagen_id3.get(constants.MUTAGEN_UFID_KEY)
    if this_ufid:
        try:
            au_file.volume, au_file.import_timestamp, au_file.fingerprint = (
                ufid.parse(this_ufid.data))
        except ValueError:
            pass

    # Note we use the fact that mutagen_id3 is actually a mutagen.MP3 object.
    au_file.mp3_header = mp3_header.from_mutagen(au_file.mutagen_id3)

    # We assume that TLEN is accurate.  Note that it would make sense to
    # use au_file.mutagen_id3.info.length for this, but mutagen's length
    # computation is not reliable.
    au_file.duration_ms = _tag_to_int(au_file, "TLEN")

    # Try to get the frame_size and frame_count from the tags.  Again,
    # we assume these are accurate.
    au_file.frame_count = _tag_to_int(au_file, constants.TXXX_FRAME_COUNT_KEY)
    au_file.frame_size = _tag_to_int(au_file, constants.TXXX_FRAME_SIZE_KEY)

    # Try to pull the album ID out of a a tag.
    au_file.album_id = _tag_to_int(au_file, constants.TXXX_ALBUM_ID_KEY)

    return au_file
    

def scan(path, _read_id3_hook=None):
    """Produce an AudioFile object for the file at 'path'.

    This function inspects the entire file, computing the fingerprint
    and frame statistics.  The 'volume' and 'import_timestamp' fields
    are not set.

    This function is much more computationally expensive than scan_fast(),
    but is more accurate and produces more complete information.

    Args:
      path: The path to an MP3 file.
      _read_id3_hook: An optional callable that takes a path and
        returns mutagen ID3 data.  Passing in None (the default) uses
        a default implementation.  This argument should only be used
        for testing.

    Returns:
      An AudioFile object describing the file at 'path', or None if it
      does not appear to be a valid MPEG file.
    """
    au_file = AudioFile()
    au_file.path = path
    au_file.mutagen_id3 = (_read_id3_hook or _get_mp3)(path)
    if au_file.mutagen_id3 is None:
        return None

    file_obj = open(path)
    try:
        analyzer.analyze(file_obj, au_file)
    finally:
        file_obj.close()

    return au_file
