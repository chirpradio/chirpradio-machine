#!/usr/bin/env python

import io
import unittest
import xml.dom.minidom

import mutagen.id3

from chirp.common import mp3_header
from chirp.library import audio_file
from chirp.library import audio_file_test
from chirp.library import nml_writer

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


if __name__ == "__main__":
    unittest.main()
