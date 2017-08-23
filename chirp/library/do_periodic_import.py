#!/usr/bin/env python

import logging
import os
import sys
from chirp.common import timestamp
from chirp.common.conf import (LIBRARY_PREFIX, LIBRARY_DB,
                                   LIBRARY_TMP_PREFIX)
from chirp.common.printing import cprint
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


def import_albums(dry_run):
    inbox = dropbox.Dropbox()
    prescan_timestamp = timestamp.now()
    error_count = 0
    album_count = 0
    seen_fp = {}

    db = database.Database(LIBRARY_DB)

    try:
        for alb in inbox.albums():
            alb.drop_payloads()
            album_count += 1
            cprint(u'#{num} "{title}"'.format(num=album_count, title=alb.title()))
            if alb.tags():
                cprint(u"(%s)" % ", ".join(alb.tags()))
            else:
                print
            duration_ms = sum(au.duration_ms for au in alb.all_au_files)
            if alb.is_compilation():
                cprint("Compilation")
                for i, au in enumerate(alb.all_au_files):
                    artist = au.mutagen_id3["TPE1"]
                    cprint(u"  {:02d}: {}".format(i+1, artist))
            else:
                cprint(alb.artist_name())
            cprint(u"{} tracks / {} minutes".format(
                len(alb.all_au_files), int(duration_ms / 60000)))
            cprint(u"ID=%015x" % alb.album_id)
            sys.stdout.flush()

            # Check that the album isn't already in library.
            collision = False
            for au in alb.all_au_files:
                if au.fingerprint in seen_fp:
                    cprint(u"***** ERROR: DUPLICATE TRACK WITHIN IMPORT", type='error')
                    cprint(u"This one is at %s" % au.path)
                    cprint(u"Other one is at %s" % seen_fp[au.fingerprint].path)
                    collision = True
                    break
                fp_au_file = db.get_by_fingerprint(au.fingerprint)
                if fp_au_file is not None:
                    cprint(u"***** ERROR: TRACK ALREADY IN LIBRARY", type='error')
                    cprint(fp_au_file.mutagen_id3)
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
                cprint("OK!\n")
            except (import_file.ImportFileError, album.AlbumError), ex:
                cprint("***** IMPORT ERROR")
                cprint("*****   %s\n" % str(ex))
                error_count += 1

            sys.stdout.flush()
            yield # scanned an album
    except analyzer.InvalidFileError as ex:
        cprint("***** INVALID FILE ERROR", type='error')
        cprint("*****   %s\n" % str(ex), type='error')
        error_count += 1

    cprint("-" * 40)
    cprint("Found %d albums" % album_count)
    if error_count > 0:
        cprint("Saw %d errors" % error_count, type='failure')
        return
    cprint("No errors found")

    if dry_run:
        cprint("Dry run --- terminating", type='success')
        return

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
        yield # import an album
    # Flush out any remaining tracks.
    if txn:
        txn.commit(LIBRARY_PREFIX)
    return


def main():
    dry_run = "--actually-do-import" not in sys.argv
    cprint()
    if dry_run:
        cprint("+++ This is only a dry run.  No actual import will occur.")
        cprint("+++ We will only scan the dropbox looking for errors.")
    else:
        cprint("*" * 70)
        cprint("***")
        cprint("*** WARNING!  This is a real import!")
        cprint("*** If no errors are found, the music library will be updated!")
        cprint("***")
        cprint("*" * 70)
    cprint()
    for _ in import_albums(dry_run):
        pass


if __name__ == "__main__":
    main()
