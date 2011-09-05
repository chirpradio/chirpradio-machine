
# The username for the music library.  The library is exported as a shared
# drive under this user's home directory.
USER = "music-library"


TFLT_WHITELIST = set((
        u"MPG/3",   # MPEG 1/2 layer III (i.e. MP3)
))


TOWN_FILE_OWNER = u"The Chicago Independent Radio Project"


UFID_OWNER_IDENTIFIER = u"http://chirpradio.org/_ufid/1"


# The CHIRP UFID tag has this hash key in Mutagen.
MUTAGEN_UFID_KEY = u"UFID:%s" % UFID_OWNER_IDENTIFIER


TXXX_ALBUM_ID_DESCRIPTION = u"CHIRP Album ID"
TXXX_ALBUM_ID_KEY = u"TXXX:%s" % TXXX_ALBUM_ID_DESCRIPTION


TXXX_FRAME_COUNT_DESCRIPTION = u"Frame Count"
TXXX_FRAME_COUNT_KEY = u"TXXX:%s" % TXXX_FRAME_COUNT_DESCRIPTION


TXXX_FRAME_SIZE_DESCRIPTION = u"Frame Size"
TXXX_FRAME_SIZE_KEY = u"TXXX:%s" % TXXX_FRAME_SIZE_DESCRIPTION


DEFAULT_ID3_TEXT_ENCODING = 3  # 3 == UTF-8


# Format to use when guest/featured artists are moved from TPE1 to TIT2.
TIT2_IMPORT_GUEST_FORMAT = " (w/ %(guest)s)"


# Any file containing one of these ID3 tags is automatically rejected!
ID3_TAG_BLACKLIST = set((
        # Terms of use frame: we do not want any files in the library that
        # have special terms.
        # TODO(trow): Uncomment this.
        # "USER",
        ))


# Tags in this list are allowed; all other non-blacklisted tags are stripped
# out and discarded.  For each Mutagen ID3 tag, the value of either its
# FrameID or HashKey attributes must appear in this list.
ID3_TAG_WHITELIST = set((
        "TALB",  # Album/Movie/Show title
        "TBPM",  # Beats per minute,
        "TCOM",  # Composer
        "TCON",  # Content type
        "TCOP",  # Copyright
        "TDLY",  # Playlist delay
        "TDOR",  # Original release time
        "TDRC",  # Recording time
        "TDRL",  # Release time
        "TDTG",  # Tagging time
        "TENC",  # Encoded by
        "TEXT",  # Lyricist/text writer
        "TFLT",  # File type
        "TIT1",  # Content group description
        "TIT2",  # Title/songname/content description
        "TIT3",  # Subtitle/Description refinement
        "TKEY",  # Initial key
        "TLAN",  # Language
        "TLEN",  # Length
        "TMED",  # Media type
        "TOAL",  # Original album/movie/show title
        "TOLY",  # Original lyricist(s)/text writer(s)
        "TOPE",  # Original artist(s)/performer(s)
        "TOWN",  # File owner
        "TPE1",  # Lead performer(s)/Soloist(s)
        "TPE2",  # Band/orchestra/accompaniment
        "TPE3",  # Conductor/performer refinement
        "TPE4",  # Interpreted, remixed, or otherwise modified by
        "TPOS",  # Part of a set
        "TPUB",  # Publisher
        "TRCK",  # Track number/position in set
        "TRSN",  # Internet radio station name
        "TRSO",  # Internet radio station owner
        "TSOA",  # Album sort order
        "TSOP",  # Performer sort order
        "TSOT",  # Title sort order
        "TSRC",  # ISRC (international standard recording code)
        "TSSE",  # Software/hardware and settings used when encoding

        "UFID",  # Unique file identifier

        TXXX_ALBUM_ID_KEY,  # Used to store the album's ID.
        TXXX_FRAME_COUNT_KEY,  # The number of MP3 frames in this file.
        TXXX_FRAME_SIZE_KEY,   # The size in bytes of all the MP3 frames.
))


# When new audio files are brought into the CHIRP library, these tags
# are stripped out (if present) and replaced.
ID3_TAG_STRIPPED_ON_IMPORT = set((
        "TFLT",  # File type
        "TLEN",  # Length
        "TOWN",  # File owner
))


# These tags must be present in every audio file in the CHIRP library.
ID3_TAG_REQUIRED = set((
        "TFLT",  # File type
        "TIT2",  # Title/songname/content description
        "TLEN",  # Length
        "TOWN",  # File owner
        "TPE1",  # Lead performer(s)/Soloist(s)
        "TRCK",  # Track number/position in set
        MUTAGEN_UFID_KEY,  # Unique file identifier for CHIRP
        TXXX_ALBUM_ID_KEY,  # Used to store the album's ID.
        TXXX_FRAME_COUNT_KEY,  # The number of MP3 frames in this file.
        TXXX_FRAME_SIZE_KEY,   # The size in bytes of all the MP3 frames.
))
