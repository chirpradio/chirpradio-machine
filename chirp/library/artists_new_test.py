import unittest
import io
import codecs
from chirp.library import artists, similarity

TEST_WHITELIST = """
# A comment, followed by a blank line

Bob Dylan
The Fall
Fall
John Lee Hooker
Tom Petty & the Heartbreakers
Tom Petty and the Heartbreakers
"""

def _unicode_stringio(text):
    return io.StringIO(text)

class ArtistsNewTest(unittest.TestCase):

    def test_loading_whitelist(self):

        file_obj = _unicode_stringio(TEST_WHITELIST)
        artists.reset_artist_whitelist(artists._read_artist_whitelist_from_file(file_obj))
        
        names = artists._complete_whitelist
        self.assertTrue(len(names) == 6)

        collision_mappings = artists._collision_mappings
        self.assertTrue(len(collision_mappings[similarity.canonicalize_string("The Fall")]) == 2)
        self.assertTrue(len(collision_mappings[similarity.canonicalize_string("Tom Petty and the Heartbreakers")]) == 2)
    
    def test_check_collisions(self):
        for artist in artists._collision_mappings:
            if len(artists._collision_mappings[artist]) > 1:
                print(artist)
        file_obj = _unicode_stringio(TEST_WHITELIST)
        artists.reset_artist_whitelist(artists._read_artist_whitelist_from_file(file_obj))

        for the_fall in ["fall", "fall, the", " the fall", "fall, the "]:
            self.assertTrue(len(artists.check_collisions(the_fall)) == 2)


if __name__ == "__main__":
    unittest.main()