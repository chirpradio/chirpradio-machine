"""Code for dealing with Mutagen text tags (i.e. tags named T???)."""

import re
import mutagen.id3

from chirp.library import constants

# A regular expression used to clean up adjacent whitespace.
_TWO_OR_MORE_SPACES_RE = re.compile(r"\s{2,}", re.UNICODE)


def is_vanilla_text(tag):
    """Returns true if tag is a text frame with a writable 'text' attribute."""
    return (isinstance(tag, mutagen.id3.TextFrame)
            and not (isinstance(tag, mutagen.id3.TimeStampTextFrame)
                     or isinstance(tag, mutagen.id3.NumericTextFrame)))


def standardize(tag):
    """Fix a text tag's encoding and whitespace.

    This function does nothing when applied to non-text tags.

    Args:
      tag: A mutagen ID3 tag.  This tag is modified in-place.
    """
    # Make sure the tag uses our standard encoding.
    if isinstance(tag, mutagen.id3.TextFrame):
        tag.encoding = constants.DEFAULT_ID3_TEXT_ENCODING
    # If this is not a text tag, stop here.
    if not is_vanilla_text(tag):
        return
    # Fix up the whitespace, stripping out empties.
    new_text = []
    for text_str in tag.text:
        text_str = _TWO_OR_MORE_SPACES_RE.sub(u" ", text_str.strip())
        if text_str:
            new_text.append(text_str)
    tag.text = new_text
        
