"""
Code to convert the names of artists into a standardized form.

Note that this module's _init() function is called on import.
"""

import codecs
import os
import re
import sys
import threading

from chirp.common import ROOT_DIR
from chirp.library import similarity


# The directory containing the library data.
_LIBRARY_DATA_PREFIX = os.path.join(ROOT_DIR, "library", "data")

# The file containing the official artist list.
_WHITELIST_FILE = os.path.join(_LIBRARY_DATA_PREFIX, "artist-whitelist")
 
# The file containing mappings from alternative forms of an artist name
# to the official form.
_MAPPINGS_FILE = os.path.join(_LIBRARY_DATA_PREFIX, "artist-mappings")

# The separator used between the key/value pairs in a file of mappings.
# Unicode char \xbb is the double-greater-than sign.
_MAPPINGS_SEP = u"\xbb\xbb\xbb"

# A dict containing the data parsed from _WHITELIST_FILE.
# This is populated at module import-time by calling _init().
_global_whitelist  = {}

# A pair of dicts containing the data parsed from _MAPPINGS_FILE.
# These are populated at module import-time by calling _init().
_global_raw_mappings = {}
_global_mappings = {}

# A global lock that guards the global whitelist and mappings.
_global_lock = threading.Lock()


def all():
    """Returns an iterable sequence of all known artists."""
    _global_lock.acquire()
    try:
        return _global_whitelist.values()
    finally:
        _global_lock.release()


def sort_key(artist_name):
    return similarity.get_sort_key(artist_name.lower())


def _standardize_simple(artist_name, whitelist, mappings):
    """Attempt to standardize an artist name using only "simple" methods.

    Args:
      artist_name: A unicode string containing an artist's name
      whitelist: A whitelist dict that maps canonicalized names
        to names
      mappings: A mappings dict whose keys and values are both
        canonicalized artist names

    Returns:
      A string containing the standardized form of the artist name,
      or None if the name is not recognized.
    """
    canon_name = similarity.canonicalize_string(artist_name)
    # We just try to look up the canonicalized form of the artist name
    # in both the whitelist and mapping dicts.
    if canon_name in whitelist:
        return whitelist[canon_name]
    elif canon_name in mappings:
        return whitelist.get(mappings[canon_name])
    else:
        return None


def _standardize(artist_name, whitelist, mappings):
    """Attempt to standardize an artist name.

    Args:
      artist_name: A unicode string containing an artist's name
      whitelist: A whitelist dict that maps canonicalized names
        to names
      mappings: A mappings dict whose keys and values are both
        canonicalized artist names

    Returns:
      A string containing the standardized form of the artist name,
      or None if the name is not recognized.
    """
    artist_name = artist_name.strip()
    # First just try standardization based on the whitelist and mappings.
    # If that works, return the standardized string.
    std = _standardize_simple(artist_name, whitelist, mappings)
    if std: return std
    # Since that didn't work, we now try to find a corresponding item
    # in the whitelist by shuffling the order of the words.
    artist_name_split = artist_name.split()
    # Try moving the last word first.
    # This handles a case like "John Lee Hooker" -> "Hooker, John Lee"
    if len(artist_name_split) > 1:
        parts = [artist_name_split[-1]] + artist_name_split[:-1]
        std = _standardize_simple(" ".join(parts), whitelist, mappings)
        if std: return std
    # Try swapping the first two words.
    # This handles cases like "Cave, Nick & the Bad Seeds" ->
    # "Nick Cave & the Bad Seeds"
    if len(artist_name_split) > 2:
        parts = ([artist_name_split[1], artist_name_split[0]]
                 + artist_name_split[2:])
        std = _standardize_simple(" ".join(parts), whitelist, mappings)
        if std: return std
    # Nothing worked, so we just return None.
    return None


def standardize(artist_name):
    """Attempt to standardize an artist name using the official artist list.

    Args:
      artist_name: A unicode string containing an artist's name
      
    Returns:
      A string containing the standardized form of the artist name
      according to the official artist list stored in chirp/library/data,
      or None if the name is not recognized.
    """
    if artist_name is None:
        return None
    global _global_whitelist
    global _global_mappings
    _global_lock.acquire()
    try:
        return _standardize(artist_name, _global_whitelist, _global_mappings)
    finally:
        _global_lock.release()


