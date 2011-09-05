"""Code for parsing with bulk tagging forms."""

import hashlib
import logging
import re
import sys


VERIFIED = "verified"
QUESTION = "???"
DUPLICATE = "duplicate"
DELETE = "delete"
TALB_MISMATCH = "TALB mismatch"

# Example:
# a7314af4 [ 1 ] 192 12 Mer de Noms
LINE_RE = re.compile(r"([0-9a-f]{8})\s+\[([^\]]*)\]\s+(\d+)\s+\d+\s+(.+)",
                     re.UNICODE)

# Example match is between >> <<:
# >>00123--------- <<A Perfect Circle
NEW_SECTION_RE = re.compile(r"^\d{5}-{9}\s(.*)", re.UNICODE)


def _update(this_batch, artist, results):
    dup_resolver = {}
    for dir_hash, code, bitrate_str, talb in this_batch:

        code = code.strip()
        bitrate = int(bitrate_str)
        save = False

        if not code:
            results[dir_hash] = (VERIFIED, artist, talb)
        elif code.lower() == "x":
            results[dir_hash] = (DELETE, artist, talb)
        elif code == "?":
            results[dir_hash] = (QUESTION, artist, talb)
        elif code in dup_resolver:
            (other_dir_hash, other_bitrate,
             artist, other_talb) = dup_resolver[code]
            if talb != other_talb:
                # Note that this will produce strange results in the presense
                # of repeated mismatches.  Oh well.
                msg = '"%s" vs. "%s"' % tuple(sorted([talb, other_talb]))
                results[dir_hash] = (TALB_MISMATCH, artist, talb, msg)
                results[other_dir_hash] = (TALB_MISMATCH,
                                           artist, other_talb, msg)
                logging.warn("TALB mismatch: %s", msg)
            elif other_bitrate < bitrate:
                results[other_dir_hash] = (DUPLICATE, artist, talb)
                save = True
            else:
                results[dir_hash] = (DUPLICATE, artist, talb)
        else:
            save = True

        if save:
            dup_resolver[code] = (dir_hash, bitrate, artist, talb)

    # Move anything left in our dup_resolver dict into results.
    for dir_hash, _, artist, talb in dup_resolver.itervalues():
        if dir_hash not in results:
            results[dir_hash] = (VERIFIED, artist, talb)


def get_path_hash(full_dirpath):
    """Map a full directory name to a bulk tagging form hash key."""
    return hashlib.md5(full_dirpath).hexdigest()[:8]


def parse_file(file_obj):
    """Parse a human-editted bulk tagging form, and return a dict.

    Args:
      file_obj: A file-like object to read the form from.

    Returns:
      A dict mapping hashed paths to (action code, artist, album, ...) tuples.
    """
    results = {}

    this_batch = []
    artist = None
    for line in file_obj:
        match = NEW_SECTION_RE.match(line)
        if match:
            _update(this_batch, artist, results)
            artist = match.group(1)
            this_batch = []
            continue
        line = line.strip()
        match = LINE_RE.search(line)
        if match:
            this_batch.append([x.strip() for x in match.groups()])
        elif line:
            logging.info("Skipping line %r\n", line)

    _update(this_batch, artist, results)

    return results


