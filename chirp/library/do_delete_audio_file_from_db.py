#!/usr/bin/env python
"""
Remove audio files and their M3U tags based on a fingerprints id given
Usage:

    See what will be deleted:
    do_delete_audio_file_from_db <fingerprint_id> <fingerprint_id>

    Actually delete:
    do_delete_audio_file_from_db <fingerprint_id> <fingerprint_id> --delete

Flags:
 --db = specify a filesystem path to an alternate location for the sqlite
        database file
 --delete = actually do the delete. Nothing will be deleted without this flag.

"""

import pprint
import sys
import sqlite3
import argparse
from chirp.common.conf import LIBRARY_DB
from chirp.library import database


class AudioFileManager(object):

    def __init__(self, library_db_file=None):
        if not library_db_file:
            library_db_file = LIBRARY_DB
        self.db_path = library_db_file
        self.db = database.Database(library_db_file)
        self.conn = self.db._get_connection()
        self.conn.row_factory = sqlite3.Row

    def _select_rows(self, cursor):
        while True:
            item = cursor.fetchone()
            if item is None:
                break
            yield item

    def print_rows(self, rows):
        for row in rows:
            pprint.pprint(list(row))

    def get_rows(self, fingerprints, table):
        sql = ("SELECT * "
               "FROM %s "
               "WHERE fingerprint IN (%s) "
               ) % (table, ",".join("?" * len(fingerprints)))
        cursor = self.conn.execute(sql, fingerprints)
        return self._select_rows(cursor)

    def get_tags(self, fingerprints):
        return self.get_rows(fingerprints, table="id3_tags")

    def get_audio_files(self, fingerprints):
        return self.get_rows(fingerprints, table="audio_files")

    def del_rows(self, fingerprints, table):
        sql = ("DELETE "
               "FROM %s "
               "WHERE fingerprint IN (%s) "
               ) % (table, ",".join("?" * len(fingerprints)))

        self.conn.execute(sql, fingerprints)

    def del_tags(self, fingerprints):
        self.del_rows(fingerprints, table="id3_tags")

    def del_audiofiles(self, fingerprints):
        try:
            self.del_tags(fingerprints)
            self.del_rows(fingerprints, table="audio_files")
        except Exception:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description='Delete records in audio file sqlite database.')
    parser.add_argument(
        'fingerprint', type=str, nargs='+',
        help=(
            'Audio file finterprint to delete. Can specify more '
            'than one, space delimited.  Must pass the --delete flag to '
            'confirm the delete.'))
    parser.add_argument(
        '--delete', action="store_true",
        help='Delete the audiofile based on the fingerprint passed in')
    parser.add_argument(
        '--db', action='store', type=str, default=None,
        help=(
            "Specify a full filesystem path to the database file "
            "to operate on."))

    args = parser.parse_args()

    afm = AudioFileManager(library_db_file=args.db)

    sys.stdout.write("ARGS: {} \n\n".format(str(args)))
    sys.stdout.write("Using database: {}\n".format(afm.db_path))

    fingerprints = args.fingerprint

    tags = afm.get_tags(fingerprints)

    audio_files = list(afm.get_audio_files(fingerprints))
    sys.stdout.write("\nROWS TO DELETE from audio_files\n\n")
    afm.print_rows(audio_files)

    sys.stdout.write("\nROWS TO DELETE from id3_tags\n\n")
    afm.print_rows(tags)

    if set(fingerprints) != set(f["fingerprint"] for f in audio_files):
        sys.stdout.write(
            "\n\nWARNING: A fingerprint was given that does not match "
            "an audio file in the database\n\n")

    if args.delete:
        afm.del_audiofiles(fingerprints)
        sys.stdout.write("\nDELETED\n")
    else:
        sys.stdout.write("\nNOTHING DELETED.  Pass in the --delete flag.\n")


if __name__ == "__main__":
    sys.exit(main())
