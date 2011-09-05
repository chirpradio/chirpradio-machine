
"""
Utilities related to MP3 (MPEG vers 1 layer III) audio headers.

This file is based on information found at:
  http://www.datavoyage.com/mpgscript/mpeghdr.htm

"""

import struct

# Channel codes
STEREO = 0
JOINT_STEREO = 1
DUAL_MONO = 2
MONO = 3

# Convert a channel code to a string
_CHANNELS_TO_STR = {
    STEREO: 'stereo',
    JOINT_STEREO: 'joint_stereo',
    DUAL_MONO: 'dual_mono',
    MONO: 'mono',
    None: None,
}

# These following are lookup tables that are used when parsing the
# headers.

_PROTECTED_TABLE = (True, False)

_BIT_RATE_KBPS_TABLE = (0, 32, 40, 48, 56, 64, 80, 96,
                        112, 128, 160, 192, 224, 256, 320)

_SAMPLING_RATE_HZ_TABLE = (44100, 48000, 32000)

_PADDING_TABLE = (False, True)

# Every MP3 frame contains exactly 1152 samples.
_SAMPLES_PER_FRAME = 1152


def _match_eq(x, y):
    """Check equality, with None treated as a wildcard."""
    return (x is None) or (y is None) or (x == y)


class MP3Header(object):
    """Encapsulates the data in an MPEG vers 1 layer III audio frame header.
    
    Attributes:
      sampling_rate_hz: an int, the sampling rate frequency expressed in Hz
      bit_rate_kbps: an int, the bit rate expressed in Kbps
      channels: one of MONO, DUAL_MONO, STEREO, JOINT_STEREO
      channels_str: a human-readable string representation of the 'channels'
        attribute
      protected: a bool, if True the header is followed by a 16-bit CRC
      padding: a bool, if True the frame is padded by an extra slot
      frame_size: an int, the total size of the frame in bytes; this size
        includes both the header and the data
      duration_ms: a float, the total duration of this frame measured in
        milliseconds

    In a template for use with the match method, some of the above may be None.
    """

    def __init__(self, sampling_rate_hz=None, bit_rate_kbps=None,
                 channels=None, protected=None, padding=None):
        self.sampling_rate_hz = sampling_rate_hz
        self.bit_rate_kbps = bit_rate_kbps
        self.channels = channels
        self.channels_str = _CHANNELS_TO_STR[channels]
        self.protected = protected
        self.padding = padding
        self.frame_size = None
        self.duration_ms = None
        
        # Compute the size of the frame in bytes.
        if (bit_rate_kbps is not None
            and sampling_rate_hz is not None
            and padding is not None):
            self.frame_size = 144000 * bit_rate_kbps / sampling_rate_hz
            if padding:
                self.frame_size += 1

        # Compute the duration of the frame, in milliseconds.
        if sampling_rate_hz is not None:
            self.duration_ms = _SAMPLES_PER_FRAME * (1000.0 / sampling_rate_hz)

    def is_complete(self):
        """Returns True if this is a fully-specified header."""
        return (self.sampling_rate_hz is not None
                and self.bit_rate_kbps is not None
                and self.channels is not None
                and self.protected is not None
                and self.padding is not None)

    def match(self, hdr):
        """Compare this object to a template.

        Args:
          hdr: An MP3Header object

        Returns:
          True if all of the non-None attributes in hdr equal the
            corresponding attributes in this object, False otherwise.
        """
        return (_match_eq(self.protected, hdr.protected)
                and _match_eq(self.bit_rate_kbps, hdr.bit_rate_kbps)
                and _match_eq(self.sampling_rate_hz, hdr.sampling_rate_hz)
                and _match_eq(self.padding, hdr.padding)
                and _match_eq(self.channels, hdr.channels))

    def __str__(self):
        """Produce a human-readable version of this header."""
        attributes = []
        if self.sampling_rate_hz:
            attributes.append('%gKhz' % (self.sampling_rate_hz/1000.0))
        if self.bit_rate_kbps is not None:
            attributes.append('%gKbps' % self.bit_rate_kbps)
        if self.channels is not None:
            attributes.append(_CHANNELS_TO_STR[self.channels])
        if self.protected:
            attributes.append('prot')
        if self.padding:
            attributes.append('pad')
        return '[MP3Header %s]' % ' '.join(attributes)


