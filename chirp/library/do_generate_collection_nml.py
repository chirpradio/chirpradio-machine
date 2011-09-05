#!/usr/bin/env python

# Generate a collection.nml file from our library catalog.

import codecs
import sys
import time
from chirp.common import settings
from chirp.library import database
from chirp.library import nml_writer


def main():
    out_fh = codecs.open("output.nml", "w", "utf-8")
    # TODO(trow): Don't hard-wire the drive letter.
    writer = nml_writer.NMLWriter("T:", "/Library", out_fh)
    db = database.Database(settings.LIBRARY_DB)
    count = 0
    start_t = time.time()
    for au_file in db.get_all():
        writer.write(au_file)
        count += 1
        if count % 1000 == 0:
            elapsed_t = time.time() - start_t
            sys.stderr.write("%d (%.1f/s)...\n" % (count, count / elapsed_t))
    writer.close()
    out_fh.close()
    sys.stderr.write("Wrote %d tracks to collection\n" % count)


if __name__ == "__main__":
    main()
