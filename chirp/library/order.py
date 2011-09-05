"""Processing for track and disk order-numbering.

This code parses and verifies track and disk order-numbering, i.e. the
text of the form "nn/mm" stored in TRCK and TPOS tags.
"""

import re
import mutagen.id3

# A regular expression used to parse order-number descriptions.
_NUMBERING_RE = re.compile(r"^\s*(-?\d+)([^\d\-]+(-?\d+))?\s*$", re.UNICODE)


_ARCHIVAL_RE = re.compile(r"^\d+/\d+$", re.UNICODE)


class BadOrderError(Exception):
    """Raised when an order-numbering string is malformed."""


def decode(text):
    """Decode an order-numbering string.

    Args:
      text: A string containing track or disk order-numbering.

    Returns:
      A 2-tuple containing:
        * The item's order-number.
        * The total number of items in the collection, or None if the total
          number is not known.
    
    Raises:
      BadOrderError: if text is malformed or obviously invalid.
    """
    match = _NUMBERING_RE.search(text)
    if match:
        order_num = int(match.group(1))
        if order_num > 0:
            total_num_str = match.group(3)
            if total_num_str is None:
                return order_num, None
            else:
                total_num = int(total_num_str)
                if order_num <= total_num:
                    return order_num, total_num
    raise BadOrderError("Bad numbering \"%s\"" % text)


def encode(order_num, total_num):
    """Encode order-numbering information using our preferred format.

    Args:
      order_num: The item's order-number.
      total_num: The total number of items, or None if not known.
    
    Returns:
      A string suitable for use in a TPOS or TRCK tag.

    Raises:
      BadOrderError: if any of the arguments are obviously bad.
    """
    if order_num <= 0:
        raise BadOrderError("Bad order-number \"%d\"" % order_num)
    if total_num is not None:
        if order_num > total_num:
            raise BadOrderError("Bad order-number \"%d/%d\""
                                % (order_num, total_num))
        
        return u"%d/%d" % (order_num, total_num)
    return u"%d" % order_num


def standardize_str(text):
    """Convert an order-numbering string to our standard form."""
    order_num, max_num = decode(text)
    return encode(order_num, max_num)


def _is_order_tag(tag):
    if not isinstance(tag, mutagen.id3.NumericPartTextFrame):
        return False
    if len(tag.text) != 1:
        raise BadOrderError("Tag %r has %d text parts" % (tag, len(tag.text)))
    return True


def standardize(tag):
    """Put an order-numbering ID3 tag into our standard form.

    This function does nothing when applied to a non-order-numbering tag.

    Args:
      tag: A mutagen ID3 tag, which is modified in-place.

    Returns:
      A 2-tuple with the decoded version of the order string.

    raises:
      BadOrderError: if the tag is obviously bad.
    """
    if not _is_order_tag(tag):
        return
    tag.text[0] = standardize_str(tag.text[0])
    return decode(tag.text[0])


def is_archival(text):
    """Returns True if text is in our preferred archival form."""
    if not _ARCHIVAL_RE.match(text):
        return False
    try:
        order_num, total_num = decode(text)
        return total_num is not None
    except BadOrderError:
        return False


def verify_and_standardize_str_list(text_list):
    """Verify a list of order strings and convert them to the standard form.

    Args:
      text_list: A list of strings containing order-numbering.

    Returns:
      The list of strings converted into our standard order-numbering
      format ("nn/mm").

    Raises:
      BadOrderError: if any of the strings are invalid, or if there are
        gaps in the sequence or other problems.
    """
    if not text_list:
        raise BadOrderError("Passed an empty list.")
    new_text_list = []
    expected_total_num = len(text_list)
    seen_order_nums = set()

    for text in text_list:
        order_num, total_num = decode(text)
        if order_num in seen_order_nums:
            raise BadOrderError("Duplicate order-number: \"%s\"" % text)
        seen_order_nums.add(order_num)
        if total_num is None:
            total_num = expected_total_num
        elif total_num != expected_total_num:
            raise BadOrderError(
                "Bad total number in list: \"%s\"" % text)
        if order_num > total_num:
            raise BadOrderError("Bad order-number: \"%s\"" % text)
        new_text_list.append(encode(order_num, total_num))

    missing_order_nums = set(xrange(1, expected_total_num+1)) - seen_order_nums
    if missing_order_nums:
        raise BadOrderError("Missing order-numbers: %s"
                            % sorted(missing_order_nums))
    return new_text_list


def verify_and_standardize(tag_list):
    """Verify a list of ID3 order tags and convert them to the standard form.

    Args:
      tag_list: A list of mutagen ID3 order-numbering tags.  These 
        tags are modified in-place.

    Raises:
      BadOrderError: if any of the tags are invalid, or if there are
        gaps in the sequence or other problems.
    """
    for tag in tag_list:
        if not _is_order_tag(tag):
            raise BadOrderError("Non-order tag %r" % tag)
    text_list = [tag.text[0] for tag in tag_list]
    new_text_list = verify_and_standardize_str_list(text_list)
    for i, text_str in enumerate(new_text_list):
        tag_list[i].text[0] = text_str
