import unittest
import sys
import io
import shutil
import tempfile
import time

from chirp.library.do_periodic_import import import_albums
from chirp.library import do_dump_new_artists_in_dropbox
from chirp.library import database

class DoPeriodicImport(unittest.TestCase):
    old_audio_file = "plasterbrain - Nimbasa CORE - Nimbasa CORE - Single (01a6c39c69a662103e83dd8ace4a18a8d16a11c6)"

    def update_db(self, db_path):
        def _update_db(db):
            db.__init__(db_path)
        return _update_db
    
    def update_drop(self, dropbox_folder):
        def _update_drop(drop):
            drop.__init__(dropbox_folder)
        return _update_drop
    
    def update_artists(self, whitelist):
        def _update_artists(artists):
            with tempfile.NamedTemporaryFile(mode="w+") as tmp:
                tmp.write(whitelist)
                tmp.read()
                artists._WHITELIST_FILE = tmp.name
                artists._init()
        return _update_artists
    
    
    def test_continue_past_error(self):

        db_path = "chirp/library/testdata/do_periodic_import_test/empty.db"
        db = database.Database(db_path)
        for audio_file in db.get_all():
            self.assertEqual(audio_file, None) #making sure test database has not been corrupted
        db.close()
        
        with tempfile.NamedTemporaryFile() as tmp:
            shutil.copy(db_path, tmp.name)
            input = "1" #Yes
            sys.stdin = io.StringIO(input)
            for _ in import_albums(False, True,
                                   update_db = self.update_db(tmp.name),
                                   update_artists = self.update_artists("Beatles"),
                                   update_drop = self.update_drop("chirp/library/testdata/do_dump_new_artists_test/dropbox/Beatles")):
                pass
            tmp_db = database.Database(tmp.name)
            for audio_file in tmp_db.get_all():
                self.assertEqual(str(audio_file), "Beatles - Beatles Song - Beatles Album (01a6c39c69a662103e83dd8ace4a18a8d16a11c6)")
    
        time.sleep(1)
    
    def test_correct_artist(self):
        import warnings
        warnings.simplefilter("ignore")

        db_path = "chirp/library/testdata/do_periodic_import_test/empty.db"
        db = database.Database(db_path)
        for audio_file in db.get_all():
            self.assertEqual(audio_file, None)
        db.close()

        input = "1" #Yes/The Beatles
        sys.stdin = io.StringIO(input)
        for _ in do_dump_new_artists_in_dropbox.main_generator(True, True,
                                                               update_artists=self.update_artists("The Beatles\n"),
                                                               update_drop=self.update_drop("chirp/library/testdata/do_dump_new_artists_test/dropbox/Beatles")):
            
            pass



        with tempfile.NamedTemporaryFile() as tmp:
            shutil.copy(db_path, tmp.name)
            input = "1" #Yes
            sys.stdin = io.StringIO(input)
            for _ in import_albums(False, True,
                                   update_db = self.update_db(tmp.name),
                                   update_artists = self.update_artists("The Beatles\n"),
                                   update_drop = self.update_drop("chirp/library/testdata/do_dump_new_artists_test/dropbox/Beatles")):
                pass
            tmp_db = database.Database(tmp.name)
            for audio_file in tmp_db.get_all():
                print(audio_file)
                self.assertEqual(str(audio_file), "The Beatles - Beatles Song - Beatles Album (01a6c39c69a662103e83dd8ace4a18a8d16a11c6)")
    
        time.sleep(1) #ensure that timestamp of imports is different

    def test_do_not_correct_artist(self):
        import warnings
        warnings.simplefilter("ignore")

        db_path = "chirp/library/testdata/do_periodic_import_test/empty.db"
        db = database.Database(db_path)
        for audio_file in db.get_all():
            self.assertEqual(audio_file, None)
        db.close()

        input = "2" #No/Beatles
        sys.stdin = io.StringIO(input)
        for _ in do_dump_new_artists_in_dropbox.main_generator(True, True,
                                                               update_artists=self.update_artists("The Beatles\n"),
                                                               update_drop=self.update_drop("chirp/library/testdata/do_dump_new_artists_test/dropbox/Beatles")):
            
            pass



        with tempfile.NamedTemporaryFile() as tmp:
            shutil.copy(db_path, tmp.name)
            input = "1" #Yes
            sys.stdin = io.StringIO(input)
            for _ in import_albums(False, True,
                                   update_db = self.update_db(tmp.name),
                                   update_artists = self.update_artists("Beatles\nThe Beatles\n"),
                                   update_drop = self.update_drop("chirp/library/testdata/do_dump_new_artists_test/dropbox/Beatles")):
                pass
            tmp_db = database.Database(tmp.name)
            for audio_file in tmp_db.get_all():
                print(audio_file)
                self.assertEqual(str(audio_file), "Beatles - Beatles Song - Beatles Album (01a6c39c69a662103e83dd8ace4a18a8d16a11c6)")
        
        time.sleep(1)
    
    
    def test_multiple_matches(self):
        import warnings
        warnings.simplefilter("ignore")

        db_path = "chirp/library/testdata/do_periodic_import_test/Beatles.db"
        db = database.Database(db_path)
        for audio_file in db.get_all():
            self.assertEqual(str(audio_file), "Beatles - Beatles Song - Beatles Album (01a6c39c69a662103e83dd8ace4a18a8d16a11c6)")
        db.close()

        input = "1" #Beatles
        sys.stdin = io.StringIO(input)
        for _ in do_dump_new_artists_in_dropbox.main_generator(True, True,
                                                               update_artists=self.update_artists("Beatles\nThe Beatles\n"),
                                                               update_drop=self.update_drop("chirp/library/testdata/do_periodic_import_test/dropbox/")):
            
            pass


        with tempfile.NamedTemporaryFile() as tmp:
            shutil.copy(db_path, tmp.name)
            input = "1" #Yes
            sys.stdin = io.StringIO(input)

            for _ in import_albums(False, True,
                                   update_db = self.update_db(tmp.name),
                                   update_artists = self.update_artists("Beatles\nThe Beatles\n"),
                                   update_drop = self.update_drop("chirp/library/testdata/do_periodic_import_test/dropbox")):
                pass
            
            tmp_db = database.Database(tmp.name)
            audio_files = [str(audiofile) for audiofile in tmp_db.get_all()]
            print(audio_files)
            correct_audio_files = ["Beatles - Touch-Tone Telephone - Spirit Phone (999851444012f39ef90f12cc22c06166afb0a848)",
                                   "Beatles - Beatles Song - Beatles Album (01a6c39c69a662103e83dd8ace4a18a8d16a11c6)"]
            self.assertEqual(audio_files, correct_audio_files)
        
        time.sleep(1)
    
if __name__ == '__main__':
    unittest.main()