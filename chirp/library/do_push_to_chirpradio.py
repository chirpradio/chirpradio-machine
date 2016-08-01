"""
Pushes new music library data up into the cloud (i.e. the AppEngine
data store).  This causes the newly-added tracks to appear in the DJ
database and other chirpradio apps.

TODO(trow): Some of this is a bit hacky; it was put together quickly
to do the initial import.  It needs cleaning up before it can be put
into general use.
"""

import datetime
import re
import sys
import time
import urllib2

from chirp.common.printing import cprint
from chirp.common import timestamp
from chirp.common import conf
from chirp.library import album
from chirp.library import constants
from chirp.library import database
from chirp.library import order
from chirp.library import titles

from chirp.common import chirpradio
from google.appengine.ext import db
from djdb import models
from djdb import search


START_TIMESTAMP = 0
start_at_flag = "--start-at="
for arg in sys.argv:
    if arg.startswith(start_at_flag):
        arg = arg[len(start_at_flag):]
        START_TIMESTAMP = timestamp.parse_human_readable(arg)
        break

# TODO(trow): Is this optimal?
_NUM_ALBUMS_PER_FLUSH = 3

_DISC_NUM_RE = re.compile("disc\s+(\d+)", re.IGNORECASE)

_artist_cache = {}

DRY_RUN = False


class UnknownArtistError(Exception):
    pass


def get_artist_by_name(name):
    global _artist_cache
    if name in _artist_cache:
        return _artist_cache[name]
    while True:
        try:
            art = models.Artist.fetch_by_name(name)
            if art is None:
                raise UnknownArtistError("Unknown artist: %s" % name)
            _artist_cache[name] = art
            return art
        except urllib2.URLError:
            cprint("Retrying fetch_by_name for '%s'" % name)


def seen_album(album_id):
    while True:
        try:
            for alb in models.Album.all().filter("album_id =", album_id):
                if not alb.revoked:
                    return True
            return False
        except urllib2.URLError:
            cprint("Retrying fetch of album_id=%s" % album_id)


def process_one_album(idx, alb):
    # Build up an Album entity.
    kwargs = {}
    kwargs["parent"] = idx.transaction
    kwargs["title"] = alb.title()
    kwargs["album_id"] = alb.album_id
    kwargs["import_timestamp"] = datetime.datetime.utcfromtimestamp(
        alb.import_timestamp())
    kwargs["num_tracks"] = len(alb.all_au_files)
    kwargs["import_tags"] = alb.tags()

    if alb.is_compilation():
        kwargs["is_compilation"] = True
    else:
        kwargs["is_compilation"] = False
        kwargs["album_artist"] = get_artist_by_name(alb.artist_name())

    for key, val in sorted(kwargs.iteritems()):
        cprint("%s: %s" % (key, val))
    if seen_album(alb.album_id):
        cprint("   Skipping")
        return

    album = models.Album(**kwargs)

    # Look for a disc number in the tags.
    for tag in kwargs["import_tags"]:
        m = _DISC_NUM_RE.search(tag)
        if m:
            album.disc_number = int(m.group(1))
            break

    idx.add_album(album)

    for au_file in alb.all_au_files:
        track_title, import_tags = titles.split_tags(au_file.tit2())
        track_num, _ = order.decode(unicode(au_file.mutagen_id3["TRCK"]))
        kwargs = {}
        if alb.is_compilation():
            kwargs["track_artist"] = get_artist_by_name(au_file.tpe1())
        track = models.Track(
            parent=idx.transaction,
            ufid=au_file.ufid(),
            album=album,
            title=track_title,
            import_tags=import_tags,
            track_num=track_num,
            sampling_rate_hz=au_file.mp3_header.sampling_rate_hz,
            bit_rate_kbps=int(au_file.mp3_header.bit_rate_kbps),
            channels=au_file.mp3_header.channels_str,
            duration_ms=au_file.duration_ms,
            **kwargs)
        idx.add_track(track)


def flush(list_of_pending_albums):
    if not list_of_pending_albums:
        return
    if DRY_RUN:
        cprint("Dry run -- skipped flush")
        return
    idx = search.Indexer()
    for alb in list_of_pending_albums:
        process_one_album(idx, alb)
    # This runs as a batch job, so set a very long deadline.
    while True:
        try:
            rpc = db.create_rpc(deadline=120)
            idx.save(rpc=rpc)
            return
        except urllib2.URLError:
            cprint("Retrying indexer flush")


def maybe_flush(list_of_pending_albums):
    if len(list_of_pending_albums) < _NUM_ALBUMS_PER_FLUSH:
        return list_of_pending_albums
    flush(list_of_pending_albums)
    return []


def main():
    for _ in main_generator(START_TIMESTAMP):
        pass


def main_generator(start_timestamp):
    #chirpradio.connect("10.0.1.98:8000")
    chirpradio.connect()

    sql_db = database.Database(conf.LIBRARY_DB)
    pending_albums = []
    this_album = []
    # TODO(trow): Select the albums to import in a saner way.
    for vol, import_timestamp in sql_db.get_all_imports():
        if start_timestamp is not None and import_timestamp < start_timestamp:
            continue
        cprint("***")
        cprint("*** import_timestamp = %s" % timestamp.get_human_readable(
            import_timestamp))
        cprint("***")
        for au_file in sql_db.get_by_import(vol, import_timestamp):
            if this_album and this_album[0].album_id != au_file.album_id:
                alb = album.Album(this_album)
                pending_albums.append(alb)
                cprint('Adding "%s"' % alb.title())
                pending_albums = maybe_flush(pending_albums)
                this_album = []
            this_album.append(au_file)
            yield

    # Add the last album to the list of pending albums, then do the
    # final flush.
    if this_album:
        alb = album.Album(this_album)
        cprint('Adding "%s"' % alb.title())
        pending_albums.append(alb)
        this_album = []
    flush(pending_albums)


if __name__ == "__main__":
    main()
