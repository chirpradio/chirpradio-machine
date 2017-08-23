#!/usr/bin/env python

# Generate a collection.nml file from our library catalog.

import codecs
import sys
import time
import os.path
import subprocess
from chirp.common.printing import cprint
from chirp.common import conf
from chirp.library import database
from chirp.library import nml_writer


def main():
    for _ in main_generator():
        pass


def main_generator():
    nml_file = os.path.join(os.getcwd(), 'output.nml')
    cprint(u'Writing Traktor file to {}'.format(nml_file))
    with codecs.open(nml_file, "w", "utf-8") as out_fh:
        # TODO(trow): Don't hard-wire the drive letter.
        writer = nml_writer.NMLWriter("T:", "/Library", out_fh)
        db = database.Database(conf.LIBRARY_DB)
        count = 0
        start_t = time.time()
        for au_file in db.get_all():
            writer.write(au_file)
            count += 1
            elapsed_t = time.time() - start_t
            cprint(type='count', count=count, elapsed_seconds=elapsed_t)
            if count % 1000 == 0:
                sys.stderr.write("{count} ({rate:.1f}/s)...\n".format(count=count, rate=count / elapsed_t))
            yield
        writer.close()

    # Move the file to where Traktor users expect to find it.
    cprint(u'Copying NML file to {}'.format(conf.TRAKTOR_NML_FILE))
    cmd = [
        'install',      # command that combines cp with chown, chmod, and strip
        '-m', '0775',
        '-g', 'traktor',
        nml_file,
        conf.TRAKTOR_NML_FILE]
    subprocess.check_call(cmd)

    cprint("Wrote %d tracks to collection\n" % count, type='success')


if __name__ == "__main__":
    main()
