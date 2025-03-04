#!/usr/bin/env python

import io
import unittest
import xml.dom.minidom
import time
import random
from tempfile import TemporaryFile

import mutagen.id3

from chirp.common import mp3_header
from chirp.common import unicode_util
from chirp.common import timestamp
from chirp.library import audio_file
from chirp.library import audio_file_test
from chirp.library import nml_writer
from chirp.library import order, database

from chirp.library import nml_writer_test_data as test_data

import codecs
import os


class NMLWriterTest(unittest.TestCase):

    def assert_is_valid_xml(self, xml_str):
        xml.dom.minidom.parseString(xml_str)

    def test_empty(self):
        output = io.StringIO()
        writer = nml_writer.NMLWriter("test_file_volume", "/lib", output)
        writer.close()
        output_str = output.getvalue()
        self.assert_is_valid_xml(output_str)
        self.assertTrue("<COLLECTION ENTRIES=\"%10d\"" % 0 in output_str)

    def test_simple(self):
        output = io.StringIO()
        writer = nml_writer.NMLWriter("test_file_volume", "/lib", output)
        for i in range(10):
            writer.write(audio_file_test.get_test_audio_file(i))
        writer.close()
        output_str = output.getvalue()
        self.assert_is_valid_xml(output_str)
        self.assertTrue("<COLLECTION ENTRIES=\"%10d\"" % 10 in output_str)

    # I compare strings to avoid dependency of ElementTree for these tests
    # However, using ElementTree for the tests would make them more robust to format changes

    # Avoid get_since dependency by using this mock object
    def _create_mock_db(test_au_files):
        return type("TestDB", (), {
            "get_since": lambda self, timestamp: test_au_files,
            "get_since_less_queries": lambda self, timestamp: test_au_files
        })()

    def _au_file_to_nml_entry(au_file, root_dir, file_volume_quoted):
        entry_data = {}

        entry_data["order_num"], entry_data["total_num"] = order.decode(
            str(au_file.mutagen_id3.get("TRCK")))
        if entry_data["total_num"] is None:
            entry_data["total_num"] = 100

        entry_data["artist"] = unicode_util.simplify(
            au_file.mutagen_id3.get("TPE1", nml_writer._UNKNOWN_ARTIST))
        entry_data["album"] = unicode_util.simplify(
            au_file.mutagen_id3.get("TALB", nml_writer._UNKNOWN_ALBUM))
        entry_data["song"] = unicode_util.simplify(
            au_file.mutagen_id3.get("TIT2", nml_writer._UNKNOWN_SONG))
        
        # TODO(trow): Set this somehow.
        entry_data["genre"] = "Unknown"

        entry_data["dir"] = au_file.canonical_directory(prefix=root_dir).replace("/", "/:")
        entry_data["file"] = au_file.canonical_filename()
        entry_data["volume"] = file_volume_quoted

        entry_data["bitrate"] = int(
            au_file.mp3_header.bit_rate_kbps * 1000)
        entry_data["size_in_kb"] = int(au_file.frame_size / 1024)
        entry_data["duration_s"] = int(au_file.duration_ms / 1000)
            
        entry_data["import_date"] = time.strftime(
            "%Y/%m/%d", time.gmtime(au_file.import_timestamp))
        entry_data["modified_date"] = entry_data["import_date"]
        entry_data["modified_time"] = "35364"

        # Clean up any XML-unsafe characters and wrap each value in
        # quotes.
        for k, v in list(entry_data.items()):
            new_v = xml.sax.saxutils.quoteattr(str(v))
            if new_v != v:
                entry_data[k] = new_v

        return test_data.NML_ENTRY_FORMAT % entry_data
    
    def _write_new_files(self, file_volume, root_dir, output, db):
        writer = nml_writer.NMLReadWriter(file_volume, root_dir, output, db)
        new_timestamp = writer.add_new_files()
        writer.close()
        return new_timestamp
    
    def _create_prefix_suffix_strings(self, num_entries=None, new_timestamp=None):
        result = []
        if num_entries is not None:
            result.append(test_data.TEST_NML_PREFIX % num_entries)
        if new_timestamp is not None:
            result.append(test_data.TEST_NML_SUFFIX % new_timestamp)
        return result
    
    def _write_and_get_common_strs(self, file_volume, root_dir, output, db,
                                   num_entries, expected_files):
        new_timestamp = self._write_new_files(file_volume, root_dir, output, db)
        expected_strs = self._create_prefix_suffix_strings(num_entries, new_timestamp)
        for file in expected_files:
            expected_strs += NMLWriterTest._au_file_to_nml_entry(file, root_dir, file_volume.replace("/", "/:"))
        return expected_strs
    
    def _assert_strings_in_output(self, expected_strings, output=None, output_string=None):
        output_str = output_string if output_string is not None else output.getvalue()
        output_str_no_newline = output_str.replace("\n", "")
        self.assert_is_valid_xml(output_str)
        for expected_str in expected_strings:
            self.assertTrue(expected_str.replace("\n", "") in output_str_no_newline,
                f"Assertion failed on string {expected_str if len(expected_str) < 500 else expected_str[:500] + '...'}")
        
        return (output_str, output_str_no_newline)

    def test_add(self):
        # Create mock data
        file_volume = "test_file_volume"
        root_dir = "/lib"
        starting_timestamp = 123
        output = io.StringIO(test_data.TEST_NML_PREFIX % 1 + test_data.TEST_NML_ENTRIES_1 + test_data.TEST_NML_SUFFIX % starting_timestamp)
        test_au_files = []
        for i in range(4):
            test_au_file = audio_file_test.get_test_audio_file(i)
            test_au_files.append(test_au_file)
        db = NMLWriterTest._create_mock_db(test_au_files)

        expected_strs = self._write_and_get_common_strs(file_volume, root_dir,
            output, db, 5, test_au_files)
        expected_strs += test_data.TEST_NML_ENTRIES_1
        
        self._assert_strings_in_output(expected_strs, output)
    
    def test_add_more(self):
        # Create mock data
        file_volume = "test_file_volume"
        root_dir = "/lib"
        starting_timestamp = 123
        output = io.StringIO(test_data.TEST_NML_PREFIX % 20 + test_data.TEST_NML_ENTRIES_20 + test_data.TEST_NML_SUFFIX % starting_timestamp)
        test_au_files = []
        for i in range(10):
            test_au_file = audio_file_test.get_test_audio_file(i)
            test_au_files.append(test_au_file)
        db = NMLWriterTest._create_mock_db(test_au_files)

        expected_strs = self._write_and_get_common_strs(file_volume, root_dir,
            output, db, 30, test_au_files)
        expected_strs += test_data.TEST_NML_ENTRIES_20
        
        self._assert_strings_in_output(expected_strs, output)

    def test_modify(self):
        # Create mock data
        file_volume = "T:"
        root_dir = "/Library"
        starting_timestamp = 100
        files_to_modify = [
            audio_file_test.get_test_audio_file(0),
            audio_file_test.get_test_audio_file(1),
        ]
        files_to_modify[0].fingerprint = "b8609231eeaf3ed162854f8043092e7995ca6ec5"
        files_to_modify[0].mp3_header.bit_rate_kbps = 320
        files_to_modify[0].duration_ms = 226000
        files_to_modify[1].fingerprint = "5f5fbc125fe58681970710383237463a5dde44cd"
        files_to_modify[1].mp3_header.bit_rate_kbps = 320
        files_to_modify[1].duration_ms = 212000
        for file in files_to_modify:
            file.volume = 1
            file.import_timestamp = timestamp.parse_human_readable("20230130-200020")
        output = io.StringIO(test_data.TEST_NML_PREFIX % 20 + test_data.TEST_NML_ENTRIES_20 + test_data.TEST_NML_SUFFIX % starting_timestamp)
        db = NMLWriterTest._create_mock_db(files_to_modify)

        writer = nml_writer.NMLReadWriter(file_volume, root_dir, output, db)
        new_timestamp = writer.add_new_files()
        writer.close()

        output_str = output.getvalue()
        self.assertTrue(test_data.TEST_NML_PREFIX % 20 in output_str)
        self.assertTrue(test_data.TEST_NML_SUFFIX % new_timestamp in output_str)
        self.assertFalse(test_data.TEST_NML_ENTRIES_1 in output_str)
        self.assertFalse(test_data.TEST_NML_SECOND_ENTRY in output_str)
        for file in files_to_modify:
            expected_entry = NMLWriterTest._au_file_to_nml_entry(file, root_dir, file_volume.replace("/", "/:"))
            self.assertTrue(expected_entry in output_str)
        expected_old_entries = test_data.TEST_NML_ENTRIES_20.replace(test_data.TEST_NML_ENTRIES_1 + "\n", '').replace(test_data.TEST_NML_SECOND_ENTRY + "\n", '')
        self.assertTrue(expected_old_entries in output_str)
    
    def test_modify_non_consecutive(self):
        # Create mock data
        file_volume = "T:"
        root_dir = "/Library"
        starting_timestamp = 100
        files_to_modify = [
            audio_file_test.get_test_audio_file(0),
            audio_file_test.get_test_audio_file(1),
        ]
        files_to_modify[0].fingerprint = "b8609231eeaf3ed162854f8043092e7995ca6ec5"
        files_to_modify[0].mp3_header.bit_rate_kbps = 320
        files_to_modify[0].duration_ms = 226000
        files_to_modify[1].fingerprint = "dde770a3ef37e72585081f46d44ad1435ed0367b"
        files_to_modify[1].mp3_header.bit_rate_kbps = 320
        files_to_modify[1].duration_ms = 309000
        for file in files_to_modify:
            file.volume = 1
            file.import_timestamp = timestamp.parse_human_readable("20230130-200020")
        output = io.StringIO(test_data.TEST_NML_PREFIX % 20 + test_data.TEST_NML_ENTRIES_20 + test_data.TEST_NML_SUFFIX % starting_timestamp)
        db = NMLWriterTest._create_mock_db(files_to_modify)

        writer = nml_writer.NMLReadWriter(file_volume, root_dir, output, db)
        new_timestamp = writer.add_new_files()
        writer.close()

        output_str = output.getvalue()
        self.assertTrue(test_data.TEST_NML_PREFIX % 20 in output_str)
        self.assertTrue(test_data.TEST_NML_SUFFIX % new_timestamp in output_str)
        self.assertFalse(test_data.TEST_NML_ENTRIES_1 in output_str)
        self.assertFalse(test_data.TEST_NML_THIRD_ENTRY in output_str)
        self.assertTrue(test_data.TEST_NML_SECOND_ENTRY in output_str)
        for file in files_to_modify:
            expected_entry = NMLWriterTest._au_file_to_nml_entry(file, root_dir, file_volume.replace("/", "/:"))
            self.assertTrue(expected_entry in output_str)
        ordered_entries = test_data.TEST_NML_ENTRIES_20\
            .replace(test_data.TEST_NML_ENTRIES_1,\
                     NMLWriterTest._au_file_to_nml_entry(files_to_modify[0], root_dir, file_volume))\
            .replace(test_data.TEST_NML_THIRD_ENTRY,\
                     NMLWriterTest._au_file_to_nml_entry(files_to_modify[1], root_dir, file_volume))
        self.assertTrue(ordered_entries in output_str)

    def test_track_order(self):
        # Create mock data
        file_volume = "test_file_volume"
        root_dir = "/lib"
        starting_timestamp = 123
        output = io.StringIO(test_data.TEST_NML_PREFIX % 20 + test_data.TEST_NML_ENTRIES_20 + test_data.TEST_NML_SUFFIX % starting_timestamp)
        test_au_files = []
        for i in range(10):
            test_au_file = audio_file_test.get_test_audio_file(i)
            test_au_file.album_id = 1
            test_au_file.mutagen_id3.delall("TRCK")
            test_au_file.mutagen_id3.add(mutagen.id3.TRCK(text=["%d/10" % (i + 1)]))
            test_au_files.append(test_au_file)
        shuffled_files = test_au_files.copy()
        random.shuffle(shuffled_files)
        db = NMLWriterTest._create_mock_db(shuffled_files)

        # Add new audio files to the NML file
        writer = nml_writer.NMLReadWriter(file_volume, root_dir, output, db)
        new_timestamp = writer.add_new_files()
        writer.close()

        # Check that all the expected elements are still in the file
        output_str = output.getvalue()
        self.assert_is_valid_xml(output_str)
        self.assertTrue(test_data.TEST_NML_PREFIX % 30 in output_str)
        self.assertTrue(test_data.TEST_NML_SUFFIX % new_timestamp in output_str)
        self.assertTrue(test_data.TEST_NML_ENTRIES_20 in output_str)
        output_str_no_newline = output_str.replace("\n", "")
        for i in range(10):
            expected_entry = NMLWriterTest._au_file_to_nml_entry(shuffled_files[i], root_dir, file_volume.replace("/", "/:"))
            self.assertTrue(expected_entry.replace("\n", "") in output_str_no_newline)
        # Check correct order
        expected_ordered_entries = test_data.TEST_NML_ENTRIES_20
        for file in test_au_files:
            expected_ordered_entries += NMLWriterTest._au_file_to_nml_entry(file, root_dir, file_volume.replace("/", "/:"))
        self.assertTrue(expected_ordered_entries.replace("\n", "") in output_str_no_newline)

    # Create new file from scratch
    def test_new_file(self):
        file_volume = "test_file_volume"
        root_dir = "/lib"
        output = io.StringIO()
        test_au_files = []
        for i in range(10):
            test_au_file = audio_file_test.get_test_audio_file(i)
            test_au_file.volume = None
            test_au_file.import_timestamp = None
            test_au_files.append(test_au_file)
        db_name = "/tmp/chirp-library-db_test.%d.sqlite3_db" % int(time.time() * 1000000)
        db = database.Database(db_name)
        txn = db.begin_add(17, 1230959520)
        for file in test_au_files:
            txn.add(file)
        txn.commit()

        writer = nml_writer.NMLReadWriter(file_volume, root_dir, output, db)
        new_timestamp = writer.add_new_files()
        writer.close()

        output_str = output.getvalue()
        self.assert_is_valid_xml(output_str)
        self.assertTrue(test_data.TEST_NML_PREFIX.replace("\n", "") % 10 in output_str)
        self.assertTrue(test_data.TEST_NML_SUFFIX.replace("\n", "") % new_timestamp in output_str)
        for i in range(10):
            expected_entry = NMLWriterTest._au_file_to_nml_entry(test_au_files[i], root_dir, file_volume.replace("/", "/:"))
            self.assertTrue(expected_entry.replace("\n", "") in output_str)
    
    def _add_test_files_to_db(db, range_start, range_stop, import_timestamp):
            added_files = []
            txn = db.begin_add(17, import_timestamp)
            for i in range(range_start, range_stop):
                test_au_file = audio_file_test.get_test_audio_file(i)
                test_au_file.volume = None
                test_au_file.import_timestamp = None
                added_files.append(test_au_file)
                txn.add(test_au_file)
            txn.commit()
            return added_files

    # Add from scratch and then add auto without closing
    def test_create_then_add(self):
        file_volume = "test_file_volume"
        root_dir = "/lib"
        output = io.StringIO()
        db_name = "/tmp/chirp-library-db_test.%d.sqlite3_db" % int(time.time() * 1000000)
        db = database.Database(db_name)
        test_au_files = []
        writer = nml_writer.NMLReadWriter(file_volume, root_dir, output, db)
        def add_test_files_to_db(range_start, range_stop, import_timestamp):
            test_au_files.extend(
                NMLWriterTest._add_test_files_to_db(db, range_start, range_stop, import_timestamp)
            )
        
        add_test_files_to_db(0, 5, 1230000001)
        first_timestamp = writer.add_new_files()

        time.sleep(1)

        add_test_files_to_db(5, 11, first_timestamp + 1)
        second_timestamp = writer.add_new_files()

        self.assertGreater(second_timestamp, first_timestamp)

        writer.close()

        output_str = output.getvalue()
        self.assert_is_valid_xml(output_str)
        output_str_no_newline = output_str.replace("\n", "")
        self.assertTrue((test_data.TEST_NML_PREFIX % 11).replace("\n", "")
                        in output_str_no_newline)
        self.assertTrue((test_data.TEST_NML_SUFFIX % second_timestamp).replace("\n", "")
                        in output_str_no_newline)
        for au_file in test_au_files:
            expected_entry = NMLWriterTest._au_file_to_nml_entry(au_file, root_dir, file_volume.replace("/", "/:"))
            self.assertTrue((expected_entry).replace("\n", "") in output_str_no_newline)
    
    # Add from scratch, then call close, then add new files
    def test_create_close_add(self):
        file_volume = "test_file_volume"
        root_dir = "/lib"
        output = io.StringIO()
        db_name = "/tmp/chirp-library-db_test.%d.sqlite3_db" % int(time.time() * 1000000)
        db = database.Database(db_name)
        test_au_files = []
        def add_test_files_to_db(range_start, range_stop, import_timestamp):
            test_au_files.extend(
                NMLWriterTest._add_test_files_to_db(db, range_start, range_stop, import_timestamp)
            )
        
        add_test_files_to_db(0, 5, 1230000001)
        writer = nml_writer.NMLReadWriter(file_volume, root_dir, output, db)
        first_timestamp = writer.add_new_files()
        writer.close()

        time.sleep(1)

        add_test_files_to_db(5, 11, first_timestamp + 1)
        writer = nml_writer.NMLReadWriter(file_volume, root_dir, output, db)
        second_timestamp = writer.add_new_files()
        writer.close()

        self.assertGreater(second_timestamp, first_timestamp)

        output_str = output.getvalue()
        self.assert_is_valid_xml(output_str)
        output_str_no_newline = output_str.replace("\n", "")
        self.assertTrue((test_data.TEST_NML_PREFIX % 11).replace("\n", "")
                        in output_str_no_newline)
        self.assertTrue((test_data.TEST_NML_SUFFIX % second_timestamp).replace("\n", "")
                        in output_str_no_newline)
        for au_file in test_au_files:
            expected_entry = NMLWriterTest._au_file_to_nml_entry(au_file, root_dir, file_volume.replace("/", "/:"))
            self.assertTrue((expected_entry).replace("\n", "") in output_str_no_newline)

    # File without timestamp is given one after closing
    def test_missing_timestamp(self):
        file_volume = "test_file_volume"
        root_dir = "/lib"
        test_audio_file = audio_file_test.get_test_audio_file(0)
        db = NMLWriterTest._create_mock_db([test_audio_file])
        timestamp_no_newline = test_data.TEST_NML_TIMESTAMP_ELEM.replace("\n", "")
        output = io.StringIO(test_data.TEST_NML_PREFIX % 1 + test_data.TEST_NML_ENTRIES_1 + test_data.TEST_NML_SUFFIX_NO_TIMESTAMP)
        
        output_str = output.getvalue()
        self.assertFalse(timestamp_no_newline in output_str.replace("\n", ""))

        writer = nml_writer.NMLReadWriter(file_volume, root_dir, output, db)
        new_timestamp = writer.add_new_files()
        writer.close()

        output_str = output.getvalue()
        output_str_no_newline = output_str.replace("\n", "")
        self.assertTrue(timestamp_no_newline % new_timestamp in output_str_no_newline)
        self.assertTrue((test_data.TEST_NML_PREFIX % 2).replace("\n", "") in output_str_no_newline)
        self.assertTrue((test_data.TEST_NML_SUFFIX % new_timestamp).replace("\n", "") in output_str_no_newline)
        self.assertTrue(test_data.TEST_NML_ENTRIES_1.replace("\n", "") in output_str_no_newline)
        self.assertTrue(NMLWriterTest._au_file_to_nml_entry(test_audio_file, root_dir, file_volume)
                        .replace("\n", "") in output_str_no_newline)

    def test_invalid_file(self):
        file_volume = "test_file_volume"
        root_dir = "/lib"
        db_name = "/tmp/chirp-library-db_test.%d.sqlite3_db" % int(time.time() * 1000000)
        db = database.Database(db_name)

        output = io.StringIO("<NML>")
        self.assertRaises(ValueError, nml_writer.NMLReadWriter, file_volume,
                          root_dir, output, db)
        
        output = io.StringIO("<NML />")
        writer = nml_writer.NMLReadWriter(file_volume, root_dir, output, db)
        self.assertRaises(ValueError, writer.add_new_files)
        self.assertRaises(ValueError, writer.close)
    
    # TODO: add tests for manual adding

    # The append-only close mode doesn't work with StringIO outputs so it needs a separate test
    def test_append_only_close(self):
        # Create mock data
        file_volume = "test_file_volume"
        root_dir = "/lib"
        starting_timestamp = 1230000001
        test_au_files = []
        db_name = "/tmp/chirp-library-db_test.%d.sqlite3_db" % int(time.time() * 1000000)
        db = database.Database(db_name)
        test_au_files.extend(NMLWriterTest._add_test_files_to_db(db, 0, 10, starting_timestamp+1))
        with TemporaryFile("r+", encoding="utf-8") as output:
            output.write(test_data.TEST_NML_PREFIX % 20 + test_data.TEST_NML_ENTRIES_20 + test_data.TEST_NML_SUFFIX % starting_timestamp)
            expected_strs = self._create_prefix_suffix_strings(20, starting_timestamp)
            expected_strs += test_data.TEST_NML_ENTRIES_20
            output.seek(0)
            self._assert_strings_in_output(expected_strs, output_string=output.read())

            expected_strs = self._write_and_get_common_strs(file_volume, root_dir,
                output, db, 30, test_au_files)
            expected_strs += test_data.TEST_NML_ENTRIES_20
            output.seek(0)
            self._assert_strings_in_output(expected_strs, output_string=output.read())

    # Tests that the append-only close mode does not trigger if a file is made from scratch
    def test_from_scratch_temp_file(self):
        # Create mock data
        file_volume = "test_file_volume"
        root_dir = "/lib"
        starting_timestamp = 1230000001
        test_au_files = []
        db_name = "/tmp/chirp-library-db_test.%d.sqlite3_db" % int(time.time() * 1000000)
        db = database.Database(db_name)
        test_au_files.extend(NMLWriterTest._add_test_files_to_db(db, 0, 10, starting_timestamp+1))
        with TemporaryFile("r+", encoding="utf-8") as output:
            expected_strs = self._write_and_get_common_strs(file_volume, root_dir,
                output, db, 10, test_au_files)
            output.seek(0)
            self._assert_strings_in_output(expected_strs, output_string=output.read())
    
    # Tests that the append-only close mode does not trigger if a file is modified
    def test_modify_temp_file(self):
        # Files have only been modified
        file_volume = "test_file_volume"
        root_dir = "/lib"
        starting_timestamp = 1230000001
        file_to_modify = audio_file_test.get_test_audio_file(0)
        file_to_modify.fingerprint = "b8609231eeaf3ed162854f8043092e7995ca6ec5"
        file_to_modify.mp3_header.bit_rate_kbps = 320
        file_to_modify.duration_ms = 226000
        file_to_modify.volume = 1
        file_to_modify.import_timestamp = timestamp.parse_human_readable("20230130-200020")
        db = NMLWriterTest._create_mock_db([file_to_modify])
        with TemporaryFile("r+", encoding="utf-8") as output:
            output.write(test_data.TEST_NML_PREFIX % 20 + test_data.TEST_NML_ENTRIES_20 + test_data.TEST_NML_SUFFIX % starting_timestamp)
            expected_strs = self._create_prefix_suffix_strings(20, starting_timestamp)
            expected_strs += test_data.TEST_NML_ENTRIES_20
            output.seek(0)
            self._assert_strings_in_output(expected_strs, output_string=output.read())

            expected_strs = self._write_and_get_common_strs(file_volume, root_dir,
                output, db, 20, [file_to_modify])
            expected_strs += test_data.TEST_NML_ENTRIES_20.replace(test_data.TEST_NML_ENTRIES_1 + "\n", '')
            output.seek(0)
            (_, output_str_no_newline) = self._assert_strings_in_output(expected_strs, output_string=output.read())

            self.assertFalse(test_data.TEST_NML_ENTRIES_20 in output_str_no_newline)
            self.assertFalse(test_data.TEST_NML_ENTRIES_1 in output_str_no_newline)
        
        additional_test_file = audio_file_test.get_test_audio_file(1)
        db = NMLWriterTest._create_mock_db([file_to_modify, additional_test_file])
        with TemporaryFile("r+", encoding="utf-8") as output:
            output.write(test_data.TEST_NML_PREFIX % 20 + test_data.TEST_NML_ENTRIES_20 + test_data.TEST_NML_SUFFIX % starting_timestamp)
            expected_strs = self._create_prefix_suffix_strings(20, starting_timestamp)
            expected_strs += test_data.TEST_NML_ENTRIES_20
            output.seek(0)
            self._assert_strings_in_output(expected_strs, output_string=output.read())

            expected_strs = self._write_and_get_common_strs(file_volume, root_dir,
                output, db, 21, [file_to_modify, additional_test_file])
            expected_strs += test_data.TEST_NML_ENTRIES_20.replace(test_data.TEST_NML_ENTRIES_1 + "\n", '')
            output.seek(0)
            (_, output_str_no_newline) = self._assert_strings_in_output(expected_strs, output_string=output.read())

            self.assertFalse(test_data.TEST_NML_ENTRIES_20 in output_str_no_newline)
            self.assertFalse(test_data.TEST_NML_ENTRIES_1 in output_str_no_newline)


if __name__ == "__main__":
    unittest.main()
