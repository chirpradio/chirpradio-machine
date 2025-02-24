#!/usr/bin/env python

import io
import unittest
import xml.dom.minidom
import time
import random

import mutagen.id3

from chirp.common import mp3_header
from chirp.common import unicode_util
from chirp.common import timestamp
from chirp.library import audio_file
from chirp.library import audio_file_test
from chirp.library import nml_writer
from chirp.library import order

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
    
    # def test_parse(self):
    #     nml_file = os.path.join(os.getcwd(), 'output.nml')
    #     with codecs.open(nml_file, "r+", "utf-8") as output2:
    #         writer = nml_writer.NMLReadWriter("test_file_volume", "/lib", output2)
    #         print(writer.get_timestamp())

    # def test_write2(self):
    #     nml_file = os.path.join(os.getcwd(), 'output.nml')
    #     with codecs.open(nml_file, "r+", "utf-8") as output2:
    #         writer = nml_writer.NMLReadWriter("test_file_volume", "/lib", output2)
    #         writer.test_write()

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
        # Very temporary way to make a database class with the needed function
        db = type("TestDB", (), {
            "get_au_files_after": lambda self, timestamp: test_au_files
        })()

        # Add new audio files to the NML file
        writer = nml_writer.NMLReadWriter(file_volume, root_dir, output, db)
        new_timestamp = writer.add_new_files()
        writer.close()

        # Check that all the expected elements are still in the file
        output_str = output.getvalue()
        self.assert_is_valid_xml(output_str)
        self.assertTrue(test_data.TEST_NML_PREFIX % 5 in output_str)
        self.assertTrue(test_data.TEST_NML_SUFFIX % new_timestamp in output_str)
        self.assertTrue(test_data.TEST_NML_ENTRIES_1 in output_str)
        for i in range(4):
            expected_entry = NMLWriterTest._au_file_to_nml_entry(test_au_files[i], root_dir, file_volume.replace("/", "/:"))
            self.assertTrue(expected_entry in output_str)
    
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
        # Very temporary way to make a database class with the needed function
        db = type("TestDB", (), {
            "get_au_files_after": lambda self, timestamp: test_au_files
        })()

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
        for i in range(10):
            expected_entry = NMLWriterTest._au_file_to_nml_entry(test_au_files[i], root_dir, file_volume.replace("/", "/:"))
            self.assertTrue(expected_entry in output_str)

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
        # Very temporary way to make a database class with the needed function
        db = type("TestDB", (), {
            "get_au_files_after": lambda self, timestamp: files_to_modify
        })()

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
        # Very temporary way to make a database class with the needed function
        db = type("TestDB", (), {
            "get_au_files_after": lambda self, timestamp: files_to_modify
        })()

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
        # Very temporary way to make a database class with the needed function
        db = type("TestDB", (), {
            "get_au_files_after": lambda self, timestamp: shuffled_files
        })()

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
        for i in range(10):
            expected_entry = NMLWriterTest._au_file_to_nml_entry(shuffled_files[i], root_dir, file_volume.replace("/", "/:"))
            self.assertTrue(expected_entry in output_str)
        # Check correct order
        expected_ordered_entries = test_data.TEST_NML_ENTRIES_20
        for file in test_au_files:
            expected_ordered_entries += NMLWriterTest._au_file_to_nml_entry(file, root_dir, file_volume.replace("/", "/:"))
        self.assertTrue(expected_ordered_entries in output_str)

    # TODO: add test to make file from scratch
    def test_new_file(self):
        file_volume = "test_file_volume"
        root_dir = "/lib"
        output = io.StringIO()
        test_au_files = []
        for i in range(10):
            test_au_file = audio_file_test.get_test_audio_file(i)
            test_au_files.append(test_au_file)
        # Very temporary way to make a database class with the needed function
        db = type("TestDB", (), {
            "get_au_files_after": lambda self, timestamp: test_au_files
        })()

        writer = nml_writer.NMLReadWriter(file_volume, root_dir, output, db)
        new_timestamp = writer.add_new_files()
        writer.close()

        output_str = output.getvalue()
        self.assert_is_valid_xml(output_str)
        self.assertTrue(test_data.TEST_NML_PREFIX % 10 in output_str)
        self.assertTrue(test_data.TEST_NML_SUFFIX % new_timestamp in output_str)
        for i in range(10):
            expected_entry = NMLWriterTest._au_file_to_nml_entry(test_au_files[i], root_dir, file_volume.replace("/", "/:"))
            self.assertTrue(expected_entry in output_str)
    
    # TODO: test where you add from scratch and then add auto without closing


if __name__ == "__main__":
    unittest.main()
