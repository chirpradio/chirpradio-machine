"""Database abstraction layer for the music library.

This API is designed to be extremely simple.  The only supported
operations are:

  * Create the database tables (Database.create_tables)
  * Walk across all all audio files (Database.get_all)
  * Get a list of all valid imports (Database.get_all_imports)
  * Get all audio files that were part of a particular import
    (Database.get_by_import)
  * Find a single audio file by it's fingerprint (Database.get_by_fingerprint)
  * Transactionally add N new audio files, grouped into a single import
    (Database.begin_add, Database.update)
  * Write a single audio file's updated ID3 tags into the database
    (Database.update)

Extending the functionality of this module to support other operations
is *strongly* discouraged.

This is the *only* code that should write to either the audio_files or
id3_tags tables.  Everyone and everything else should treat those
tables as read-only.
TODO(trow): This should be enforced by db permissions in our final prod
environment.
"""

import sqlite3

import mutagen.id3

from chirp.common import timestamp
from chirp.library import audio_file
from chirp.library import schema


def _insert(target, table_name, insert_tuple):
    """Shorthand for inserting a tuple of items into a table."""
    sql = "INSERT INTO %s VALUES (%s)" % (
        table_name,
        ",".join(["?"] * len(insert_tuple)))
    target.execute(sql, insert_tuple)


def _insert_tags(conn, fingerprint, timestamp, mutagen_id3):
    """Insert an audio file's ID3 tags into the database.
    
    Args:
      conn: The database connection.
      fingerprint: The audio file's fingerprint.
      timestamp: A timestamp associated with these tags.  When initially
        importing a file into the library, this should be equal to the
        import timestamp.
      mutagen_id3: A mutagen.id3.ID3 object containing the file's tags
    """
    for tag in mutagen_id3.itervalues():
        tag_tuple = schema.id3_tag_to_tuple(fingerprint, timestamp, tag)
        _insert(conn, "id3_tags", tag_tuple)


def _get_tags(conn, au_file, cutoff_timestamp):
    """Get the ID3 tags for a particular audio file.

    Args:
      conn: The database connection.
      au_file: The audio file these tags are for.  The fingerprint is read
        from this object in order to determine which ID3 tags to pull out
        of the database.  The tags that are found are stored into this
        object's mutagen_id3 attribute.
      cutoff_timestamp: Ignore any timestamps from after this timestamp.

    We always populate au_file.mutagen_id3 with the set of tags with the
    greatest possible timestamp.

    Returns:
      True if we found tags for this au_file, False otherwise.
    """
    sql = ("SELECT timestamp, mutagen_repr FROM id3_tags"
           " WHERE fingerprint=\"%s\"" % au_file.fingerprint)
    if cutoff_timestamp is not None:
        sql += " AND timestamp <= %d" % cutoff_timestamp
    # Get the tags out in decreasing order, so we always see the
    # greatest possible timestamp first.
    sql += " ORDER BY timestamp DESC"

    cursor = conn.execute(sql)
    au_file.mutagen_id3 = mutagen.id3.ID3()
    max_timestamp = None
    while True:
        item = cursor.fetchone()
        if item is None:
            break
        this_timestamp, this_repr = item
        # We only want to return tags from a single timestamp.
        if max_timestamp is None:
            max_timestamp = this_timestamp
        elif max_timestamp != this_timestamp:
            break
        tag = eval(this_repr, mutagen.id3.__dict__, {})
        au_file.mutagen_id3.add(tag)
    # max_timestamp is None if and only if we didn't find any
    # matching rows.
    return (max_timestamp is not None)


def _audio_file_generator(conn, sql):
    """Turns a SQL query into a generator of AudioFile objects."""
    cursor = conn.execute(sql)
    while True:
        au_file_tuple = cursor.fetchone()
        if au_file_tuple is None:
            return
        au_file = schema.tuple_to_audio_file(au_file_tuple)
        assert _get_tags(conn, au_file, None)
        yield au_file


