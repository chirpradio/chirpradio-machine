
import os
import time
import unittest

import mutagen.id3

from chirp.library import audio_file_test
from chirp.library import database

TEST_DB_NAME_PATTERN = "/tmp/chirp-library-db_test.%d.sqlite"

class DatabaseTest(unittest.TestCase):

    def setUp(self):
        self.name = TEST_DB_NAME_PATTERN % int(time.time() * 1000000)
        self.db = database.Database(self.name)

    def tearDown(self):
        os.unlink(self.name)

    def assert_same_audio_files(self, seq_a, seq_b):
        def _make_dict(seq):
            return dict(
                ((x.volume, x.import_timestamp, x.fingerprint), x)
                for x in seq)
        dict_a = _make_dict(seq_a)
        dict_b = _make_dict(seq_b)
        self.assertEqual(set(dict_a), set(dict_b))
        for key in dict_a:
            self.assertEqual(dict_a[key], dict_b[key])

    def test_create_tables(self):
        # Should succeed the first time.
        self.assertTrue(self.db.create_tables())
        # Should fail second time.
        self.assertFalse(self.db.create_tables())
        # Should start out empty.
        self.assertEqual([], list(self.db.get_all()))

    def test_add(self):
        all_au_files = [audio_file_test.get_test_audio_file(i)
                        for i in xrange(1000)]

        self.assertTrue(self.db.create_tables())

        test_volume = 17
        test_import_timestamp = 1230959520

        # It is an error to add an audio file with the wrong volume or
        # timestamp.
        boom_txn = self.db.begin_add(test_volume, test_import_timestamp)
        au_file = all_au_files[0]
        au_file.volume = test_volume + 1
        au_file.import_timestamp = test_import_timestamp
        self.assertRaises(AssertionError, boom_txn.add, au_file)
        au_file.volume = test_volume
        au_file.import_timestamp = test_import_timestamp + 1
        self.assertRaises(AssertionError, boom_txn.add, au_file)

        # Committing an empty transaction is OK.
        add_txn = self.db.begin_add(test_volume, test_import_timestamp)
        add_txn.commit()

        # Reverting an empty transaction is OK too.
        add_txn = self.db.begin_add(test_volume, test_import_timestamp)
        add_txn.revert()

        for au_file in all_au_files:
            au_file.volume = None
            au_file.import_timestamp = None

        add_txn = self.db.begin_add(test_volume, test_import_timestamp)
        for au_file in all_au_files:
            add_txn.add(au_file)
        add_txn.revert()
        # Should still be empty after reverting.
        self.assertEqual([], list(self.db.get_all()))

        for au_file in all_au_files:
            au_file.volume = None
            au_file.import_timestamp = None

        add_txn = self.db.begin_add(test_volume, test_import_timestamp)
        for au_file in all_au_files:
            add_txn.add(au_file)
        add_txn.commit()

        # Should be able to get_all.
        self.assert_same_audio_files(
            all_au_files,
            list(self.db.get_all()))

        # Should be able to get each file by fingerprint.
        for au_file in all_au_files:
            fetched_au_file = self.db.get_by_fingerprint(au_file.fingerprint)
            self.assertEqual(au_file, fetched_au_file)

    def test_update(self):
        self.assertTrue(self.db.create_tables())

        test_au_file = audio_file_test.get_test_audio_file(123)
        test_au_file.volume = None
        test_au_file.import_timestamp = None
        test_volume = 19
        test_import_timestamp = 1230012345

        add_txn = self.db.begin_add(test_volume, test_import_timestamp)
        add_txn.add(test_au_file)
        add_txn.commit()

        fetched_au_file = self.db.get_by_fingerprint(test_au_file.fingerprint)
        self.assertEqual(test_au_file, fetched_au_file)

        # Modify an existing tag.
        mod_tag = test_au_file.mutagen_id3["TPE1"]
        mod_tag.text[0] += "arbitrary change"
        # Add a new tag.
        new_tag = mutagen.id3.TPUB(text=[u"TPUB"])
        test_au_file.mutagen_id3.add(new_tag)
        # Delete a tag.
        del test_au_file.mutagen_id3["TALB"]

        new_timestamp = test_import_timestamp + 1000
        self.db.update(test_au_file, new_timestamp)

        fetched_au_file = self.db.get_by_fingerprint(test_au_file.fingerprint)
        self.assertEqual(test_au_file, fetched_au_file)


if __name__ == "__main__":
    unittest.main()