def is_standardized(artist_name):
    """Returns True if artist_name is exactly equal to its standardization."""
    return standardize(artist_name) == artist_name


_BASE_SPLIT_PATTERN = (
    r"\s*((feat\.?)|(ft\.)|(featuring)|(with)|(w/)|(and)|(&))"
    r"\s+(?P<feat>.*)")

_SPLIT_RES = [
    re.compile(r"%s%s%s" % (a, _BASE_SPLIT_PATTERN, b), re.IGNORECASE)
    for a, b in ((r"\(", r"\)"), (r"\[", r"\]"), ("", ""))]


def split(artist_name):
    """Split an artist name into primary and secondary parts.

    The purpose of this function is to extract guest artists and other
    collaborators from an artist name.  For example, in the string
    "Madvillain feat. Lord Quas", we'd say that "Madvillain" is the primary
    part and "Lord Quas" is the secondary part.  In this case the tuple
    ("Madvillain", "Lord Quas") would be returned.

    This function does not take the artist whitelist into account, and thus
    might make the wrong guess in some cases.  For complete accuracy,
    use split_and_standardize() instead.

    Args:
      artist_name: A unicode string containing an artist's name

    Returns:
      A 2-tuple containing the primary and secondary parts.  Each is a
      best guess, and the primary is not guaranteed to be standardized or
      to appear in the whitelist.  None is returned if there cannot
      possibly be a secondary part.
"""
    for pattern in _SPLIT_RES:
        match = pattern.search(artist_name)
        if match:
            this_pos = match.start()
            return (artist_name[:this_pos].strip(),
                    match.group('feat').strip())
    return artist_name, None


def split_and_standardize(artist_name):
    """Split an artist name into standardized primary and secondary parts.

    The purpose of this function is to extract guest artists and other
    collaborators from an artist name.  For example, in the string
    "Madvillain feat. Lord Quas", we'd say that "Madvillain" is the primary
    part and "Lord Quas" is the secondary part.  In this case the tuple
    ("Madvillain", "Lord Quas") would be returned.

    Args:
      artist_name: A unicode string containing an artist's name

    Returns:
      A 2-tuple containing the primary and secondary parts.  The primary
      part is a standardized artist name.  The secondary part is not
      standardized, and may be any nonempty string.  None is returned for
      the secondary if there is no secondary part.
    """

    # If the full name of the artist is on our whitelist, there is
    # nothing else to do.
    std = standardize(artist_name)
    if std is not None:
        return std, None

    # Holds the solution with the longest head part.
    best_head, best_tail = None, None

    for pattern in _SPLIT_RES:
        pos = 0
        while pos >= 0:
            match = pattern.search(artist_name, pos)
            if not match:
                break
            this_pos = match.start()
            head = standardize(artist_name[:this_pos])
            if (head is not None
                and (best_head is None or len(head) > len(best_head))):
                best_head = head
                best_tail = match.group('feat').strip()
            pos = this_pos + 1

    return best_head, best_tail


def suggest(name):
    canon_name = similarity.canonicalize_string(name)
    _global_lock.acquire()
    try:
        canon_whitelist = list(_global_whitelist)
    finally:
        _global_lock.release()
    best_guess = None
    # We ignore any items that are more than 10 edits away from our
    # original name.
    MAX_DIST = 10
    MAX_NORM_DIST = 0.25
    best_dist = 1e+100
    for guess in canon_whitelist:
        normalizer = (len(guess)+len(canon_name)/2.0)
        max_value = min(MAX_DIST, int(1+normalizer*MAX_NORM_DIST))
        lev_dist = similarity.get_levenshtein_distance(
            canon_name, guess, max_value=max_value)
        if lev_dist < MAX_DIST:
            normalized_lev_dist = lev_dist / normalizer
            if normalized_lev_dist < MAX_NORM_DIST:
                best_guess = guess
                best_dist = normalized_lev_dist
    return _global_whitelist.get(best_guess)


def _seq_to_whitelist(seq_of_names):
    new_whitelist = {}
    for name in seq_of_names:
        canon = similarity.canonicalize_string(name)
        if canon in new_whitelist:
            sys.stderr.write("Artist whitelist collision: \"%s\" and \"%s\"\n"
                             % (new_whitelist[canon], name))
            return None
        new_whitelist[canon] = name
    return new_whitelist


