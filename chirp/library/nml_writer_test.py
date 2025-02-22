#!/usr/bin/env python

import io
import unittest
import xml.dom.minidom
import time

import mutagen.id3

from chirp.common import mp3_header
from chirp.common import unicode_util
from chirp.library import audio_file
from chirp.library import audio_file_test
from chirp.library import nml_writer
from chirp.library import order

from chirp.library.nml_writer_test_data import TEST_NML_PREFIX, TEST_NML_ENTRIES_1, TEST_NML_SUFFIX, NML_ENTRY_FORMAT

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
    #         writer = nml_writer.NMLWriter2("test_file_volume", "/lib", output2)
    #         print(writer.get_timestamp())

    # def test_write2(self):
    #     nml_file = os.path.join(os.getcwd(), 'output.nml')
    #     with codecs.open(nml_file, "r+", "utf-8") as output2:
    #         writer = nml_writer.NMLWriter2("test_file_volume", "/lib", output2)
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
        
        # TODO: make this an XML element from the start instead of using fromstring
        return NML_ENTRY_FORMAT % entry_data

    def test_add(self):
        # Create mock data
        file_volume = "test_file_volume"
        root_dir = "/lib"
        starting_timestamp = 123
        output = io.StringIO(TEST_NML_PREFIX % 1 + TEST_NML_ENTRIES_1 + TEST_NML_SUFFIX % starting_timestamp)
        test_au_files = []
        for i in range(4):
            test_au_file = audio_file_test.get_test_audio_file(i)
            # test_au_file.import_timestamp = starting_timestamp + 1
            test_au_files.append(test_au_file)
        # Very temporary way to make a database class with the needed function
        db = type("TestDB", (), {
            "get_au_files_after": lambda self, timestamp: test_au_files
        })()

        # Add new audio files to the NML file
        writer = nml_writer.NMLWriter2(file_volume, root_dir, output, db)
        new_timestamp = writer.add_new_files()
        writer.close()

        # Check that all the expected elements are still in the file
        output_str = output.getvalue()
        self.assert_is_valid_xml(output_str)
        self.assertTrue(TEST_NML_PREFIX % 5 in output_str)
        self.assertTrue(TEST_NML_SUFFIX % new_timestamp in output_str)
        self.assertTrue(TEST_NML_ENTRIES_1 in output_str)
        for i in range(4):
            expected_entry = NMLWriterTest._au_file_to_nml_entry(test_au_files[i], root_dir, file_volume.replace("/", "/:"))
            self.assertTrue(expected_entry in output_str)

    # def test_modify(self):
    #     # Create mock data
    #     test_au_files = []
    #     for i in range(10):
    #         test_au_file = audio_file_test.get_test_audio_file(i)
    #         test_au_file.import_timestamp = i
    #     output = io.StringIO()
    #     # Very temporary way to make a database class with the needed function
    #     db = type("TestDB", (object), {
    #         "get_au_files_after": lambda self, timestamp: 1
    #     })()
    #     writer = nml_writer.NMLWriter2("test_file_volume", "/lib", output, )

    # TODO: add test to check added order is correct


if __name__ == "__main__":
    unittest.main()
