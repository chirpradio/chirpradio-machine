import os
import time
import unittest
from mock import patch

from chirp.library import audio_file_test
from chirp.library import do_delete_audio_file_from_db
from chirp.library import database


TEST_DB_NAME_PATTERN = "/tmp/chirp-library-db_test.%d.sqlite"


class DeleteFingerprintTest(unittest.TestCase):

    def setUp(self):
        self.name = TEST_DB_NAME_PATTERN % int(time.time() * 1000000)
        self.db = database.Database(self.name)

    def tearDown(self):
        os.unlink(self.name)

    def _add_test_audiofiles(self):
        test_volume = 17
        test_import_timestamp = 1230959520

        # populate some dummy audiofiles into the database
        all_au_files = [audio_file_test.get_test_audio_file(i)
                        for i in xrange(10)]
        add_txn = self.db.begin_add(test_volume, test_import_timestamp)

        for au_file in all_au_files:
            au_file.volume = test_volume
            au_file.import_timestamp = test_import_timestamp

        for au_file in all_au_files:
            add_txn.add(au_file)
        add_txn.commit()

    def test_del_audiofilese__full_delete_single(self):
        # SETUP
        test_fingerprint = "0000000000000007"

        # Create db tables
        self.assertTrue(self.db.create_tables())
        self._add_test_audiofiles()

        # make sure 10 records exist
        self.assertEqual(len(list(self.db.get_all())), 10)

        # quick confirmation that the audiofile that we want to test exists.
        af = self.db.get_by_fingerprint(test_fingerprint)
        self.assertEquals(af.fingerprint, test_fingerprint)

        afm = do_delete_audio_file_from_db.AudioFileManager(
            library_db_file=self.name)

        # TEST
        afm.del_audiofiles([test_fingerprint])

        # RESULTS
        # verify audiofile doesn't exist
        af = self.db.get_by_fingerprint(test_fingerprint)
        self.assertEquals(af, None)

        # make sure only 9 records exist now
        self.assertEqual(len(list(self.db.get_all())), 9)

    def test_del_audiofiles__full_delete_multiple(self):
        # SETUP
        test_fingerprint_1 = "0000000000000005"
        test_fingerprint_2 = "0000000000000007"

        # Create db tables
        self.assertTrue(self.db.create_tables())
        self._add_test_audiofiles()

        # make sure 10 records exist
        self.assertEqual(len(list(self.db.get_all())), 10)

        # quick confirmation that the audiofiles that we want to test exists.
        af = self.db.get_by_fingerprint(test_fingerprint_1)
        self.assertEquals(af.fingerprint, test_fingerprint_1)
        af = self.db.get_by_fingerprint(test_fingerprint_2)
        self.assertEquals(af.fingerprint, test_fingerprint_2)

        afm = do_delete_audio_file_from_db.AudioFileManager(
            library_db_file=self.name)

        # TEST
        afm.del_audiofiles([test_fingerprint_1, test_fingerprint_2])

        # RESULTS
        # verify audiofiles don't exist
        af = self.db.get_by_fingerprint(test_fingerprint_1)
        self.assertEquals(af, None)

        af = self.db.get_by_fingerprint(test_fingerprint_2)
        self.assertEquals(af, None)

        # make sure only 8 records exist now
        self.assertEqual(len(list(self.db.get_all())), 8)

    def test_del_audiofiles__full_delete_non_existing_fingerprint(self):
        # SETUP
        test_fingerprint_1 = "0000000000000020"

        # Create db tables
        self.assertTrue(self.db.create_tables())
        self._add_test_audiofiles()

        # make sure 10 records exist
        self.assertEqual(len(list(self.db.get_all())), 10)

        afm = do_delete_audio_file_from_db.AudioFileManager(
            library_db_file=self.name)

        # TEST
        afm.del_audiofiles([test_fingerprint_1])

        # RESULTS
        # make sure nothing was deleted
        self.assertEqual(len(list(self.db.get_all())), 10)

    def test_del_audiofiles__raises_exception(self):
        # SETUP
        test_fingerprint_1 = "0000000000000007"

        # Create db tables
        self.assertTrue(self.db.create_tables())
        self._add_test_audiofiles()

        # make sure 10 records exist
        self.assertEqual(len(list(self.db.get_all())), 10)

        afm = do_delete_audio_file_from_db.AudioFileManager(
            library_db_file=self.name)

        # TEST
        def _raise_exception(*args, **kwargs):
            raise Exception('Test')

        with patch.object(afm, 'conn', autospec=True) as mock_conn:
            mock_conn.execute.side_effect = _raise_exception
            with self.assertRaises(Exception):
                afm.del_audiofiles([test_fingerprint_1])
            mock_conn.rollback.assert_called_with()

    def test_get_audio_files__existing_record(self):
        # SETUP
        test_fingerprint = "0000000000000007"

        # Create db tables
        self.assertTrue(self.db.create_tables())
        self._add_test_audiofiles()

        afm = do_delete_audio_file_from_db.AudioFileManager(
            library_db_file=self.name)

        # TEST
        af = afm.get_audio_files(fingerprints=[test_fingerprint])

        # RESULTS
        self.assertSetEqual(
            set(a['fingerprint'] for a in af),
            set([test_fingerprint]))

    def test_get_audio_files__non_existing_records(self):
        # SETUP
        test_fingerprint_1 = "0000000000000020"

        # Create db tables
        self.assertTrue(self.db.create_tables())
        self._add_test_audiofiles()

        afm = do_delete_audio_file_from_db.AudioFileManager(
            library_db_file=self.name)

        # TEST
        af = afm.get_audio_files(
            fingerprints=[test_fingerprint_1])

        # RESULTS
        self.assertEqual(len(list(af)), 0)

    def test_get_tags__existing_record(self):
        # SETUP
        test_fingerprint_1 = "0000000000000005"

        # Create db tables
        self.assertTrue(self.db.create_tables())
        self._add_test_audiofiles()

        afm = do_delete_audio_file_from_db.AudioFileManager(
            library_db_file=self.name)

        # TEST
        af = afm.get_tags(
            fingerprints=[test_fingerprint_1])

        # RESULTS
        self.assertListEqual(
            list(a['fingerprint'] for a in af),
            5 * [test_fingerprint_1])

    def test_get_tags__non_existing_records(self):
        # SETUP
        test_fingerprint_1 = "0000000000000020"

        # Create db tables
        self.assertTrue(self.db.create_tables())
        self._add_test_audiofiles()

        afm = do_delete_audio_file_from_db.AudioFileManager(
            library_db_file=self.name)

        # TEST
        af = afm.get_tags(
            fingerprints=[test_fingerprint_1])

        # RESULTS
        self.assertEqual(len(list(af)), 0)

    def test_print_rows_can_handle_non_ascii(self):
        afm = do_delete_audio_file_from_db.AudioFileManager(
            library_db_file=self.name
        )
        afm.print_rows([
            [u'non-ascii string with a \xf8 character'],
        ])
