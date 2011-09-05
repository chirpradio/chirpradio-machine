#!/usr/bin/env python

import cStringIO
import unittest
import xml.dom.minidom

import mutagen.id3

from chirp.common import mp3_header
from chirp.library import audio_file
from chirp.library import audio_file_test
from chirp.library import nml_writer



class NMLWriterTest(unittest.TestCase):

    def assert_is_valid_xml(self, xml_str):
        xml.dom.minidom.parseString(xml_str)

    def test_empty(self):
        output = cStringIO.StringIO()
        writer = nml_writer.NMLWriter("test_file_volume", "/lib", output)
        writer.close()
        output_str = output.getvalue()
        self.assert_is_valid_xml(output_str)
        self.assertTrue("<COLLECTION ENTRIES=\"%10d\"" % 0 in output_str)

    def test_simple(self):
        output = cStringIO.StringIO()
        writer = nml_writer.NMLWriter("test_file_volume", "/lib", output)
        for i in xrange(10):
            writer.write(audio_file_test.get_test_audio_file(i))
        writer.close()
        output_str = output.getvalue()
        self.assert_is_valid_xml(output_str)
        self.assertTrue("<COLLECTION ENTRIES=\"%10d\"" % 10 in output_str)


if __name__ == "__main__":
    unittest.main()
