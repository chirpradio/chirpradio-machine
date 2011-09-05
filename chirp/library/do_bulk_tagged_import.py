import codecs
import os
import sys

from chirp.common import timestamp
from chirp.library import bulk_tagging_form
from chirp.library import database
from chirp.library import import_transaction


def load_dir_hash_map():
    map = {}
    # TODO(trow): This is hard-wired for the bulk tagging forms used
    # during the initial import.
    for name in ("/home/trow/crawls/crawl-2.log",
                 "/home/trow/crawls/crawl-3.log"):
        for line in codecs.open(name, "r", "utf-8"):
            dir_hash, msg, path = line.strip().split("\t")
            assert dir_hash not in map
            map[dir_hash] = path
    return map


def main():
    db = database.Database("/home/trow/library/catalog.sqlite3_db")
    
    def new_txn():
        # TODO(trow): Use a better /tmp directory.
        return import_transaction.ImportTransaction(db, 1, timestamp.now(),
                                                    "/tmp/import",
                                                    dry_run=False)
    # TODO(trow): Use a better prefix.
    TARGET = "/home/trow/prefix"
    SIZE_LIMIT = 0.95 * (4 << 30)  # 95% of 4GB, our basic import size.
    txn = None

    dir_hash_map = load_dir_hash_map()
    form = bulk_tagging_form.parse_file(
        codecs.open("/home/trow/initial_import/form2.txt", "r", "utf-8"))
    verified = sorted(
        [x for x in form.iteritems() if x[1][0] == bulk_tagging_form.VERIFIED],
        key = lambda x: x[1])
    for i, (dir_hash, val) in enumerate(verified):
        code = val[0]
        if code != bulk_tagging_form.VERIFIED:
            continue
        path = dir_hash_map[dir_hash].encode("utf-8")
        _, artist, talb = val
        sys.stderr.write("%d of %d\n" % (i, len(verified)))
        sys.stderr.write("%s\n" % path)
        sys.stderr.write("Artist: %s\n" % artist.encode("utf-8"))
        if not txn:
            txn = new_txn()
        txn.add_album_from_directory(path, new_album_name=talb)
        if txn.total_size_in_bytes > SIZE_LIMIT:
            txn.commit(TARGET)
            txn = None

    if txn:
        txn.commit(TARGET)


def profile():
    import cProfile, pstats
    prof = cProfile.Profile()
    prof = prof.runctx("main()", globals(), locals())
    stats = pstats.Stats(prof)
    stats.sort_stats("cumulative")  # Or cumulative
    stats.print_stats(80)  # 80 = how many to print 

main()
