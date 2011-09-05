
"""
Similarity metrics; useful when finding duplicate ID3 tags.
"""

import re
import unicodedata


def canonicalize_string(txt):
    """Generate a canonicalized version of a string.

    We canonicalize the string by:
      * Mapping it to lower case
      * Stripping off any leading or trailing "the"
      * Converting the word "and" to the symbol "&".
      * Stripping out all non-alphanumeric characters (except for "&"),
        including all whitespace.  If this leaves us with only the empty
        string, we instead strip out only whitespace.  This allows us
        to still distinguish all-punctuation strings like "!!!!".

    Args:
      txt: A string

    Returns:
      A unicode string containing a canonicalized version of txt.
    """
    # If necessary, convert txt to unicode.
    if not isinstance(txt, unicode):
        txt = unicode(txt)
    # Map txt to lower-case.
    txt = txt.lower()
    # Strip off any leading "the".
    if txt.startswith("the "):
        txt = txt[4:]
    if txt.endswith(" the"):
        txt = txt[:-4]
    # Replace the string "and" with "&".
    txt = txt.replace(" and ", "&")
    # Filter out all characters that are not unicode letters or
    # numbers (or "&", for which we make a special exception).
    chars = []
    for c in txt:
        c_cat = unicodedata.category(c)[0]
        if c == u"&" or c_cat == "L" or c_cat == "N":
            # This strips off any diacritics.
            c = unicodedata.normalize("NFD", c)[0]
            chars.append(c)
    # If there is nothing left, txt must consist entirely of punctuation
    # or something similiarly odd.  Try again, but with a weaker filter.
    if txt and not chars:
        chars = []
        for c in txt:
            c_cat = unicodedata.category(c)[0]
            # C = other, Z = separators
            if c_cat != "C" and c_cat != "Z":
                chars.append(c)
    return u''.join(chars)


def get_sort_key(text):
    """Returns a sort key for the string 'text'."""
    if text.lower().startswith(u"the "):
        text = text[4:]
    return text


def get_levenshtein_distance(string_1, string_2, max_value=None):
    """Return the Levenshtein distance between two strings.

    Note that the computation is relatively expensive: it is O(NM)
    for strings of length N and M.  The number of iterations can
    potentially be reduced by setting max_value.

    Args:
      string_1: A string
      string_2: Another string
      max_value: Sets an upper limit against which the return value
        is clamped.  

    Returns:
      The integral Levenshtein distance between the two strings, optionally
      clamped from above by max_value.

    For more information, see the Wikipedia page:
      http://en.wikipedia.org/wiki/Levenshtein_distance
    (This implementation is based on pseudocode found there.)
    """
    # Make sure that string_1 is the shorter of the two strings.
    if len(string_1) > len(string_2):
        string_1, string_2 = string_2, string_1

    # If no max_value is specified, use the length of the longer of
    # the two strings (which is the largest possible value).
    if max_value is None:
        max_value = max(len(string_1), len(string_2))

    # Handle the special case of the empty string.
    if not string_1:
        return min(len(string_2), max_value)

    # If a max_value is set and the difference between the length of
    # the strings is too big, bail out immediately.
    if max_value and max_value < abs(len(string_1) - len(string_2)):
        return max_value

    prev_distance_vec = range(1, 1+len(string_2))
    for i, c_i in enumerate(string_1):
        new_distance_vec = []
        for j, c_j in enumerate(string_2):
            # cost is 0 if c_i == c_j, 1 otherwise.
            cost = abs(cmp(c_i, c_j))
            delete_dist = prev_distance_vec[j] + 1
            if j == 0:
                insert_dist  = i + 2
                substitution_dist = i + cost
            else:
                insert_dist = new_distance_vec[j-1] + 1
                substitution_dist = prev_distance_vec[j-1] + cost
            new_distance_vec.append(min(delete_dist,
                                        insert_dist,
                                        substitution_dist))
        prev_distance_vec = new_distance_vec
        # Look at the diagonal of the matrix to place a lower bound on
        # the edit distance.  If that lower bound is greater than or
        # equal to the max allowed value, return immediately.
        dist_lower_bound = new_distance_vec[len(string_2)-len(string_1)+i]
        if dist_lower_bound >= max_value:
            return max_value

    # Pull the answer off of the end of the last distance vector.
    return prev_distance_vec[-1]


def get_common_prefix(string_1, string_2):
    """Find the largest common prefix of two strings.
    
    Args:
      string_1: A string.
      string_2: Another string.

    Returns:
      The longest common prefix of string_1 and string_2.
    """
    # If either string_1 or string_2 is the empty string, the common
    # prefix must be the empty string.
    if not (string_1 and string_2):
        return ""
    min_len = min(len(string_1), len(string_2))
    for i in xrange(min_len):
        if string_1[i] != string_2[i]:
            return string_1[:i]
    return string_1[:min_len]
            
                          
                          
    
    
