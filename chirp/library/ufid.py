"""
Construct and parse our unique file identifiers (UFIDs).

A UFID encodes three pieces of information in a "/"-separated triple:
  * A volume number
  * A deposit timestamp
  * A fingerprint
"""

import re
import mutagen.id3
from chirp.common import timestamp
from chirp.library import constants
from chirp.library import fingerprint

_UFID_RE = re.compile(r"^vol([0-9a-f]{2})/([0-9T:-]+)/([0-9a-f]{40})$")


def ufid_prefix(volume, import_timestamp):
    """Returns the prefix of a UFID string.

    Args:
      volume: An integer volume number
      import_timestamp: A timestamp

    Returns:
      The leading substring of all UFIDs with the given volume and timestamp.
    """
    return "vol%02x/%s/" % (volume,
                            timestamp.get_human_readable(import_timestamp))


def ufid(volume, import_timestamp, fingerprint):
    """Returns a full UFID string.

    Args:
      volume: An integer volume number
      import_timestamp: A integer timestamp
      fingerprint: A string containing a fingerprint

    Returns:
      A string containing a UFID.
    """
    return ufid_prefix(volume, import_timestamp) + fingerprint


def ufid_tag(volume, import_timestamp, fingerprint):
    """Returns a mutagen UFID tag.

    Args:
      volume: An integer volume number
      import_timestamp: A integer timestamp
      fingerprint: A string containing a fingerprint

    Returns:
      A populated mutagen.id3.UFID instance.
    """
    return mutagen.id3.UFID(owner=constants.UFID_OWNER_IDENTIFIER,
                            data=ufid(volume, import_timestamp, fingerprint))
    

def parse(ufid_str):
    """Extract information from a UFID string.
    
    Args:
      ufid_str: A string, probably produced by a prior call to ufid()
      
    Returns:
      A (volume number, deposit timestamp, fingerprint) 3-tuple.

    Raises:
      ValueError: if ufid_str is invalid.
    """
    match = _UFID_RE.match(ufid_str)
    if match:
        vol = int(match.group(1), 16)
        ts = timestamp.parse_human_readable(match.group(2))
        fp = match.group(3)
        if vol > 0 and timestamp.is_valid(ts) and fingerprint.is_valid(fp):
            return vol, ts, fp
    raise ValueError("Bad UFID string \"%s\"" % ufid_str)
                              
