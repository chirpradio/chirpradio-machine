#!/usr/bin/env python

import unittest
import mutagen.id3

from chirp.library import audio_file
from chirp.library import checker
from chirp.library import constants
from chirp.library import ufid


TEST_VOL = 17
TEST_TS = 1228080954
TEST_FP = "1" * 40
TEST_DURATION = 12345
TEST_ALBUM_ID = 33333
TEST_FRAME_COUNT = 444
TEST_FRAME_SIZE = 55555


class CheckerTest(unittest.TestCase):

    def setUp(self):
        self.au_file = audio_file.AudioFile()
        self.au_file.volume = TEST_VOL
        self.au_file.import_timestamp = TEST_TS
        self.au_file.fingerprint = TEST_FP
        self.au_file.duration_ms = TEST_DURATION
        self.au_file.mutagen_id3 = mutagen.id3.ID3()
        self.au_file.album_id = TEST_ALBUM_ID
        self.au_file.frame_count = TEST_FRAME_COUNT
        self.au_file.frame_size = TEST_FRAME_SIZE

    def assertTagError(self, prefix):
        errors = checker.find_tags_errors(self.au_file)
        for err_msg in errors:
            if err_msg.startswith(prefix):
                return
        print errors
        self.fail()

    def assertNoTagError(self, prefix):
        errors = checker.find_tags_errors(self.au_file)
        for err_msg in errors:
            if err_msg.startswith(prefix):
                self.fail(errors)

    def test_general_tag_checks(self):
        self.assertTagError(checker.ERROR_TAG_MISSING_REQUIRED + "UFID")
        
        self.au_file.mutagen_id3["TALB"] = mutagen.id3.TALB(
            text="Album Name", encoding=0)  # latin-1, which is wrong
        self.assertTagError(checker.ERROR_TAG_WRONG_ENCODING)
        self.au_file.mutagen_id3["LINK"] = mutagen.id3.LINK(
            url="http://www.chirpradio.org/")
        self.assertTagError(checker.ERROR_TAG_NOT_WHITELISTED)

    def test_numeric_tag_checks(self):
        tlen_tag = mutagen.id3.TLEN(text=["bad"])
        self.au_file.mutagen_id3["TLEN"] = tlen_tag

        self.assertTagError(checker.ERROR_NUMERIC_MALFORMED + "TLEN")

        tlen_tag.text = ["12345"]
        self.assertNoTagError(checker.ERROR_NUMERIC_MALFORMED + "TLEN")

    def test_tflt_tag_checks(self):
        tflt_tag = mutagen.id3.TFLT(text=["bad"])
        self.au_file.mutagen_id3["TFLT"] = tflt_tag
        self.assertTagError(checker.ERROR_TFLT_NON_WHITELISTED)

        tflt_tag.text = ["MPG/3"]
        self.assertNoTagError(checker.ERROR_TFLT_NON_WHITELISTED)

    def test_tlen_tag_checks(self):
        tlen_tag = mutagen.id3.TLEN(text=[str(TEST_DURATION+1)])
        self.au_file.mutagen_id3["TLEN"] = tlen_tag
        self.assertTagError(checker.ERROR_TLEN_INCORRECT)

        tlen_tag.text = [str(TEST_DURATION)]
        self.assertNoTagError(checker.ERROR_TLEN_INCORRECT)

    def test_town_tag_checks(self):
        town_tag = mutagen.id3.TOWN(text=["Incorrect"])
        self.au_file.mutagen_id3["TOWN"] = town_tag
        self.assertTagError(checker.ERROR_TOWN_INCORRECT)
        
        town_tag.text = [constants.TOWN_FILE_OWNER]
        self.assertNoTagError(checker.ERROR_TOWN_INCORRECT)

    def test_tpe_tag_checks(self):
        tpe_tag = mutagen.id3.TPE1(text=["Non-standard artist name"])
        self.au_file.mutagen_id3.add(tpe_tag)
        self.assertTagError(checker.ERROR_TPE_NONSTANDARD)

        tpe_tag.text = ["Bob Dylan"]
        self.assertNoTagError(checker.ERROR_TPE_NONSTANDARD)

    def test_order_tag_checks(self):
        for tag_type in (mutagen.id3.TPOS, mutagen.id3.TRCK):
            tag = tag_type()
            for bad_order in ("bad", "3", "3,4", "  3/4", "4/3"):
                tag.text = [bad_order]
                self.au_file.mutagen_id3.add(tag)
                self.assertTagError(
                    checker.ERROR_ORDER_MALFORMED + tag.FrameID)
            tag.text = ["3/4"]
            self.assertNoTagError(
                checker.ERROR_ORDER_MALFORMED + tag.FrameID)

    def test_ufid_tag_checks(self):
        ufid_tag = mutagen.id3.UFID(owner="bad", data="bad")
        self.au_file.mutagen_id3.add(ufid_tag)
        self.assertTagError(checker.ERROR_TAG_MISSING_REQUIRED + "UFID")

        ufid_tag.owner = constants.UFID_OWNER_IDENTIFIER
        # Need to re-add since changing the owner also changes the
        # hash key.  A very annoying corner case, more proof that
        # mutagen's "just make it look like a dict" strategy is
        # ultimately misguided.
        self.au_file.mutagen_id3.add(ufid_tag)
        self.assertTagError(checker.ERROR_UFID_BAD_MALFORMED)

        bad_ufid_data = ufid.ufid(TEST_VOL + 1, TEST_TS, TEST_FP)
        ufid_tag.data = bad_ufid_data
        self.assertTagError(checker.ERROR_UFID_BAD_VOLUME)

        bad_ufid_data = ufid.ufid(TEST_VOL, TEST_TS + 1, TEST_FP)
        ufid_tag.data = bad_ufid_data
        self.assertTagError(checker.ERROR_UFID_BAD_TIMESTAMP)

        bad_ufid_data = ufid.ufid(TEST_VOL, TEST_TS, "2" * 40)
        ufid_tag.data = bad_ufid_data
        self.assertTagError(checker.ERROR_UFID_BAD_FINGERPRINT)

        ufid_tag.data = self.au_file.ufid()
        errors = checker.find_tags_errors(self.au_file)
        self.assertNoTagError(checker.ERROR_TAG_MISSING_REQUIRED + "UFID")
        self.assertNoTagError(checker.ERROR_UFID_BAD_OWNER)
        self.assertNoTagError(checker.ERROR_UFID_BAD_MALFORMED)
        self.assertNoTagError(checker.ERROR_UFID_BAD_VOLUME)
        self.assertNoTagError(checker.ERROR_UFID_BAD_TIMESTAMP)
        self.assertNoTagError(checker.ERROR_UFID_BAD_FINGERPRINT)

    def test_tag_checks_no_errors(self):
        self.au_file.mutagen_id3.add(mutagen.id3.TOWN(
                text=["MPG/3"],
                encoding=constants.DEFAULT_ID3_TEXT_ENCODING))
        self.au_file.mutagen_id3.add(mutagen.id3.TLEN(
                text=[str(TEST_DURATION)],
                encoding=constants.DEFAULT_ID3_TEXT_ENCODING))
        self.au_file.mutagen_id3.add(mutagen.id3.TOWN(
                text=[constants.TOWN_FILE_OWNER],
                encoding=constants.DEFAULT_ID3_TEXT_ENCODING))
        self.au_file.mutagen_id3.add(mutagen.id3.TPE1(
                text=["Bob Dylan"],
                encoding=constants.DEFAULT_ID3_TEXT_ENCODING))
        self.au_file.mutagen_id3.add(mutagen.id3.TIT2(
                text=["Just Like Tom Thumb's Blues"],
                encoding=constants.DEFAULT_ID3_TEXT_ENCODING))
        self.au_file.mutagen_id3.add(mutagen.id3.TRCK(
                text=["3/4"],
                encoding=constants.DEFAULT_ID3_TEXT_ENCODING))
        self.au_file.mutagen_id3.add(self.au_file.ufid_tag())
        self.au_file.mutagen_id3.add(mutagen.id3.TFLT(
                text=["MPG/3"],
                encoding=constants.DEFAULT_ID3_TEXT_ENCODING))
        self.au_file.mutagen_id3.add(mutagen.id3.TXXX(
                desc=constants.TXXX_FRAME_SIZE_DESCRIPTION,
                text=[unicode(TEST_FRAME_SIZE)],
                encoding=constants.DEFAULT_ID3_TEXT_ENCODING))
        self.au_file.mutagen_id3.add(mutagen.id3.TXXX(
                desc=constants.TXXX_FRAME_COUNT_DESCRIPTION,
                text=[unicode(TEST_FRAME_COUNT)],
                encoding=constants.DEFAULT_ID3_TEXT_ENCODING))
        self.au_file.mutagen_id3.add(mutagen.id3.TXXX(
                desc=constants.TXXX_ALBUM_ID_DESCRIPTION,
                text=[unicode(TEST_ALBUM_ID)],
                encoding=constants.DEFAULT_ID3_TEXT_ENCODING))


        self.assertEqual([], checker.find_tags_errors(self.au_file))


if __name__ == "__main__":
    unittest.main()


        
