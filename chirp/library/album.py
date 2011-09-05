"""
Code for dealing with albums.  Albums are collections of related AudioFiles.
"""

import hashlib
import os
from chirp.library import artists
from chirp.library import audio_file
from chirp.library import constants
from chirp.library import import_file
from chirp.library import order
from chirp.library import titles
from chirp.library import ufid


class AlbumError(Exception):
    """Raised by album-related errors."""


def _compute_album_id(all_au_files):
    # To generate an album ID in a deterministic way, we sort and concatenate
    # the track fingerprints, and then compute a 60-bit hash of the resulting
    # blob by taking the top 15 hex digits of the MD5 checksum.  (We use
    # 60 instead of 64 bits because sqlite gets angry if you try to add a 
    # value > 2^63 to an integer-typed column.)
    #
    # Obviously we can only do this if all of the audio files have
    # fingerprints; if not, None is returned.
    if not all(x.fingerprint is not None for x in all_au_files):
        return None
    hasher = hashlib.new("md5")
    for fp in sorted(au_file.fingerprint for au_file in all_au_files):
        hasher.update(fp)
    return int(hasher.hexdigest()[:15], 16)


def _standardize_tags(all_au_files, new_album_name=None):
    """Perform album-level standardizations on a set of tags.

    Args:
      all_au_files: A list of AudioFile objects corresponding to all of the
        tracks on a single album.
      new_album_name: If not None, the text of the TALB tag is replaced
        by this string.

    If necessary, the AudioFile objects are modified in place, moving
    guest artists from TPE1 into TIT2.

    Raises:
      AlbumError: if the there are gaps or problems with the track numbers,
        or if the TALB tag is not consistent across all of the tracks.
    """
    # Check that both TPE1 and TIT2 are present in every file.
    for au_file in all_au_files:
        if "TPE1" not in au_file.mutagen_id3:
            raise AlbumError("Missing TPE1 in %s" % au_file.path)
        if "TIT2" not in au_file.mutagen_id3:
            raise AlbumError("Mising TIT2 in %s" % au_file.path)

    # Check that the album names all match.
    all_talb = set(unicode(au_file.mutagen_id3["TALB"])
                   for au_file in all_au_files)
    if len(all_talb) != 1:
        # Is the inconsistency only an issue of upper vs. lower case?
        # If so, pick the version that is in the majority.
        if len(set(x.lower() for x in all_talb)) == 1:
            freq = {}
            for x in all_talb:
                freq[x] = freq.get(x, 0) + 1
            all_talb = set([sorted((n, x) for x, n in freq.items())[0][1]])
        else:
            raise AlbumError("Inconsistent album names: %s" %
                              " / ".join(all_talb))

    # Standardize the album name.
    album_name = titles.standardize(new_album_name or all_talb.pop())
    if album_name is None:
        raise AlbumError('Invalid album name: "%s"' % album_name)
    for au_file in all_au_files:
        au_file.mutagen_id3["TALB"].text = [ album_name ]

    # Check and clean up track numbering.
    for au_file in all_au_files:
        if not "TRCK" in au_file.mutagen_id3:
            raise AlbumError("Missing TRCK tag in %s" % au_file.path)
    all_trck = [au_file.mutagen_id3["TRCK"] for au_file in all_au_files]
    try:
        order.verify_and_standardize(all_trck)
    except order.BadOrderError, ex:
        raise AlbumError(str(ex))

    # Construct a set of all of the artist names attached to these
    # tracks.
    all_tpe1 = set(unicode(au_file.mutagen_id3["TPE1"])
                   for au_file in all_au_files)

    for au_file in all_au_files:
        tit2 = unicode(au_file.mutagen_id3["TIT2"])
        # If artist name's don't all match, attempt to extract
        # guest artists and move them into the song titles.
        if len(all_tpe1) > 1:
            tpe1 = unicode(au_file.mutagen_id3["TPE1"])
            new_tpe1, guest = artists.split_and_standardize(tpe1)
            if new_tpe1 is None:
                raise AlbumError("Bad TPE1: %s" % repr(tpe1))
            elif tpe1 != new_tpe1:
                au_file.mutagen_id3["TPE1"].text = [new_tpe1]
            if guest is not None:
                guest_str = constants.TIT2_IMPORT_GUEST_FORMAT % {
                    'guest': guest }
                # We need to append the guest artist in a way that
                # respects any [tags] in the song title.
                tit2 = titles.append(tit2, guest_str)
        # Standardize and store the track name.
        std_tit2 = titles.standardize(tit2)
        if std_tit2 is None:
            raise AlbumError("Bad track name: %s" % tit2)
        au_file.mutagen_id3["TIT2"].text = [std_tit2]

    # Now attach an album ID to each track.
    album_id = _compute_album_id(all_au_files)
    for au_file in all_au_files:
        au_file.album_id = album_id


