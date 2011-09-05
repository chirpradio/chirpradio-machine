
import unittest

import mutagen.id3

from chirp.library import album
from chirp.library import audio_file


class AlbumTest(unittest.TestCase):

    def create_test_album(self, num_tracks):
        all_au_files = []        
        for i in range(1, num_tracks+1):
            au_file = audio_file.AudioFile()
            all_au_files.append(au_file)
            au_file.fingerprint = "%040x" % i
            au_file.mutagen_id3 = mutagen.id3.ID3()
            au_file.mutagen_id3.add(
                mutagen.id3.TPE1(text=["Fall, The"], encoding=3))
            au_file.mutagen_id3.add(
                mutagen.id3.TALB(text=["TALB [Tag]"], encoding=3))
            au_file.mutagen_id3.add(
                mutagen.id3.TIT2(text=["TIT2 [Tag]"], encoding=3))
            au_file.mutagen_id3.add(
                mutagen.id3.TRCK(text=["%d/%d" % (i, num_tracks)], encoding=3))
        return all_au_files

    create_test_album.__test__ = False  # not a test itself

    def test_standardize_tags(self):
        test_alb = self.create_test_album(4)
        album._standardize_tags(test_alb)
        # Check that nothing chaged.
        self.assertEqual(
            [repr(x.mutagen_id3) for x in self.create_test_album(4)],
            [repr(x.mutagen_id3) for x in test_alb])
        
        # Check that the album ID got attached.
        expected_id = album._compute_album_id(test_alb)
        for au_file in test_alb:
            self.assertEqual(expected_id, au_file.album_id)

        # Check that we correctly split the artist name.
        test_alb[2].mutagen_id3["TPE1"].text = ["The Fall ft. T-Pain"]
        album._standardize_tags(test_alb)
        self.assertEqual("The Fall",
                         unicode(test_alb[2].mutagen_id3["TPE1"]))
        self.assertEqual(u"TIT2 (w/ T-Pain) [Tag]",
                         unicode(test_alb[2].mutagen_id3["TIT2"]))

        # Check that we can change the album name using our optional
        # arg.
        album._standardize_tags(test_alb, new_album_name="New Name")
        for au_file in test_alb:
            self.assertEqual("New Name",
                             unicode(au_file.mutagen_id3["TALB"]))

        # Check that the import fails if the album is named inconsistently.
        test_alb[1].mutagen_id3["TALB"].text = ["Some other album name"]
        self.assertRaises(album.AlbumError,
                          album._standardize_tags, test_alb)


if __name__ == "__main__":
    unittest.main()
