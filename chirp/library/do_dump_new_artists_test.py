import unittest
import sys
import io

from chirp.library import do_dump_new_artists_in_dropbox

class DoDumpNewArtists(unittest.TestCase):
    whitelist_file = "chirp/library/testdata/do_dump_new_artists_test/whitelist"
    dropbox_folder = ""

    def update_artists(self, artists):
        artists._WHITELIST_FILE = self.whitelist_file
        artists._init()

    def update_drop(self, drop):
        drop.__init__(self.dropbox_folder)
    
    def write_whitelist(self, whitelist):
        with open(self.whitelist_file, "w") as file:
            file.write(whitelist)
    
    def set_dropbox(self, folder):
        dropbox_root = "chirp/library/testdata/do_dump_new_artists_test/dropbox/"
        self.dropbox_folder = dropbox_root + folder
    
    def test_new_artist(self):
        import warnings
        warnings.simplefilter("ignore")
        whitelist = "ABCDE\nThe Beatles\nThe Fall\nZebra\n"
        self.write_whitelist(whitelist)
        self.set_dropbox("plasterbrain")
        for _ in do_dump_new_artists_in_dropbox.main_generator(True, True,
                                                               update_artists=self.update_artists,
                                                               update_drop=self.update_drop):
            pass
        with open(self.whitelist_file, "r") as file:
            self.assertEqual(file.read(), "ABCDE\nThe Beatles\nThe Fall\nplasterbrain\nZebra\n")

    def test_yes(self):
        import warnings
        warnings.simplefilter("ignore")

        whitelist = "ABCDE\nThe Beatles\nThe Fall\nZebra\n"
        self.write_whitelist(whitelist)
        self.set_dropbox("Beatles")

        input = "1" #Yes
        sys.stdin = io.StringIO(input)
        for _ in do_dump_new_artists_in_dropbox.main_generator(True, True,
                                                               update_artists=self.update_artists,
                                                               update_drop=self.update_drop):
            pass

        with open(self.whitelist_file, "r") as file:
            self.assertEqual(file.read(), whitelist)
    
    def test_no(self):
        import warnings
        warnings.simplefilter("ignore")

        whitelist = "ABCDE\nThe Beatles\nThe Fall\nZebra\n"
        self.write_whitelist(whitelist)
        self.set_dropbox("Beatles")

        input = "2" #No
        sys.stdin = io.StringIO(input)
        for _ in do_dump_new_artists_in_dropbox.main_generator(True, True,
                                                               update_artists=self.update_artists,
                                                               update_drop=self.update_drop):
            pass

        with open(self.whitelist_file, "r") as file:
            self.assertEqual(file.read(), "ABCDE\nBeatles\nThe Beatles\nThe Fall\nZebra\n")


    def test_collision(self):
        import warnings
        warnings.simplefilter("ignore")

        whitelist = "ABCDE\nBeatles\nThe Beatles\nThe Fall\nZebra\n"
        self.write_whitelist(whitelist)
        self.set_dropbox("Beatles")

        input = "1"
        sys.stdin = io.StringIO(input)

        for _ in do_dump_new_artists_in_dropbox.main_generator(True, True,
                                                               update_artists=self.update_artists,
                                                               update_drop=self.update_drop):
            pass

        with open(self.whitelist_file, "r") as file:
            self.assertEqual(file.read(), "ABCDE\nBeatles\nThe Beatles\nThe Fall\nZebra\n")

        
if __name__ == '__main__':
    unittest.main()