def reset_artist_whitelist(seq_of_names):
    """Replaces the current in-memory cache of whitelisted artists.

    Args:
      seq_of_names: An iterable sequence of standardized unicode artist names.

    Returns:
      True if the passed-in sequence of names is valid.  If the list is
      invalid, False is returned and no update is performed.
    """
    new_whitelist = _seq_to_whitelist(seq_of_names)
    if new_whitelist is None:
        return False
    _global_lock.acquire()
    try:
        global _global_whitelist
        _global_whitelist = new_whitelist
        return True
    finally:
        _global_lock.release()
            

###
### The below is code related to initializing the artist whitelist.
###

def _read_artist_whitelist_from_file(file_obj):
    """Read the artist whitelist from a file.

    Args:
      file_obj: A file object to read the whitelist from

    Returns a set of whitelisted artist names.
    """
    whitelist = set()
    for line in file_obj:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        whitelist.add(line)
    return whitelist


def _read_artist_mappings_from_file(file_obj):
    """Read the artist mappings from a file.

    Args:
      file_obj: A file object to read the mappings from

    Returns:
      A 2-tuple containing
        * A mapping dict, which carries canonicalized strings to
          canonicalized strings
        * A "raw mapping dict, which gives the mapping exactly as
          described in the file, without any canonicalization.
    """
    raw_mappings = {}
    mappings = {}
    for line in file_obj:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        before, sep, after = line.partition(_MAPPINGS_SEP)
        if not sep:
            sys.stderr.write("Skipping invalid mapping: \"%s\"\n"
                             % line.encode("utf-8"))
            continue
        before = before.strip()
        after = after.strip()
        raw_mappings[before] = after

        canon_before = similarity.canonicalize_string(before)
        canon_after = similarity.canonicalize_string(after)
        mappings[canon_before] = canon_after

    return mappings, raw_mappings


def _init():
    """Bootstrap the global whitelist and mappings."""
    # Read in the artist whitelist.
    global _global_whitelist
    assert reset_artist_whitelist(_read_artist_whitelist_from_file(
            codecs.open(_WHITELIST_FILE, "r", "utf-8")))

    # Read in the artist name mappings.
    global _global_raw_mappings
    global _global_mappings
    _global_mappings, _global_raw_mappings = _read_artist_mappings_from_file(
        codecs.open(_MAPPINGS_FILE, "r", "utf-8"))


# Note that the data in mappings in considered to be definitive, and
# clobbers data currently in the whitelist.
def merge_whitelist_and_mappings(whitelist, raw_mappings):
    """Combine information from whitelist and mappings.

    Args:
      whitelist: A whitelist dict
      raw_mappings: A raw mappings dict
      
    Returns:
      A (whitelist, raw_mapping) pair that is equivalent to the args
      but with certain normalizations applied that take information
      from the mappings and applies it back to the whitelist, thereby
      correcting any inconsistencies.
    """
    new_whitelist = dict(whitelist)
    inv_whitelist = dict((v, k) for k, v in whitelist.iteritems())
    new_raw_mappings = {}
    for before, after in raw_mappings.iteritems():
        std_before = _standardize(before, whitelist, {})
        std_after = _standardize(after, whitelist, {})
        # Every "after" should exactly match a whitelist item.
        if after != std_after:
            if std_after is not None:
                # Delete the whitelist entry that created the non-matching
                # standardization of after.
                try:
                    del new_whitelist[inv_whitelist[std_after]]
                except KeyError:
                    pass
            # A "before" item in the mappings should never exactly match
            # an existing whitelist entry.  If it does, delete it from
            # the whitelist.
            canon_before = similarity.canonicalize_string(before)
            if canon_before in new_whitelist:
                del new_whitelist[canon_before]
            # Insert the "after" form into the new whitelist.
            canon_after = similarity.canonicalize_string(after)
            new_whitelist[canon_after] = after
        # If we can figure out a mapping based solely on the whitelist,
        # the mapping can be dropped.
        if std_before and std_before == std_after:
            continue
        new_raw_mappings[before] = after

    # If the whitelist and mappings remained stable under these operations,
    # return them.
    if new_whitelist == whitelist and new_raw_mappings == raw_mappings:
        return new_whitelist, new_raw_mappings
    # If something did change, call self recursively on the results.
    return merge_whitelist_and_mappings(new_whitelist, new_raw_mappings)


#######################
# INITIALIZATION CODE #
#######################

_init()
