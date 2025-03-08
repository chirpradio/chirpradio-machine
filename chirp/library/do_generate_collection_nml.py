#!/usr/bin/env python

# Generate a collection.nml file from our library catalog.

import codecs
import sys
import time
import os.path
import subprocess
import argparse
from chirp.common.printing import cprint
from chirp.common import conf
from chirp.library import database
from chirp.library import nml_writer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--safe', action='store_true',
        help=("Write to NML file in a way that is slower, but uses less memory "
              "and doens't depend on the previous file structure. Recommended "
              "only if the default run mode is causing you errors.")
    )
    args = parser.parse_args()

    nml_generator = safe_nml_generator if args.safe else main_generator
    for _ in nml_generator():
        pass

def safe_nml_generator():
    nml_file = os.path.join(os.getcwd(), 'output.nml')
    cprint('Writing Traktor file to {}'.format(nml_file))
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
    cprint("Wrote %d tracks to collection\n" % count, type='success')

def main_generator():
    # TODO: maybe add more progress updates
    nml_file = os.path.join(os.getcwd(), 'output.nml')
    with codecs.open(nml_file, "r+", "utf-8") as out_fh:
        # TODO(trow): Don't hard-wire the drive letter.
        db = database.Database(conf.LIBRARY_DB)
        cprint('Writing Traktor file to {}'.format(nml_file))

        cprint("Parsing NML file")

        writer = nml_writer.NMLReadWriter("T:", "/Library", out_fh, db)
        try:
            writer.add_new_files()
            cprint("Writing data to file storage")
            writer.close()
        except ValueError as e:
            cprint(f"NMLReadWriter failed with error {e} "
                    "due to an unexpected NML file format. "
                    "Switching to backup NMLWriter.")
            yield from safe_nml_generator()
        except MemoryError:
            cprint(f"NMLReadWriter failed with error {e} "
                    "due to insufficient memory. "
                    "Switching it backup NMLWriter."
                    "We recommend rerunning with the '--safe' flag")
            yield from safe_nml_generator()

    # Move the file to where Traktor users expect to find it.
    cprint('Copying NML file to {}'.format(conf.TRAKTOR_NML_FILE))
    cmd = [
        'install',      # command that combines cp with chown, chmod, and strip
        '-m', '0775',
        '-g', 'traktor',
        nml_file,
        conf.TRAKTOR_NML_FILE]
    subprocess.check_call(cmd)


if __name__ == "__main__":
    main()
