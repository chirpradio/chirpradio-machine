import os
import sys

from chirp.common.printing import cprint
from chirp.library import album
from chirp.library import audio_file
from chirp.library import import_file
from chirp.library import ufid


class ImportTransaction(object):

    def __init__(self, db, volume, import_timestamp, tmp_prefix,
                 dry_run=True):
        self._db = db
        self._volume = volume
        self._import_timestamp = import_timestamp
        self._tmp_prefix = tmp_prefix
        self._dry_run = dry_run

        self.total_size_in_bytes = 0
        self.num_albums = 0
        self._all_au_files = []

    @property
    def num_tracks(self):
        return len(self._all_au_files)

    def add_album(self, alb, new_album_name=None):
        # Plug in the volume and import timestamp for this transaction.
        alb.set_volume_and_import_timestamp(
            self._volume, self._import_timestamp)
        alb.ensure_payloads()

        cprint(u'Adding Album "%s"' % alb.title())
        sys.stdout.flush()

        # Write the files to our temporary prefix.
        for au_file in alb.all_au_files:
            # Might raise an ImportFileError.
            if not self._dry_run:
                import_file.write_file(au_file, self._tmp_prefix)
        # We forget the payloads immediately to save RAM.
        alb.drop_payloads()

        # Everything checks out!
        self._all_au_files.extend(alb.all_au_files)
        self.num_albums += 1
        self.total_size_in_bytes += sum(
            au.frame_size for au in alb.all_au_files)

    def commit(self, target_prefix):
        if self._dry_run:
            return
        # Start a database transaction to add the files.
        txn = self._db.begin_add(self._volume, self._import_timestamp)
        # Write each new file into the database.
        for au_file in self._all_au_files:
            txn.add(au_file)
        ufid_prefix = ufid.ufid_prefix(self._volume, self._import_timestamp)
        # Strip off trailing "/"
        if ufid_prefix.endswith("/"):
            ufid_prefix = ufid_prefix[:-1]
        tmp_dir = os.path.join(self._tmp_prefix, ufid_prefix)
        real_dir = os.path.join(target_prefix, ufid_prefix)
        cprint("*** Committing %d albums / %d bytes" % (
            self.num_albums, self.total_size_in_bytes))
        cprint("*** tmp_dir=%s" % tmp_dir)
        cprint("*** real_dir=%s" % real_dir)
        sys.stdout.flush()
        os.renames(tmp_dir, real_dir)
        txn.commit()
        # Write out a list of source files that were just committed.
        out = open(os.path.join(real_dir, "_source_files"), "w")
        for path in sorted(af.path for af in self._all_au_files):
            out.write(path)
            out.write("\n")
        out.close()