def parse(data, offset=0):
    """Extract an MP3 header from the front of a data buffer.

    MP3 headers consist of 4 bytes, so this function will always fail
    (and return None) if 'data' is not at least that long.
 
    Args:
      data: A string containing an MP3 frame
      offset: If set, start looking for the MP3 frame at this offset

    Returns:
      An MP3Header object, or None if 'data' is not prefixed by a
      valid header.
    """
    if len(data) < offset + 4:
        return None

    frame_data = struct.unpack_from('>I', data, offset=offset)[0]
    # 0xff is used as the frame synch byte in MPEG audio.
    # This particular condition identifies the frame as being part
    # of MPEG version 1 and layer III.
    if (frame_data >> 16) & 0xFFFE != 0xFFFA:
        return None

    protected_raw = (frame_data >> 16) & 0x1
    protected = _PROTECTED_TABLE[protected_raw]

    bit_rate_raw = (frame_data >> 12) & 0xF
    if bit_rate_raw == 0xF:
        return None
    bit_rate_kbps = _BIT_RATE_KBPS_TABLE[bit_rate_raw]
    # "free format" is not supported.
    if bit_rate_kbps == 0:
        return None

    sampling_rate_raw = (frame_data >> 10) & 0x3
    if sampling_rate_raw == 3:
        return None
    sampling_rate_hz = _SAMPLING_RATE_HZ_TABLE[sampling_rate_raw]

    padding_raw = (frame_data >> 9) & 0x1
    padding = _PADDING_TABLE[padding_raw]

    # We ignore the "private" bit.

    channels = (frame_data >> 6) & 0x3

    # We ignore the "channel mode extension" bits.
    # We ignore the "copyright" bit.
    # We ignore the "original" bit.
    # We also ignore the "emphasis" bits.

    return MP3Header(protected=protected,
                     bit_rate_kbps=bit_rate_kbps,
                     sampling_rate_hz=sampling_rate_hz,
                     padding=padding,
                     channels=channels)


def find(data, expected_hdr=None):
    """Find the next MP3 header in a data buffer.

    Args:
      data: a buffer containing a slice of an MP3 audio stream
      expected_hdr: an optional template that the returned header
        must match; specifying this can help avoid accidentally finding
        spurious frames inside a corrupted stream

    Returns:
      A 2-tuple of the form (hdr, offset).
        If hdr is None, there is guaranteed to be no frame up to the offset.
        Otherwise hdr is an MP3Header object describing the frame that begins
        at the offset.
    """
    i = 0
    len_data = len(data)
    while i < len_data:
        i = data.find('\xff', i)
        # No frame synch byte found
        if i == -1:
            return None, len_data
        # We found a possible frame, but there is not enough data.
        if i+4 > len_data:
            return None, i
        # Pull out the header; if it matches the expected header
        # template, return it.
        hdr = parse(data, offset=i)
        if hdr and (expected_hdr is None or hdr.match(expected_hdr)):
            return hdr, i
        # Otherwise this was not actually the beginning of a new frame,
        # so move forward one byte and keep looking.
        i += 1
    return None, len_data


def from_mutagen(mutagen_mp3):
    """Construct a MP3Header from a mutagen.mp3.MP3 object.

    Args:
      mutagen_mp3: A mutagen.mp3.MP3 object.

    Returns:
      A representative (i.e. partially-populated) MP3Header describing
      the characteristics of the MP3 file represented by mutagen_mp3.
    """
    return MP3Header(
        sampling_rate_hz=mutagen_mp3.info.sample_rate,
        bit_rate_kbps=mutagen_mp3.info.bitrate / 1000.0,
        channels=mutagen_mp3.info.mode)
        
