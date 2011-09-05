"""
Convert a stream into a sequence of MPEG audio frames.

"""

from chirp.common import id3_header
from chirp.common import mp3_header


# The size of the chunks of data we read from file_obj.  The largest
# possible MP3 frame is 1045 bytes; this value should be larger than
# that.  Keeping the value low helps performance by minimizing the
# number of string copies.
_READ_SIZE = 4 << 10  # 4k


def split(file_obj, expected_hdr=None):
    """Extract a sequence of MPEG audio frames from a file-like object.
    
    Args:
      file_obj: A file-like object
      expected_hdr: If given, only yield frames matching this MP3Header
        template

    Yields:
      A (hdr, data_buffer) pair.
      If 'hdr' is None, data buffer contains non-MPEG-audio junk that
      was found inside the stream.  Otherwise 'hdr' is an MP3Header object
      and 'data_buffer' contains the MP3 frame.
    """
    def block_generator():
        while True:
            block = file_obj.read(_READ_SIZE)
            if not block:
                break
            yield block

    for hdr, data_buffer in split_blocks(block_generator(),
                                         expected_hdr=expected_hdr):
        yield hdr, data_buffer


def split_blocks(block_iter, expected_hdr=None):
    """Extract a sequence of MPEG audio frames from a stream of data blocks.
    
    Args:
      block_iter: An iterable object that yields a sequence of data
        blocks.
      expected_hdr: If given, only yield frames matching this MP3Header
        template

    Yields:
      A (hdr, data_buffer) pair.
      If 'hdr' is None, data buffer contains non-MPEG-audio junk that
      was found inside the stream.  Otherwise 'hdr' is an MP3Header object
      and 'data_buffer' contains the MP3 frame.
    """
    buffered = ''
    current_hdr = None
    at_end_of_stream = False
    to_be_skipped = 0

    while True:
        # First we skip data if necessary.
        while to_be_skipped > 0:
            assert current_hdr is None
            # If we don't have anything in our buffer, pull in the
            # next block.
            if not buffered:
                try:
                    buffered = block_iter.next()
                except StopIteration:
                    sys.stderr.write(
                        "Stream ended while skipping data "
                        "between frames (probably ID3 headers).\n")
                    at_end_of_stream = True
                    break
            # If the buffer contains less than the amount of data to
            # be skipped, yield it all and update to_be_skipped.
            # Otherwise slice the amount to be skipped off of the
            # front of the buffer.
            if len(buffered) <= to_be_skipped:
                yield None, buffered
                to_be_skipped -= len(buffered)
                buffered = ''
            else:
                yield None, buffered[:to_be_skipped]
                buffered = buffered[to_be_skipped:]
                to_be_skipped = 0

        # We try to have at least _READ_SIZE bytes of data buffered.
        if len(buffered) < _READ_SIZE:
            # To avoid excess string copies, we collect data in a list
            # until we have the desired amount, then concatenate it all
            # at the end.
            buffered_list = [ buffered ]
            buffered_size = len(buffered)
            while buffered_size < _READ_SIZE:
                try:
                    next_block = block_iter.next()
                except StopIteration:
                    at_end_of_stream = True
                    break
                buffered_list.append(next_block)
                buffered_size += len(next_block)
            buffered = ''.join(buffered_list)

        # Are we at the end of the file?  If so, break out of the
        # "while True:" loop
        if not buffered:
            break

        # Do we have an MP3 header?  If so, yield the frame and then
        # slice it off of our buffer.
        if current_hdr:
            current_frame = buffered[:current_hdr.frame_size]
            # If we found a full-length frame, yield it.  Otherwise
            # return the truncated frame as junk.  (We can be sure not
            # to throw away a valid frame since we buffer at least the
            # next _READ_SIZE bytes, and _READ_SIZE is larger than any
            # possible MP3 frame.
            if len(current_frame) != current_hdr.frame_size:
                current_hdr = None
            yield current_hdr, current_frame
            current_hdr = None
            buffered = buffered[len(current_frame):]

        # Look for the next ID3 header.
        id3_size, id3_offset = id3_header.find_size(buffered)

        # Look for the next MP3 header.
        next_hdr, offset = mp3_header.find(buffered, expected_hdr=expected_hdr)

        # If we see an ID3 header before the next MP3 header, skip past the
        # ID3.  We do this out of paranoia, since an ID3 header might contain
        # false synch.
        if id3_size is not None and id3_offset < offset:
            to_be_skipped = id3_offset + id3_size
            continue
        
        # We are starting on this header.
        current_hdr = next_hdr

        # If we cannot make any progress and are at the end of the
        # stream, just return what we have buffered as junk and then
        # break out of the loop
        if (current_hdr, offset) == (None, 0) and at_end_of_stream:
            if buffered:
                yield None, buffered
            break

        # Did we find junk before the next frame?  If so, yield it.
        if offset > 0:
            yield None, buffered[:offset]
            buffered = buffered[offset:]


