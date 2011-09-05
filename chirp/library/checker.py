"""
Checker; ensure that an AudioFile is valid and conforms to our tagging style.
"""

from chirp.library import analyzer
from chirp.library import artists
from chirp.library import constants
from chirp.library import order
from chirp.library import ufid


# These are the human-readable strings returned by a call to find_tags_errors.

ERROR_TAG_MISSING_REQUIRED = "Missing required tag: "
ERROR_TAG_NOT_WHITELISTED = "Non-whitelisted tag: "
ERROR_TAG_WRONG_ENCODING = "Tag has incorrect encoding: "

ERROR_NUMERIC_MALFORMED = "Malformed numeric tag: "

ERROR_TFLT_NON_WHITELISTED = "TFLT tag holds non-whitelisted value"

ERROR_TLEN_INCORRECT = "TLEN tag contains incorrect file duration"

ERROR_TXXX_FRAME_COUNT_INCORRECT = "TXXX tag contains incorrect frame count"
ERROR_TXXX_FRAME_SIZE_INCORRECT = "TXXX tag contains incorrect frame size"

ERROR_TOWN_INCORRECT = "TOWN tag holds incorrect value"

ERROR_TPE_NONSTANDARD = "TPE tag has non-standard artist: "

ERROR_ORDER_MALFORMED = "Tag contains a bad order string: "

ERROR_UFID_BAD_OWNER = "Invalid UFID owner identifier"
ERROR_UFID_BAD_MALFORMED = "Malformed UFID tag"
ERROR_UFID_BAD_VOLUME = "Incorrect volume number in UFID"
ERROR_UFID_BAD_TIMESTAMP = "Incorrect timestamp in UFID"
ERROR_UFID_BAD_FINGERPRINT = "Incorrect fingerprint in UFID"


def find_tags_errors(au_file):
    """Return a list of errors found in a file's ID3 tags.

    Args:
      au_file: An AudioFile object.

    Returns:
      A list of human-readable strings describing errors or
      inconsistencies found in the AudioFile object's ID3 tags,
      or the empty list if no errors are found.
    """
    errors = []

    # Make sure all required tags are there.
    for tag in constants.ID3_TAG_REQUIRED:
        if tag not in au_file.mutagen_id3:
            errors.append(ERROR_TAG_MISSING_REQUIRED + tag)

    # Checks that are not really tag-specific.
    for tag in au_file.mutagen_id3.itervalues():
        # Make sure all tags are on the whitelist.
        if (tag.FrameID not in constants.ID3_TAG_WHITELIST
            and tag.HashKey not in constants.ID3_TAG_WHITELIST):
            errors.append(ERROR_TAG_NOT_WHITELISTED + tag.FrameID)
        # Make sure all text tags have the correct encoding.
        if tag.FrameID.startswith("T"):
            encoding = getattr(tag, "encoding", "missing")
            if (encoding != "missing"
                and encoding != constants.DEFAULT_ID3_TEXT_ENCODING):
                errors.append(ERROR_TAG_WRONG_ENCODING + tag.FrameID)

    # Check that numeric tags are actually numeric.
    for frame_id in ("TBPM", "TLEN", "TORY", "TYER"):
        tag = au_file.mutagen_id3.get(frame_id)
        if tag and not (len(tag.text) == 1 and tag.text[0].isdigit()):
            errors.append(ERROR_NUMERIC_MALFORMED + frame_id)

    # Check that TFLT contains a whitelisted file type.
    this_tflt = au_file.mutagen_id3.get("TFLT")
    if (this_tflt
        and not (len(this_tflt.text) == 1
                 and this_tflt.text[0] in constants.TFLT_WHITELIST)):
        errors.append(ERROR_TFLT_NON_WHITELISTED)

    # Check that TLEN contains the correct length.
    this_tlen = au_file.mutagen_id3.get("TLEN")
    if (this_tlen
        and not (len(this_tlen.text) == 1
                 and str(au_file.duration_ms) == this_tlen.text[0])):
        errors.append(ERROR_TLEN_INCORRECT)

    # Check that the TXXX with the frame count is correct.
    this_fc = au_file.mutagen_id3.get(constants.TXXX_FRAME_COUNT_KEY)
    if (this_fc
        and not (len(this_fc.text) == 1
                 and str(au_file.frame_count) == this_fc.text[0])):
        errors.append(ERROR_TXXX_FRAME_COUNT_INCORRECT)

    # Check that the TXXX with the frame size is correct.
    this_fs = au_file.mutagen_id3.get(constants.TXXX_FRAME_SIZE_KEY)
    if (this_fs
        and not (len(this_fs.text) == 1
                 and str(au_file.frame_size) == this_fs.text[0])):
        errors.append(ERROR_TXXX_FRAME_SIZE_INCORRECT)

    # Check that TOWN contains the expected string.
    this_town = au_file.mutagen_id3.get("TOWN")
    if (this_town
        and not (len(this_town.text) == 1
                 and this_town.text[0] == constants.TOWN_FILE_OWNER)):
        errors.append(ERROR_TOWN_INCORRECT)

    # Check that the TPE tags contain known artists.
    for tag in au_file.mutagen_id3.itervalues():
        if tag.FrameID.startswith("TPE"):
            for txt in tag.text:
                if not artists.is_standardized(txt):
                    errors.append(ERROR_TPE_NONSTANDARD + txt)

    # Check that TRCK and TPOS contains a valid order-numbering in our
    # standard form.
    for this_tag in (au_file.mutagen_id3.get("TPOS"),
                     au_file.mutagen_id3.get("TRCK")):
        if this_tag and not (len(this_tag.text) == 1
                             and order.is_archival(this_tag.text[0])):
            errors.append("%s%s %s" % (ERROR_ORDER_MALFORMED,
                                       this_tag.FrameID,
                                       this_tag.text))

    # Check the UFID.
    this_ufid = au_file.mutagen_id3.get(constants.MUTAGEN_UFID_KEY)
    if this_ufid:
        try:
            vol, ts, fp = ufid.parse(this_ufid.data)
            if au_file.volume != vol:
                errors.append(ERROR_UFID_BAD_VOLUME)
            if au_file.import_timestamp != ts:
                errors.append(ERROR_UFID_BAD_TIMESTAMP)
            if au_file.fingerprint != fp:
                errors.append(ERROR_UFID_BAD_FINGERPRINT)
        except ValueError, ex:
            errors.append(ERROR_UFID_BAD_MALFORMED)

    # We made it!  Return the list of errors.
    return errors
    
    

    
