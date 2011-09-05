# -*- coding: utf-8 -*-

import unicodedata

_CHARACTER_NORMALIZATIONS = {
    u"Ø": "O",
    u"ø": "o",
}

def simplify(text):
    """Simplify text by replacing diacritics.

    Args:
      text: A string

    Returns:
      A verison of 'text' where the diacritics are replaced by
      7-bit ASCII characters.
    """
    simplified_chars = []
    for c in unicode(text):
        if unicodedata.category(c)[0] in ("L", "N"):
            c = unicodedata.normalize("NFD", c)[0]
            c = _CHARACTER_NORMALIZATIONS.get(c, c)
        simplified_chars.append(c)
    simplified = u"".join(simplified_chars)
    return simplified
