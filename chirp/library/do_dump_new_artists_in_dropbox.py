#!/usr/bin/env python

import codecs
import sys
from chirp.library import artists
from chirp.library import dropbox


def main():
    rewrite = ("--rewrite" in sys.argv)

    drop = dropbox.Dropbox()
    new_artists = set()
    for au_file in drop.tracks():
        try:
            tpe1 = au_file.mutagen_id3["TPE1"].text[0]
        except:
            print '** file: %r' % au_file.path
            raise
        if artists.standardize(tpe1) is None:
            new_artists.add(tpe1)

    to_print = list(new_artists)
    if rewrite:
        to_print.extend(artists.all())
    to_print.sort(key=artists.sort_key)
    
    output = None
    if rewrite:
        output = codecs.open(artists._WHITELIST_FILE, "w", "utf-8")
    for tpe1 in to_print:
        if output:
            output.write(tpe1)
            output.write("\n")
        else:
            print tpe1.encode("utf-8")
    if rewrite:
        print "Artist whitelist updated"


if __name__ == "__main__":
    main()
