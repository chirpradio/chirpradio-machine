"""Schema for our music library database.

Our data model is extremely simple:
  * Our database contains audio file objects.
  * Each audio file is uniquely identified by a fingerprint.
  * Each audio file has many ID3 tags.
  * ID3 tags are partitioned into sets by a timestamp.
"""
import re

from chirp.common import mp3_header
from chirp.library import audio_file

# Schema version 0 (legacy tables)

create_audio_files_table = """
CREATE TABLE audio_files (
  volume INTEGER,            /* volume number */
  import_timestamp INTEGER,  /* seconds since the epoch */
  fingerprint TEXT UNIQUE,   /* SHA1 hash of the MPEG frames */
  album_id INTEGER,          /* Unique identifier for source album. */
  sampling_rate_hz INTEGER,  /* Audio sampling rate, measured in Hz */
  bit_rate_kbps INTEGER,     /* File bit rate, measued in kbps */
  channels INTEGER,          /* MPEG channel identifier */
  frame_count INTEGER,       /* total number of MPEG frames */
  frame_size INTEGER,        /* total size of all MPEG frames, in bytes */
  duration_ms INTEGER        /* song duration, measured in milliseconds */
)
"""

# Audio files are uniquely identified by their fingerprints.
create_audio_files_index = """
CREATE UNIQUE INDEX audio_files_index_fingerprint
ON audio_files ( fingerprint )
"""


create_id3_tags_table = """
CREATE TABLE id3_tags (
    fingerprint TEXT,  /* Fingerprint of the file this tag is part of */
    timestamp INTEGER, /* Timestamp of this ID3 tag */
    frame_id TEXT,     /* The value of this_mutagen_id3_tag.FrameID */
    value TEXT,        /* For text tags,  unicode(this_mutagen_id3_tag) */
    mutagen_repr TEXT  /* Very Python- and Mutagen-specific */
)
"""


create_id3_tags_index = """
CREATE INDEX id3_tags_index_fingerprint
ON id3_tags ( fingerprint, timestamp DESC )
"""

# Schema version 1

enable_foreign_keys = """
PRAGMA foreign_keys = ON;
"""

create_last_modified = """
CREATE TABLE last_modified (
    fingerprint TEXT UNIQUE,           /* fingerprint of corresponding file */
    modified_timestamp INTEGER,        /* seconds since the epoch,
                                          time the metadata was last modified */
    FOREIGN KEY(fingerprint) REFERENCES audio_files(fingerprint)
)
"""

create_last_modified_index = """
CREATE UNIQUE INDEX last_modified_index_fingerprint
ON last_modified ( fingerprint )
"""

populate_last_modified = """
INSERT INTO last_modified (fingerprint, modified_timestamp)
    SELECT fingerprint, import_timestamp FROM audio_files;
"""

# List of database migrations to run when creating the database.
# Each item in this list is a list of SQLite queries to run to migrate
# to a new version of the database. The version number is saved in
# the SQLite user_version pragma.
MIGRATIONS = [
        [create_audio_files_table,
         create_audio_files_index,
         create_id3_tags_table,
         create_id3_tags_index], # schema version 0 (original)
        [enable_foreign_keys,
         create_last_modified,
         create_last_modified_index,
         populate_last_modified]] # schema version 1 (adds last_modified table)
LATEST_VERSION = len(MIGRATIONS) - 1

# Names of legacy (unversioned) tables to check for;
# if these do not exist, migration will start at schema version 0.
# If these do exist, migration will start at schema version 1.
LEGACY_TABLES = ["id3_tags", "audio_files"]

# Application ID to use in the sqlite3 header.
APPLICATION_ID = int.from_bytes(b"CHRP")


def audio_file_to_tuple(au_file):
    """Turn an AudioFile object into an insertable tuple."""
    return (au_file.volume,
            au_file.import_timestamp,
            au_file.fingerprint,
            au_file.album_id,
            au_file.mp3_header.sampling_rate_hz,
            au_file.mp3_header.bit_rate_kbps,
            au_file.mp3_header.channels,
            au_file.frame_count,
            au_file.frame_size,
            au_file.duration_ms)

def audio_file_to_last_modified(au_file):
    """Turn an AudioFile object into a tuple for the last_modified table."""
    return (au_file.fingerprint, au_file.import_timestamp)


def tuple_to_audio_file(au_file_tuple):
    """Convert a tuple into a new AudioFile object.

    This is the inverse of audio_file_to_tuple.
    """
    au_file = audio_file.AudioFile()
    (au_file.volume,
     au_file.import_timestamp,
     au_file.fingerprint,
     raw_album_id,
     sampling_rate_hz,
     bit_rate_kbps,
     channels,
     au_file.frame_count,
     au_file.frame_size,
     au_file.duration_ms) = au_file_tuple
    au_file.album_id = int(raw_album_id)
    au_file.mp3_header = mp3_header.MP3Header(
        sampling_rate_hz=sampling_rate_hz,
        bit_rate_kbps=bit_rate_kbps,
        channels=channels)
    return au_file


def id3_tag_to_tuple(fingerprint, timestamp, tag):
    """Turn a Mutagen ID3 tag object into an insertable tuple."""
    value = ""

    if hasattr(tag, "text"):
        value = str(tag)

    tag_repr = repr(tag)
    index = tag_repr.find(">")
    if index > -1:
        encoding = tag_repr[index - 1]
        tag_repr = re.sub("encoding=<.+>", f"encoding={encoding}", tag_repr)

    return (fingerprint, timestamp, tag.FrameID, value, tag_repr)
