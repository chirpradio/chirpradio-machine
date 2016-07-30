#!/usr/bin/env python

import logging
import os
import sys
from chirp.common import timestamp
from chirp.common.conf import (LIBRARY_PREFIX, LIBRARY_DB,
                                   LIBRARY_TMP_PREFIX)
from chirp.library import album
from chirp.library import analyzer
from chirp.library import artists
from chirp.library import audio_file
from chirp.library import database
from chirp.library import dropbox
from chirp.library import import_file
from chirp.library import import_transaction


VOLUME_NUMBER = 1
IMPORT_SIZE_LIMIT = 0.95 * (3 << 30)  # 95% of 3GB.


dry_run = ("--actually-do-import" not in sys.argv)


def import_albums(inbox):
    prescan_timestamp = timestamp.now()
    error_count = 0
    album_count = 0
    seen_fp = {}

    db = database.Database(LIBRARY_DB)

    try:
        for alb in inbox.albums():
            alb.drop_payloads()
            album_count += 1
            print u'#%d "%s"' % (album_count, alb.title().encode("utf-8"))
            if alb.tags():
                print "(%s)" % ", ".join(alb.tags())
            else:
                print
            duration_ms = sum(au.duration_ms for au in alb.all_au_files)
            if alb.is_compilation():
                print "Compilation"
                for i, au in enumerate(alb.all_au_files):
                    artist = unicode(au.mutagen_id3["TPE1"]).encode("utf-8")
                    print "  %02d: %s" % (i+1, artist)
            else:
                print alb.artist_name().encode("utf-8")
            print "%d tracks / %d minutes" % (
                len(alb.all_au_files), int(duration_ms / 60000))
            print "ID=%015x" % alb.album_id
            sys.stdout.flush()

            # Check that the album isn't already in library.
            collision = False
            for au in alb.all_au_files:
                if au.fingerprint in seen_fp:
                    print "***** ERROR: DUPLICATE TRACK WITHIN IMPORT"
                    print "This one is at %s" % au.path
                    print "Other one is at %s" % seen_fp[au.fingerprint].path
                    collision = True
                    break
                fp_au_file = db.get_by_fingerprint(au.fingerprint)
                if fp_au_file is not None:
                    print "***** ERROR: TRACK ALREADY IN LIBRARY"
                    print unicode(fp_au_file.mutagen_id3).encode("utf-8")
                    collision = True
                    break
                seen_fp[au.fingerprint] = au

            if collision:
                sys.stdout.flush()
                error_count += 1

            # Attach a dummy volume # and timestamp
            alb.set_volume_and_import_timestamp(0xff, prescan_timestamp)
            try:
                alb.standardize()
                print "OK!\n"
            except (import_file.ImportFileError, album.AlbumError), ex:
                print "***** IMPORT ERROR"
                print "*****   %s\n" % str(ex)
                error_count += 1

            sys.stdout.flush()
    except analyzer.InvalidFileError, ex:
        print "***** INVALID FILE ERROR"
        print "*****   %s\n" % str(ex)
        error_count += 1

    print "-" * 40
    print "Found %d albums" % album_count
    if error_count > 0:
        print "Saw %d errors" % error_count
        return False
    print "No errors found"

    if dry_run:
        print "Dry run --- terminating"
        return True

    txn = None
    for alb in inbox.albums():
        if txn is None:
            txn = import_transaction.ImportTransaction(db, VOLUME_NUMBER,
                                                       timestamp.now(),
                                                       LIBRARY_TMP_PREFIX,
                                                       dry_run=dry_run)
        txn.add_album(alb)
        # If the transaction has grown too large, commit it.
        if txn.total_size_in_bytes > IMPORT_SIZE_LIMIT:
            txn.commit(LIBRARY_PREFIX)
            txn = None
    # Flush out any remaining tracks.
    if txn:
        txn.commit(LIBRARY_PREFIX)
    return True


def main():
    print
    if dry_run:
        print "+++ This is only a dry run.  No actual import will occur."
        print "+++ We will only scan the dropbox looking for errors."
    else:
        print "*" * 70
        print "***"
        print "*** WARNING!  This is a real import!"
        print "*** If no errors are found, the music library will be updated!"
        print "***"
        print "*" * 70
    print
    inbox = dropbox.Dropbox()
    import_albums(inbox)


if __name__ == "__main__":
    main()
