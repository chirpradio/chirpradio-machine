"""
Code related to ID3 frames.

Note that this code does let you parse ID3 frames; if you need to do
that you should use mutagen, not this code.  This code is strictly
designed to create simple ID3 text frames and locate ID3 frames (which
are treated as opaque binary blobs) inside a data stream.
"""

import struct
import mutagen.id3


def _create_text_frame(frame_tag, value):
    assert len(frame_tag) == 4
    assert frame_tag[0] == "T"
    value_encoded = value.encode("utf-8")
    # We add two to the length of the encoded string to account for
    # the encoding byte and the null termination.
    size_str = mutagen.id3.BitPaddedInt.to_str(len(value_encoded)+2, width=4)
    return "".join([frame_tag,
                    size_str,
                    "\0\0",  # Flags are all 0
                    "\x03",  # 3 = utf-8 encoding
                    value_encoded,
                    "\0",  # The utf-8 string must be null-terminated
                    ]
                   )


def create(tag_list):
    """Construct an ID3v2.4 tag consisting of a series of text frames.

    Args:
      tag_list: A sequence of (tag_name, tag_value) pairs.  tag_name should
        be a 4-character string starting with "T".  tag_value should be
        a unicode string.

    Returns:
      A string containing an ID3v2.4 tag that encoded the passed-in tags.
    """
    assert len(tag_list) > 0
    all_frames = "".join(_create_text_frame(tag, value)
                         for tag, value in tag_list)
    return "".join(["ID3\x04\0\0",  # Always create v2.4 frames with flags=0
                    mutagen.id3.BitPaddedInt.to_str(len(all_frames), width=4),
                    all_frames,
                    ])


def parse_size(data, offset=0):
    """Find the size of the ID3 frame at the front of the data buffer.

    ID3 headers are at least 10 bytes long; this function will always fail
    (and return None) if data is not at least that long.

    Args:
      data: A string containing an ID3 frame
      offset: If set, start looking for the ID3 frame at this offset,
        not at the beginning of data

    Returns:
      An integer containing the size of the ID3 frame, as extracted from
      the ID3 header.  If no valid header is found, None is returned.
    """
    if len(data) < offset + 10:
        return None
    id3, vmaj, unused_vrev, unused_flags, raw_size = struct.unpack_from(
        ">3sBBB4s", data, offset=offset)
    if id3 == "ID3" and 2 <= vmaj <= 4:
        size = mutagen.id3.BitPaddedInt(raw_size)
        # Skip ID3 tags that claim to have size 0.
        if size > 0:
            return size
    return None


def find_size(data):
    """Find the size and offset of the next ID3 frame in a data buffer.

    Args:
      data: a buffer containing a slice of an audio file that possibly
        contains an ID3 frame
    
    Returns:
      A 2-tuple of the form(size, offset).
        If size is None, there is guaranteed to be no ID3 frame up to the
        offset.  Otherwise a frame of size "size" (in bytes) begins at
        the given offset.
    """
    i = data.find("ID3")
    if i == -1:
        if data.endswith("I"):
            return None, len(data)-1
        elif data.endswith("ID"):
            return None, len(data)-2
        else:
            return None, len(data)
    if len(data) < i + 10:
        return None, i
    size = parse_size(data, offset=i)
    if size is not None:
        return size, i
    # Size is mangled, so skip past the tag.
    return None, i+3


def create_test_header(size):
    """Construct a test ID3 frame header for a frame of a given size.

    This should only be used for testing.

    Args:
      size: The size to encode into the ID3 frame header
      
    Returns:
      A string containing a 10-byte encoded ID3 frame header.
    """
    flags = 0  # Just 0 for now
    encoded_size = mutagen.id3.BitPaddedInt.to_str(size, width=4)
    return struct.pack(">3sBBB4s", "ID3", 4, 0, flags, encoded_size)

