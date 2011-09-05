"""Analyzes an MP3 file, gathering statistics and looking for errors."""

import cStringIO
import hashlib
import os
from chirp.common import mp3_frame


# Files with fewer than this many MPEG frames will be rejected as
# invalid.  100 frames is about 2.6s of audio.
_MINIMUM_FRAMES = 100

_MINIMUM_REASONABLE_FILE_SIZE = 100<<10  # Files should be larger than 100k...
_MAXIMUM_REASONABLE_FILE_SIZE = 20<<20   # ...and smaller than 20MB.


class InvalidFileError(Exception):
    """Raised when a file appears to be invalid or somehow corrupted."""


# TODO(trow): Some of the validity checks in this function might be
# too strict.
def analyze(file_obj, au_file, compute_fingerprint=True, get_payload=True):
    """Populate an AudioFile object with information extracted from a file.

    Args:
      file_obj: A file-like object.
      au_file: An AudioFile object to store the results of the analysis in.
      compute_fingerprint: If False, do not compute a fingerprint.

    Returns:
      The same AudioFile object that was passed in as au_file, which
      should now have several fields set.

    Raises:
      InvalidFileError: if the file appears to be corrupted.
    """
    au_file.frame_count = 0
    au_file.frame_size = 0
    au_file.duration_ms = 0
    sha1_calc = hashlib.sha1()  # unused if compute_fingerprint is False.
    payload = cStringIO.StringIO()  # unused if get_payload is False.

    bit_rate_kbps_sum = 0
    expected_hdr = None
    first_bit_rate_kbps = None
    is_vbr = False

    for hdr, data_buffer in mp3_frame.split(file_obj):
        if hdr is None:
            continue

        au_file.frame_count += 1
        au_file.frame_size += len(data_buffer)
        au_file.duration_ms += hdr.duration_ms
        if compute_fingerprint:
            sha1_calc.update(data_buffer)
        if get_payload:
            payload.write(data_buffer)

        # If we've seen a valid header previously, make sure that all of the
        # fields that should match do actually match.
        if expected_hdr:
            if not hdr.match(expected_hdr):
                raise InvalidFileError(
                    "Bad header: found %s, expected %s (path=%s)" % (
                        hdr, expected_hdr, au_file.path))
            # Keep track of if this is a variable bit-rate file.
            if hdr.bit_rate_kbps != first_bit_rate_kbps:
                is_vbr = True

        # Add this frame's bit rate to our sum; we will use this to compute
        # the average bit rate.
        bit_rate_kbps_sum += hdr.bit_rate_kbps

        # If this is the first header we've seen, make a copy and then blank
        # out the fields that can vary.  All future headers are expected to
        # match this template.
        if expected_hdr is None:
            expected_hdr = hdr
            first_bit_rate_kbps = expected_hdr.bit_rate_kbps
            expected_hdr.bit_rate_kbps = None  # Might be a VBR file.
            expected_hdr.padding = None  # Not all frames are padded.
            expected_hdr.frame_size = None
            # You'd think that this would be constant, but MP3s
            # encountered in the wild prove otherwise.
            expected_hdr.protected = None

    if au_file.frame_count < _MINIMUM_FRAMES:
        raise InvalidFileError("Found only %d MPEG frames"
                               % au_file.frame_count)

    # Add the bit rate back into the template header, then return it.
    # If this is a VBR file, use the average bit rate instead.
    if is_vbr:
        expected_hdr.bit_rate_kbps = (
            float(bit_rate_kbps_sum) / au_file.frame_count)
    else:
        expected_hdr.bit_rate_kbps = first_bit_rate_kbps

    # Finishing populating and then return the AudioFile object.
    au_file.mp3_header = expected_hdr
    # Round the duration down to an integral number of microseconds.
    au_file.duration_ms = int(au_file.duration_ms)
    if compute_fingerprint:
        au_file.fingerprint = sha1_calc.hexdigest()
    if get_payload:
        au_file.payload = payload.getvalue()
    return au_file


def sample_and_analyze(au_file, mp3_path_list):
    """Pick a representative file from a list of filenames and analyze it.

    Args:
      mp3_path_list: A list of paths to MP3 files.
    
    Returns:
      A representative MP3 header from a file whose size
      is approximately equal to the the median of those in the list.
    """
    if not mp3_path_list:
        return None
    sizes_and_paths = sorted((os.stat(path).st_size, path)
                             for path in mp3_path_list)
    # Find the median element.
    size, sample_path = sizes_and_paths[len(sizes_and_paths)/2]
    # Complain if file is < 100k or > 20M
    if (size < _MINIMUM_REASONABLE_FILE_SIZE
        or size > _MAXIMUM_REASONABLE_FILE_SIZE):
        raise InvalidFileError("Sample file has bad size: %s %d" % (
            sample_path, size))
    f_in = open(sample_path)
    try:
        analyze(f_in, au_file, compute_fingerprint=False)
    finally:
        f_in.close()
    # We return only the MP3 header, since the rest of the au_file
    # information is tied to that specific file.
    return au_file.mp3_header

