
import sqlite3
import os
import time
import unittest

import mutagen.id3

from chirp.library import audio_file_test
from chirp.library import database
from chirp.library.schema import MIGRATIONS, LEGACY_TABLES, LATEST_VERSION

TEST_DB_NAME_PATTERN = "/tmp/chirp-library-db_test.%d.sqlite3_db"
OLD_DB_NAME_PATTERN = "/tmp/chirp-library-db_old_test.%d.sqlite3_db"

class DatabaseMigrationTest(unittest.TestCase):
    def setUp(self):
        self.name = TEST_DB_NAME_PATTERN % int(time.time() * 1000000)
        self.db = database.Database(self.name, auto_migrate = False)

    def tearDown(self):
        os.unlink(self.name)

    def test_migrate(self):
        self.assertEqual(self.db._user_version, 0)
        # Migrate to newest version
        self.db.auto_migrate()
        # Ensure version was updated
        self.assertEqual(self.db._user_version, LATEST_VERSION)
        # Ensure version in SQLite header matches
        cursor = self.db._shared_conn.execute("PRAGMA user_version;")
        self.assertEqual(cursor.fetchone()[0], self.db._user_version)

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

    def test_add(self):
        all_au_files = [audio_file_test.get_test_audio_file(i)
                        for i in range(1000)]

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
    
    # This is the same as test_add but with get_all replaced with get_all_less_queries
    def test_get_all_since(self):
        all_au_files = [audio_file_test.get_test_audio_file(i)
                        for i in range(1000)]

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
        self.assertEqual([], list(self.db.get_all_less_queries()))

        for au_file in all_au_files:
            au_file.volume = None
            au_file.import_timestamp = None

        add_txn = self.db.begin_add(test_volume, test_import_timestamp)
        for au_file in all_au_files:
            add_txn.add(au_file)
        add_txn.commit()

        # Should be able to get_all_less_queries.
        self.assert_same_audio_files(
            all_au_files,
            list(self.db.get_all_less_queries()))

        # Should be able to get each file by fingerprint.
        for au_file in all_au_files:
            fetched_au_file = self.db.get_by_fingerprint(au_file.fingerprint)
            self.assertEqual(au_file, fetched_au_file)

    def test_update(self):
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
        new_tag = mutagen.id3.TPUB(text=["TPUB"])
        test_au_file.mutagen_id3.add(new_tag)
        # Delete a tag.
        del test_au_file.mutagen_id3["TALB"]

        new_timestamp = test_import_timestamp + 1000
        self.db.update(test_au_file, new_timestamp)

        fetched_au_file = self.db.get_by_fingerprint(test_au_file.fingerprint)
        self.assertEqual(test_au_file, fetched_au_file)

    def _test_with_get_since_impl(self, use_less_queries):
        test_volume = 19
        audio_files_dict = {}
        def add_test_files(range_start, range_stop, import_timestamp):
            add_txn = self.db.begin_add(test_volume, import_timestamp)
            for i in range(range_start, range_stop):
                test_au_file = audio_file_test.get_test_audio_file(i)
                test_au_file.volume = None
                test_au_file.import_timestamp = None
                audio_files_dict[test_au_file.fingerprint] = test_au_file
                add_txn.add(test_au_file)
            add_txn.commit()
        def assert_num_since(num_expected, since_timestamp):
            num_since = 0
            get_since_impl = self.db.get_since_less_queries if use_less_queries\
                else self.db.get_since
            for au_file in get_since_impl(since_timestamp):
                self.assertTrue(au_file.fingerprint in audio_files_dict)
                self.assertEqual(au_file, audio_files_dict[au_file.fingerprint])
                num_since += 1
            self.assertEqual(num_since, num_expected)
        
        first_import_timestamp = 1230055555
        add_test_files(0, 5, first_import_timestamp)
        assert_num_since(5, first_import_timestamp - 55555)
        assert_num_since(0, first_import_timestamp)
        assert_num_since(0, first_import_timestamp + 55555)

        second_import_timestamp = 1230077777
        add_test_files(5, 11, second_import_timestamp)
        assert_num_since(11, first_import_timestamp - 1)
        assert_num_since(6, first_import_timestamp)
        assert_num_since(6, second_import_timestamp - 1)
        assert_num_since(0, second_import_timestamp)
        assert_num_since(0, second_import_timestamp + 1)

    def test_get_since(self):
        self._test_with_get_since_impl(False)
    
    def test_get_since_less_queries(self):
        self._test_with_get_since_impl(True)


if __name__ == "__main__":
    unittest.main()
