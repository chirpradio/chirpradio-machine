"""Utilities for importing audio files into the music library."""

import errno
import os
import sys
import hashlib

import mutagen.id3

from chirp.library import artists
from chirp.library import audio_file
from chirp.library import checker
from chirp.library import constants
from chirp.library import order
from chirp.library import titles


class ImportFileError(Exception):
    """Raised when a file import fails."""


def _fix_file_tags(au_file):
    """Modify a file's tags to conform to CHIRP's tagging standards.

    Args:
      au_file: An AudioFile object

    Returns:
      A new mutagen.id3.ID3 object with the corrected tags.

    Raises:
      ImportFileError: if the tagging is broken or cannot be fixed.
    """
    if constants.MUTAGEN_UFID_KEY in au_file.mutagen_id3:
        raise ImportFileError(["File already contains CHIRP UFID tag"])

    new_id3 = mutagen.id3.ID3()

    # Build up a list of tags, stripping out ones that are not on our
    # whitelist.
    for tag in au_file.mutagen_id3.values():
        if tag.FrameID in constants.ID3_TAG_BLACKLIST:
            raise ImportFileError(["Found blacklisted tag: %r" % tag])
        if not (tag.FrameID in constants.ID3_TAG_WHITELIST
                and tag.FrameID not in constants.ID3_TAG_STRIPPED_ON_IMPORT):
            continue
        # Manually filter out TPOS
        # TODO(trow): We don't want to do this long-term.
        if tag.FrameID == "TPOS":
            continue
        # Standardize TPE tags, filtering out unknown artists at
        # TPE2 or lower.
        if tag.FrameID.startswith("TPE"):
            name_std = artists.standardize(unicode(tag))
            if name_std is None:
                if tag.FrameID != "TPE1":
                    sys.stderr.write("*** Filtering %s %s\n" % (
                            tag.FrameID, unicode(tag).encode("utf-8")))
                    continue
                raise ImportFileError(
                    [u"Unknown artist %r in %s" % (unicode(tag), tag.FrameID)])
            else:
                tag.text = [name_std]
        # If the TBPM tag is present and contains a string of the form
        # "xxx BPM", strip off the suffix.  If xxx is not an integer,
        # round it off.  If it is <= 0, discard the tag entirely.
        if tag.FrameID == "TBPM":
            tbpm = unicode(tag)
            if tbpm.endswith(" BPM"):
                tbpm = tbpm[:-4]
            try:
                tbpm = int(float(tbpm))
            except ValueError:
                continue
            if tbpm <= 0:
                continue
            tag.text = [unicode(tbpm)]

        new_id3.add(tag)

    # Add our own TLEN tag.
    tlen_tag = mutagen.id3.TLEN(text=[unicode(au_file.duration_ms)],
                                encoding=constants.DEFAULT_ID3_TEXT_ENCODING)
    new_id3.add(tlen_tag)

    # Add tags containing the number of frames and the frame size.

    frame_count_tag = mutagen.id3.TXXX(
        desc=constants.TXXX_FRAME_COUNT_DESCRIPTION,
        text=[unicode(au_file.frame_count)],
        encoding=constants.DEFAULT_ID3_TEXT_ENCODING)
    new_id3.add(frame_count_tag)

    frame_size_tag = mutagen.id3.TXXX(
        desc=constants.TXXX_FRAME_SIZE_DESCRIPTION,
        text=[unicode(au_file.frame_size)],
        encoding=constants.DEFAULT_ID3_TEXT_ENCODING)
    new_id3.add(frame_size_tag)

    # Add a TXXX tag with the album ID.
    txxx = mutagen.id3.TXXX(encoding=constants.DEFAULT_ID3_TEXT_ENCODING,
                            desc=constants.TXXX_ALBUM_ID_DESCRIPTION,
                            text=[unicode(au_file.album_id)])
    new_id3.add(txxx)

    # Add a TFLT tag indicating that this is an MP3.
    tflt_tag = mutagen.id3.TFLT(text=[u"MPG/3"],
                                encoding=constants.DEFAULT_ID3_TEXT_ENCODING)
    new_id3.add(tflt_tag)

    # Add the standard CHIRP TOWN tag.
    town_tag = mutagen.id3.TOWN(text=[constants.TOWN_FILE_OWNER],
                                encoding=constants.DEFAULT_ID3_TEXT_ENCODING)
    new_id3.add(town_tag)

    return new_id3


def standardize_file(au_file):
    """Correct and check a file's tags.

    Args:
      au_file: An AudioFile object.  This object's tags are corrected
        in-place.

    Raises:
      ImportFileError: if the tags are broken or cannot be fixed.
    """
    original_id3 = au_file.mutagen_id3    
    au_file.mutagen_id3 = _fix_file_tags(au_file)
    # Make sure our checker finds no errors.
    pre_write_tagging_errors = checker.find_tags_errors(au_file)
    if pre_write_tagging_errors:
        au_file.mutagen_id3 = original_id3  # Put back the original tags
        raise ImportFileError(
            ["Found pre-write errors"] + pre_write_tagging_errors)


def write_file(au_file, prefix):
    """Write a newly-imported file into the archive.

    Args:
      au_file: An AudioFile object.
      prefix: The library prefix that the file is being imported into.

    Returns:
      The full path to the newly-imported file.

    Raises:
      ImportFileError: if the import fails.
    """
    # Make sure the canonical directory exists.
    try:
        os.makedirs(au_file.canonical_directory(prefix))
    except OSError, ex:
        if ex.errno != errno.EEXIST:
            raise

    path = au_file.canonical_path(prefix)
    if os.path.exists(path):
        raise ImportFileError(["File exists: " + path])
    au_file.mutagen_id3.save(path)
    assert au_file.payload is not None
    out_fh = open(path, "a")
    out_fh.write(au_file.payload)
    out_fh.close()

    # Now make sure that the file we just wrote passes our checks.
    new_au_file = audio_file.scan(path)
    if new_au_file is None:
        raise ImportFileError(["New file damaged!"])
    new_au_file.volume = au_file.volume
    new_au_file.import_timestamp = au_file.import_timestamp
    post_write_tagging_errors = checker.find_tags_errors(new_au_file)
    if post_write_tagging_errors:
        os.unlink(path)
        raise ImportFileError(
            ["Found post-write errors!"] + post_write_tagging_errors)

    return path



