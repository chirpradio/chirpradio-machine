"""Crawler: recursively walk a file tree, returning info about found MP3s.
"""

import logging
import os
import sys
import mutagen.mp3

from chirp.library import audio_file


class Crawler(object):
    """Recursively walk a file tree, return info about found MP3s.

    Attributes:
      directories_seen: A set of all the names of directories which
        MP3s have been returned from.
      skipped_directories: A list of names of directories that were
        not crawled.
      skipped_files: A list of (file path, reason) tuples, one for each
        file that was not crawled for an interesting reason.
    """

    def __init__(self, fast=False, directory_filter=None):
        """Constructor.

        Args:
          fast: Only scan tags, do not analyze the audio data.
          directory_filter: An optional callable; if not None, it
            is applied to each directory name that is encountered,
            and the directory is only crawled if True is returned.
        """
        self._directory_filter = directory_filter
        self._fast = fast
        self._all_roots = []
        self._reset()
        self._current_dir = None

    def _reset(self):
        """Reset our per-crawl statistics."""
        self.directories_seen = set()
        self.skipped_directories = []
        self.skipped_files = []

    def current_directory(self):
        """Exposes the directory currently being crawled."""
        return self._current_dir

    def add_root(self, root_path):
        """Add a path to the list of roots to be crawled."""
        self._all_roots.append(root_path)
        
    def _remove_ignored_directories(self, this_current_dir, dirnames):
        # Filter out directories that should not be recursively crawled.
        dirnames_to_be_crawled = []
        for name in dirnames:
            if not name.startswith("."):
                dirnames_to_be_crawled.append(name)
            else:
                full_name = os.path.join(this_current_dir, name)
                self.skipped_directories.append(full_name)
        return sorted(dirnames_to_be_crawled)

    def __iter__(self):
        """Iterator that yields a sequence of crawled MP3s.

        Yields:
          An AudioFile object.
        """
        self._reset()

        yielded_size = 0
        for root_path in self._all_roots:
            for self._current_dir, dirnames, filenames in os.walk(root_path):

                # We do not recursively descend into these directoryies.
                dirnames[:] = self._remove_ignored_directories(
                    self._current_dir, dirnames)

                # If a directory filter has been specified, use it to know
                # when to silently skip any files in a single directory.
                if (self._directory_filter
                    and not self._directory_filter(self._current_dir)):
                    continue

                # Now walk across each file in this dir, yielding a
                # stream of AudioFile objects.
                for name in filenames:
                    full_path = os.path.join(self._current_dir, name)

                    # Skip files with the wrong sorts of names.  These are
                    # not logged.
                    if name.startswith("."):
                        continue

                    if not name.lower().endswith(".mp3"):
                        self.skipped_files.append(
                            (full_path, "Invalid filename"))
                        continue
                    
                    # Stat the file, and skip the files when that
                    # operation fails.
                    try:
                        stat_obj = os.stat(full_path)
                    except (IOError, OSError), ex:
                        self.skipped_files.append((full_path, str(ex)))
                        continue

                    try:
                        if self._fast:
                            au_file = audio_file.scan_fast(full_path)
                        else:
                            au_file = audio_file.scan(full_path)
                    except Exception, ex:
                        # TODO(trow): Here we should really only catch
                        # the exceptions we expect audio_file.scan and
                        # .scan_fast to raise.
                        self.skipped_files.append((full_path, str(ex)))
                        logging.error("Skipping file %s: %s",
                                      full_path, str(ex))
                        continue

                    if au_file is None:
                        self.skipped_files.append((full_path,
                                                   "Not an MP3 (No tags?)"))
                        continue

                    # Remember this directory, then yield the AudioFile.
                    self.directories_seen.add(self._current_dir)
                    yield au_file

            
