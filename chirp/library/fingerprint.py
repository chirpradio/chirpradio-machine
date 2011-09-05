"""
Compute a metadata-invariant "fingerprint" from an MP3 file.

The fingerprint consists of 40 lowercase hex digits, and is produced
by computing the SHA1 hash of the MP3 file's MPEG frames.  This
ensures that the fingerprint depends only on the digitized audio and
is independent of the file's ID3 tags.

The fingerprint is used as a globally unique identifier inside the
music library, and is stored in a file's UFID tag.
"""

import hashlib
from chirp.common import mp3_frame


def compute(file_obj):
    """Compute a metadata-invariant fingerprint from an MP3 file.

    Args:
      file_obj: A file-like object

    Returns:
      A string containing the fingerprint, which takes the form of
      a 40-character sequence of hex digits.  If no valid MPEG frames
      are found, None is returned.
    """
    sha1_calc = hashlib.sha1()
    saw_a_valid_frame = False
    for hdr, data_buffer in mp3_frame.split(file_obj):
        if hdr is not None:
            sha1_calc.update(data_buffer)
            saw_a_valid_frame = True
    if saw_a_valid_frame:
        return sha1_calc.hexdigest()
    else:
        return None


def is_valid(fingerprint_str):
    """Check if a string is a well-formed fingerprint.

    Args:
      fingerprint_str: An object that might be a fingerprint.

    Returns:
      True if fingerprint_str appears to be a fingerprint produced by
      the compute() function.  Note that this does not check if fingerprint
      actually belongs to particular file, it only validates that the
      fingerprint is well-formed.
    """
    # Fingerprints must be strings.
    if not isinstance(fingerprint_str, str):
        return False
    # They must have length 40.
    if len(fingerprint_str) != 40:
        return False
    # They must be a sequence of hex digits.
    try:
        as_int = int(fingerprint_str, 16)
    except ValueError:
        return False
    # They must be greater than or equal to 0.
    if as_int < 0:
        return False
    # Re-encoding the integer as 0-padded hex should produce the same result.
    # (This ensures fingerprint_str doesn't contain stray whitespace or
    # uppercase digits.)
    if fingerprint_str != ("%040x" % as_int):
        return False
    # If we made it this far, the fingerprint is OK.
    return True