class Database(object):
    """Abstract database access for the music library."""

    def __init__(self, name):
        """Constructor.

        Args:
          name: A string identifying the database to connect to.
        """
        self._name = name
        # All database reads use this shared connection.  Each transaction
        # writes via its own private connection.
        self._shared_conn = self._get_connection()

    def _get_connection(self):
        """Construct a new database connection."""
        return sqlite3.connect(self._name)

    def create_tables(self):
        """Create a new set of database tables.

        Returns:
          True if the operation succeeds, False otherwise.
        """
        conn = self._get_connection()
        try:
            conn.execute(schema.create_audio_files_table)
            conn.execute(schema.create_audio_files_index)
            conn.execute(schema.create_id3_tags_table)
            conn.execute(schema.create_id3_tags_index)
        except sqlite3.OperationalError, ex:
            return False
        return True

    def get_all(self):
        """Returns a generator over all audio files in the library.

        Audio files are returned in descending import timestamp order,
        grouped by album.
        """
        sql = ("SELECT * FROM audio_files"
               " ORDER BY import_timestamp desc, album_id")
        return _audio_file_generator(self._shared_conn, sql)

    def get_all_imports(self):
        """Returns all volume/import timestamp pairs."""
        sql = ("SELECT DISTINCT volume, import_timestamp FROM audio_files"
               " ORDER BY import_timestamp")
        cursor = self._shared_conn.execute(sql)
        while True:
            this_tuple = cursor.fetchone()
            if this_tuple is None:
                return
            yield (int(this_tuple[0]), int(this_tuple[1]))

    def get_by_import(self, vol, import_timestamp):
        """Returns all audio files associated with a given import."""
        sql = ("SELECT * FROM audio_files"
               " WHERE volume=\"%d\""
               " AND import_timestamp=\"%d\""
               " ORDER BY album_id") % (vol, import_timestamp)
        return _audio_file_generator(self._shared_conn, sql)

    def get_by_fingerprint(self, fingerprint):
        """Find an audio file by it's fingerprint.

        Args:
          fingerprint: The audio file's fingerprint.

        Returns:
          An AudioFile object, or None if there is no file with the
          specified fingerprint.
        """
        sql = ("SELECT * FROM audio_files "
               " WHERE fingerprint=\"%s\"" % fingerprint)
        for au_file in _audio_file_generator(self._shared_conn, sql):
            return au_file
        return None

    def begin_add(self, volume, import_timestamp):
        """Begin a new transaction for adding files to the database.

        Args:
          volume: The volume identifier for the import associated with the
            transaction.
          import_timestamp: The timestamp of the import associated with
            the transaction.

        Returns:
          An _AddTransaction object.
        """
        conn = self._get_connection()
        return _AddTransaction(volume, import_timestamp, conn)

    def update(self, au_file, timestamp):
        conn = self._get_connection()
        _insert_tags(conn, au_file.fingerprint, timestamp, au_file.mutagen_id3)
        conn.commit()


class _AddTransaction(object):
    """Encapsulates a database transaction."""

    def __init__(self, volume, import_timestamp, conn):
        self._volume = volume
        self._import_timestamp = import_timestamp
        self._conn = conn

    def add(self, au_file):
        """Add a new audio file to the transaction.

        Args:
          au_file: An AudioFile object to be added.  The object's
            volume and import_timestamp attributes must be equal to None,
            and will be set automatically.

        It is an error to call add() after either commit() or revert().
        """
        assert self._conn is not None
        # Die if au_file contains the wrong values.
        if au_file.volume is not None:
            assert au_file.volume == self._volume
        au_file.volume = self._volume
        if au_file.import_timestamp is not None:
            assert au_file.import_timestamp == self._import_timestamp
        au_file.import_timestamp = self._import_timestamp

        _insert(self._conn, "audio_files", schema.audio_file_to_tuple(au_file))
        _insert_tags(self._conn,
                     au_file.fingerprint, au_file.import_timestamp,
                     au_file.mutagen_id3)

    def commit(self):
        """Commit the transaction.

        This method may be called at most once.  It is an error to
        call commit() after calling revert().
        """
        assert self._conn is not None
        self._conn.commit()
        self._conn = None

    def revert(self):
        """Revert the transaction.

        This method may be called at most once.  It is an error to call
        revert() after calling commit().
        """
        assert self._conn is not None
        self._conn.rollback()
        self._conn = None
