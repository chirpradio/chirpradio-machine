"""Text processing for album and track titles."""

import re


_NOT_OPEN_OR_CLOSE_TAG = r"[^\[\]]"
_NOT_CLOSE_TAG = r"[^\]]"

# After standardization, a valid title must match this regular
# expression.
_TEXT_RE = re.compile("".join((
            r"^",
            # The main part of the title
            _NOT_OPEN_OR_CLOSE_TAG, "+",
            # Zero or more tags, including leading whitespace
            r"(\s\[", _NOT_CLOSE_TAG, "+\])*",
            r"$")))

# A regular expression that matches the contents of a tag.
_TAG_RE = re.compile(r"\[(" + _NOT_CLOSE_TAG + "+)\]")


def standardize(text):
    """Put an album/track title into a standard form.

    Args:
      text: A unicode string containing the title.

    'text' is expected to be of the form
      Title String [Maybe a Tag] [Maybe Another Tag] ...
    
    Returns:
      A standardized version of 'text', or None if 'text' is malformed.
    """
    # No exotic or redundant whitespace allowed
    text = re.sub(r"\s+", " ", text)
    # Remove leading and trailing whitespace.
    text = text.strip()

    # Always use a double-quote as our "inch" marker.
    # \u201d = unicode double-quote
    # \u2019 = unicode single-quote
    text = text.replace(u"\u201d", '"')
    text = text.replace(u"\u2019\u2019", '"')
    text = text.replace(u"''", '"')
    # Always use the ASCII single-quote
    text = text.replace(u"\u2019", "'")
    
    # Remove leading and trailing whitespace inside of tags.
    text = re.sub(r"\[\s+", "[", text)
    text = re.sub(r"\s+\]", "]", text)
    # Exactly one space between tags.
    text = text.replace("][", "] [")
    # Exactly one space before any tag.
    text = re.sub(r"(\S)\[", r"\1 [", text)

    if not _TEXT_RE.match(text):
        return None
    return text


def append(text, to_append):
    """Appends text to a title string in a way that respects tags."""
    first_open = text.find("[")
    if first_open == -1:
        return text + to_append
    else:
        return "%s%s %s" % (text[:first_open].strip(),
                            to_append,
                            text[first_open:])


def split_tags(text):
    """Given a standardized title, split off the tags from the text.

    Returns (text, list of tags).
    """
    tags = _TAG_RE.findall(text)
    if tags:
        text = text[:text.find("[")].strip()
    return text, tags
