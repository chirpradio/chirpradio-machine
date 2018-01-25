#!/usr/bin/env python
"""
Remvoe audio files and their M3U tags based on a fingerprints id given
Usage:

    See what will be deleted:
    ./do_delete_auto_file_from_db.py <fingerprint_id> <fingerprint_id>

    Actually delete:
    ./do_delete_auto_file_from_db.py <fingerprint_id> <fingerprint_id> --delete

"""

import sys
import csv
import sqlite3
import argparse
from chirp.common.conf import LIBRARY_DB
from chirp.library import database


class AudioFileManager(object):

    def __init__(self, library_db_file=None):
        if not library_db_file:
            library_db_file = LIBRARY_DB
        self.db = database.Database(LIBRARY_DB)
        self.conn = self.db._get_connection()
        self.conn.row_factory = sqlite3.Row

    def _select_rows(self, cursor):
        while True:
            item = cursor.fetchone()
            if item is None:
                break
            yield item

    def print_rows(self, rows):
        w = csv.writer(sys.stdout, delimiter=',')
        for row in rows:
            w.writerow(row)

    def get_audiofiles(self, fingerprints):
        audio_files = []
        for fingerprint in fingerprints:
            af = self.db.get_by_fingerprint(fingerprint)
            if not af:
                raise Exception('Fingerprint %s has no record in the db.' % fingerprint)
            audio_files.append(af)
        return audio_files

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
        self.conn.commit()

    def del_tags(self, fingerprints):
        self.del_rows(fingerprints, table="id3_tags")

    def del_audiofiles(self, fingerprints):

        try:
            self.del_tags(fingerprints)
        except:
            raise
        else:
            self.del_rows(fingerprints, table="audio_files")


def main():
    parser = argparse.ArgumentParser(
        description='Manage records in audio file sqlite database.')
    parser.add_argument(
        'fingerprint', type=str, nargs='+',
        help='an integer for the accumulator')
    parser.add_argument(
        '--delete', action="store_true",
        help='Delete the audiofile based on the fingerprint passed in')
    args = parser.parse_args()

    afm = AudioFileManager()

    sys.stdout.write("ARGS: {} \n\n".format(str(args)))
    fingerprints = args.fingerprint
    try:
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
    except Exception as e:
        raise
        sys.stderr.write("ERROR: {}\n".format(str(e)))


if __name__ == "__main__":
    sys.exit(main())
