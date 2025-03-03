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
# TODO: index file?
from chirp.library import audio_file_test
import threading

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

def main_generator():
    # db = database.Database(conf.LIBRARY_DB)
    # start_t = time.perf_counter_ns()
    # for i in db.get_since(0):
    #     pass
    # print("Elapsed seconds", (time.perf_counter_ns() - start_t) / 1e9)
    # TODO: add memory error backup plan
# TODO: add back the printing progress
# TODO: add ocmmand line arg to run the safer version from the start
# TODO: maybe add more progress updates
    nml_file = os.path.join(os.getcwd(), 'output.nml')
    with codecs.open(nml_file, "r+", "utf-8") as out_fh:
        # TODO(trow): Don't hard-wire the drive letter.
        # TODO: Replace this with the readwriter
        # db = database.Database(conf.LIBRARY_DB)
        db = type("TestDB", (), {
            "get_since": lambda self, timestamp: [audio_file_test.get_test_audio_file(4)],
            "get_since_less_queries": lambda self, timestamp: [audio_file_test.get_test_audio_file(4)],
        })()
        cprint('Writing Traktor file to {}'.format(nml_file))
        start_t = time.perf_counter_ns()

        cprint("Parsing NML file")
        writer = nml_writer.NMLReadWriter("T:", "/Library", out_fh, db)

        is_errored = False

        def event_handler(event, args=[]):
            match event:
                case "Closing":
                    cprint("Writing data to file storage")
                case "ValueError":
                    is_errored = True
                    cprint(f"NMLReadWriter failed with error {args[0]} "
                           "due to an incorrect NML file format. "
                           "Switching to backup NMLWriter.")
                case "MemoryError":
                    is_errored = True
                    cprint(f"NMLReadWriter failed with error {args[0]} "
                           "due to insufficient memory. "
                           "Switching it backup NMLWriter.") #TODO: edit this if I add the safe flag

        def run_add_new_files(event_handler):
            try:
                writer.add_new_files()
                event_handler("Closing")
                writer.close()
            except ValueError as e:
                event_handler("ValueError", [e])
            except MemoryError:
                event_handler("MemoryError")
        
        adding_thread = threading.Thread(target=run_add_new_files, args=[event_handler])

        adding_thread.start()
        adding_thread.join()

        if is_errored:
            yield from safe_nml_generator()

        # writer.add_new_files()
        # writer.close()
        print("Elapsed seconds", (time.perf_counter_ns() - start_t) / 1e9)

    # Original with query
    # nml_file = os.path.join(os.getcwd(), 'output.nml')
    # cprint('Writing Traktor file to {}'.format(nml_file))
    # with codecs.open(nml_file, "w", "utf-8") as out_fh:
    #     # TODO(trow): Don't hard-wire the drive letter.
    #     # TODO: Replace this with the readwriter
    #     writer = nml_writer.NMLWriter("T:", "/Library", out_fh)
    #     db = database.Database(conf.LIBRARY_DB)
    #     count = 0
    #     # start_ns = time.perf_counter_ns()
    #     start_t = time.time()
    #     for au_file in db.get_all():
    #         writer.write(au_file)
    #         count += 1
    #         elapsed_t = time.time() - start_t
    #         cprint(type='count', count=count, elapsed_seconds=elapsed_t)
    #         if count % 1000 == 0:
    #             sys.stderr.write("{count} ({rate:.1f}/s)...\n".format(count=count, rate=count / elapsed_t))
    #         yield
    #     writer.close()
    #    # print("Elapsed seconds", (time.perf_counter_ns() - start_ns) / 1e9)

    # Old method but without the sql query ~35 seconds
    # nml_file = os.path.join(os.getcwd(), 'output.nml')
    # cprint('Writing Traktor file to {}'.format(nml_file))
    # with codecs.open(nml_file, "w", "utf-8") as out_fh:
    #     # TODO(trow): Don't hard-wire the drive letter.
    #     # TODO: Replace this with the readwriter
    #     writer = nml_writer.NMLWriter("T:", "/Library", out_fh)
    #     # count = 0
    #     start_ns = time.perf_counter_ns()
    #     # start_t = time.time()
    #     for i in range(272988):
    #         writer.write(audio_file_test.get_test_audio_file(i))
    #         # count += 1
    #         # elapsed_t = time.time() - start_t
    #         # cprint(type='count', count=count, elapsed_seconds=elapsed_t)
    #         # if count % 1000 == 0:
    #         #     sys.stderr.write("{count} ({rate:.1f}/s)...\n".format(count=count, rate=count / elapsed_t))
    #         # yield
    #     writer.close()
    #     print("Elapsed seconds", (time.perf_counter_ns() - start_ns) / 1e9)

    # nml_file = os.path.join(os.getcwd(), 'output.nml')
    # cprint('Writing Traktor file to {}'.format(nml_file))
    # with codecs.open(nml_file, "r+", "utf-8") as out_fh:
    #     start_ns = time.perf_counter_ns()
    #     for line in out_fh:
    #         pass
    #     print("Elapsed seconds", (time.perf_counter_ns() - start_ns) / 1e9)

    # # Move the file to where Traktor users expect to find it.
    # cprint('Copying NML file to {}'.format(conf.TRAKTOR_NML_FILE))
    # cmd = [
    #     'install',      # command that combines cp with chown, chmod, and strip
    #     '-m', '0775',
    #     '-g', 'traktor',
    #     nml_file,
    #     conf.TRAKTOR_NML_FILE]
    # subprocess.check_call(cmd)

    # cprint("Wrote %d tracks to collection\n" % count, type='success')


if __name__ == "__main__":
    main()
