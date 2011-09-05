"""Checks for any mp3 files in the library but missing from the catalog."""
import optparse
import os
import sqlite3

def main():
    p = optparse.OptionParser(
                    usage='%prog [options] /Library/vol1 catalog.sql')
    (options, args) = p.parse_args()
    if len(args) != 2:
        p.error('incorrect args')
    libdir, catfile = args
    conn = sqlite3.connect(catfile)
    cursor = conn.cursor()
    found = 0
    for root, dirs, files in os.walk(libdir):
        for fn in files:
            base, ext = os.path.splitext(fn)
            if ext == '.mp3':
                cursor.execute(
                    'select * from audio_files where fingerprint=?', [base])
                if not cursor.fetchone():
                    print ' * CATALOG MISSING %s' % base
                else:
                    found += 1
    print 'FOUND=%s' % found

if __name__ == '__main__':
    main()