class Album(object):
    
    def __init__(self, all_au_files):
        self.all_au_files = list(all_au_files)
        # Compute the album ID.
        self.album_id = _compute_album_id(self.all_au_files)
        if self.album_id is not None:
            # If the files do not have an album ID, attach it.  Otherwise
            # check that the attached ID is correct.
            for au in self.all_au_files:
                if au.album_id is None:
                    au.album_id = self.album_id
                elif au.album_id != self.album_id:
                    raise AlbumError("Album ID mismatch while building Album")
        # Sort, but only if all of the albums have track numbers.
        if all("TRCK" in x.mutagen_id3 for x in self.all_au_files):
            self._sort()
        self._tpe1_breakdown = None

    def _sort(self):
        """Sort an album's audio files by track order."""
        self.all_au_files.sort(key=lambda x: +x.mutagen_id3["TRCK"])

    def standardize(self, new_album_name=None):
        # First standardize the album-level tags.
        _standardize_tags(self.all_au_files, new_album_name)
        # Finally standardize the file-level tags.
        for au in self.all_au_files:
            import_file.standardize_file(au)
        self._sort()

    def set_volume_and_import_timestamp(self, vol, imp_ts):
        for au in self.all_au_files:
            if au.fingerprint is None:
                raise AlbumError("Can't set vol/timestamp on fp-less file")
            au.volume = vol
            au.import_timestamp = imp_ts
            au.mutagen_id3[constants.UFID_OWNER_IDENTIFIER] = ufid.ufid_tag(
                vol, imp_ts, au.fingerprint)

    def drop_payloads(self):
        for au in self.all_au_files:
            au.payload = None

    def ensure_payloads(self):
        for au in self.all_au_files:
            if au.payload is None:
                new_au = audio_file.scan(au.path)
                assert new_au.fingerprint == au.fingerprint
                au.payload = new_au.payload

    def title(self):
        """Returns the album's title."""
        title, _ = titles.split_tags(
            unicode(self.all_au_files[0].mutagen_id3["TALB"]))
        return title

    def tags(self):
        """Returns the album's tags."""
        _, tags = titles.split_tags(
            unicode(self.all_au_files[0].mutagen_id3["TALB"]))
        return tags


    def _get_tpe1_breakdown(self):
        if self._tpe1_breakdown is None:
            count = {}
            for au in self.all_au_files:
                tpe1 = unicode(au.mutagen_id3["TPE1"])
                count[tpe1] = count.get(tpe1, 0) + 1
            self._tpe1_breakdown = [
                (n, tpe1) for tpe1, n in count.iteritems()]
            self._tpe1_breakdown.sort()
            self._tpe1_breakdown.reverse()
        return self._tpe1_breakdown

    def is_compilation(self):
        """Returns True if this is a multi-artist compliation."""
        # We call the album a compilation if less than 66% of the
        # songs are by a single artist.  Obviously this is a somewhat
        # arbitrary rule.
        breakdown = self._get_tpe1_breakdown()
        return breakdown[0][0] < 0.66*len(self.all_au_files)

    def artist_name(self):
        if self.is_compilation():
            return None
        breakdown = self._get_tpe1_breakdown()
        return breakdown[0][1]

    def all_artist_names():
        return sorted(x[1] for x in self._get_tpe1_breakdown())

    def import_timestamp(self):
        return self.all_au_files[0].import_timestamp

    def __str__(self):
        prefix = u'%x:%d "%s", ' % (
            self.album_id, len(self.all_au_files), self.title())
        if self.is_compilation():
            suffix = "-compilation-"
        else:
            suffix = self.artist_name()
        return prefix + suffix
        

def from_directory(dirpath, fast=False):
    """Creates Album objects from the files in a directory.

    Found audio files are grouped into albums based on their TALB tags.
    Non-audio files are silently ignored.

    Args:
      dirpath: The path to the directory to scan for audio files.
      fast: If True, do a fast scan when analyzing the audio files.

    Returns:
      A list of Album objects.
    """
    by_talb = {}
    for basename in os.listdir(dirpath):
        file_path = os.path.join(dirpath, basename)
        # Skip anything that isn't a regular file.
        if not os.path.isfile(file_path):
            continue
        # Skip dotfiles
        if basename.startswith("."):
            continue
        # Must have mp3 as the extension.
        if not basename.lower().endswith(".mp3"):
            continue
        if fast:
            au_file = audio_file.scan_fast(file_path)
        else:
            au_file = audio_file.scan(file_path)
        # Silently skip anything that seems bogus.
        if not au_file:
            continue
        if not "TALB" in au_file.mutagen_id3:
            raise AlbumError("Missing TALB tag on %s" % file_path)
        talb = au_file.mutagen_id3["TALB"].text[0]
        by_talb.setdefault(talb, []).append(au_file)

    return [Album(all_au_files) for all_au_files in by_talb.values()]
            
