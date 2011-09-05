
import logging
import os
from chirp.common import conf
from chirp.library import album
from chirp.library import audio_file


class Dropbox(object):

    def __init__(self, dropbox_path=None):
        dropbox_path = dropbox_path or conf.MUSIC_DROPBOX
        self._path = dropbox_path
        self._dirs = {}
        self._all_files = []
        # Scan the path and remember all of the subdirectories and
        # the MP3 files that they cotain.
        for basename in os.listdir(dropbox_path):
            child_path = os.path.join(dropbox_path, basename)
            if os.path.isdir(child_path):
                mp3_names = []
                for name in os.listdir(child_path):
                    # Skip dot-files.
                    if name.startswith("."):
                        continue
                    # Must have the right file extension.
                    if not name.lower().endswith(".mp3"):
                        continue
                    mp3_path = os.path.join(child_path, name)
                    # Only accept things that look like ordinary files.
                    if os.path.isfile(mp3_path):
                        mp3_names.append(name)
                        self._all_files.append(mp3_path)
                self._dirs[child_path] = mp3_names
                    
        self._all_albums = None
        self._all_tracks = None

    def files(self):
        return list(self._all_files)

    def scan_fast(self):
        """Quickly scan all MP3 files in the dropbox.

        Returns:
          A dict mapping relative file paths to either audio_file.AudioFile
          objects, or to None in the case of a corrupted or unreadable file.
        """
        # Note the use of ad-hoc relativization in the path.
        return dict(
            (mp3_path[len(self._path):], audio_file.scan_fast(mp3_path))
            for mp3_path in self._all_files)

    def albums(self):
        """Return unstandardized versions of all albums in the dropbox."""
        if self._all_albums is None:
            self._all_albums = []
            for path in sorted(self._dirs):
                for au in album.from_directory(path):
                    self._all_albums.append(au)
                    yield au
        else:
            for au in self._all_albums:
                yield au

    def tracks(self):
        """Do a fast scan and return all tracks in the dropbox."""
        if self._all_tracks is None:
            self._all_tracks = []
            for path in self._dirs:
                for alb in album.from_directory(path, fast=True):
                    self._all_tracks.extend(alb.all_au_files)
        return self._all_tracks