def split_one_block(data, expected_hdr=None):
    """Extract a sequence of MPEG audio frames from a single block of data.

    Args:
      data: A data buffer containing the data to be split into MPEG frames.

    Returns:
      A list of (hdr, data_buffer) pairs.
      If 'hdr' is None, data buffer contains non-MPEG-audio junk that
      was found inside the stream.  Otherwise 'hdr' is an MP3Header object
      and 'data_buffer' contains the MP3 frame.
    """
    return list(split_blocks(iter([data]), expected_hdr=expected_hdr))


# This is a 44.1Khz, 112Kbps joint stereo MPEG frame of digitized
# silence.  It was produced by sampling from a Barix with no active
# input.  Like any 44.1Khz MPEG frame, it has a duration of
# 26.12245ms.
_DEAD_AIR_DATA = (
    "\xff\xfa\x80\x48\x80\x3d\x00\x00\x02\x5f\x09\x4f\x79\x26\x31\x20"
    "\x4b\x81\x29\xcf\x24\xc2\x24\x09\x94\x23\x3f\xe3\x18\x44\x81\x1f"
    "\x84\x67\x3c\x92\x8c\x90\x8b\xbb\xab\xaa\x77\x6d\x76\x91\xb4\x54"
    "\x46\x74\x4e\xa8\xa1\x57\x75\x20\xa3\x8b\x98\xb3\x1e\xd1\xea\x78"
    "\x71\x86\xd2\x6d\x49\x71\x93\x93\x91\x45\xaa\x38\x73\xe2\xab\x26"
    "\xd8\xe9\xed\xa1\x0b\xb5\xc5\x6f\x36\xb6\x9f\x16\xba\xc4\x8a\x9e"
    "\x26\x7d\x75\x54\xf5\xa7\x2c\xb6\x1c\x41\x8a\x75\xf6\xb2\x0d\xac"
    "\x06\x2e\xd3\x55\x53\x30\xec\xb6\x59\x23\x44\x4b\x4f\x9a\x0f\x1a"
    "\x07\x03\x22\x38\xf1\xa1\xc3\x80\xc8\x25\x81\xe2\xe8\x11\x15\x87"
    "\x25\xf2\xeb\x4e\x31\xfd\x41\x6a\xa2\xf5\x20\x28\xbb\x07\x10\x0d"
    "\xac\xdb\xcb\x29\xe9\x1f\xd8\x86\xd6\xfa\x48\xe8\x1a\xa8\x9a\xeb"
    "\x90\xe1\xe7\x9e\x28\xe3\xe8\x15\x2f\xc0\x8f\xa5\x22\xd1\x79\x95"
    "\x75\x50\xcf\xbe\xda\xd8\xcd\x70\x00\xd0\x12\xc0\x21\x41\xc4\xa2"
    "\x40\xf1\x9c\x10\x9c\x12\xd8\x2a\x94\xcc\xa4\x09\x6c\xe9\x7a\x98"
    "\xe6\x15\x06\x5e\x96\xcf\x2b\xd6\xb6\xbb\x16\x68\xd4\xa5\xa2\xdc"
    "\x4f\x31\x02\xf4\x91\x50\x49\x4f\x58\xc2\xf3\xa6\x49\x0a\xb0\x3f"
    "\x1e\x2f\xdd\x7a\xca\x3d\xc3\x03\x54\x1b\x6a\xa9\x0a\x97\x74\x49"
    "\x24\xb1\xa2\x2b\x8e\x09\x08\x15\x81\xb1\xc4\x02\x82\x44\xa1\x30"
    "\x10\xc4\x21\xe5\x92\xb9\xfa\x49\xa0\x9a\xec\xf5\xbc\x51\x62\xe3"
    "\xd3\x60\x55\xac\x78\x77\x27\x4d\xe6\xda\x80\x71\x76\x54\x93\x2f"
    "\x52\xe0\x0f\xa9\xee\xb1\x54\x86\x0b\x2d\xf6\xd5\x53\x9a\x2d\x9c"
    "\x72\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")

_DEAD_AIR_DURATION_MS = mp3_header._SAMPLES_PER_FRAME / 44.1


def dead_air(approximate_duration_ms):
    """Returns MPEG data for dead air.

    Args:
      approximate_duration_ms: The approximate duration of the
        returned audio, in milliseconds.

    Returns:
      A string containing concatenated valid MPEG frames.  Regardless of
      the value of approximate_duration_ms, at least one frame worth of data
      will always be returned.
    """
    num_frames = int(0.5 + approximate_duration_ms / _DEAD_AIR_DURATION_MS)
    return _DEAD_AIR_DATA * max(1, num_frames)
      

