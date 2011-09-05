"""Schema for our music library database.

Our data model is extremely simple:
  * Our database contains audio file objects.
  * Each audio file is uniquely identified by a fingerprint.
  * Each audio file has many ID3 tags.
  * ID3 tags are partitioned into sets by a timestamp.
"""

from chirp.common import mp3_header
from chirp.library import audio_file


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
    value = u""
    if hasattr(tag, "text"):
        value = unicode(tag)
    return (fingerprint, timestamp, tag.FrameID, value, repr(tag))
