"""Database abstraction layer for the music library.

This API is designed to be extremely simple.  The only supported
operations are:

  * Migrate the database tables (Database.auto_migrate, Database.migrate)
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

import re

from chirp.common import timestamp
from chirp.common.printing import cprint
from chirp.library import audio_file
from chirp.library import schema
from os.path import exists, join, basename, dirname
from shutil import copyfile

"""A string unlikely to appear in any values that is used to separate concatenated tags"""
TAGS_SEPARATOR = "^&*"


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
    for tag in mutagen_id3.values():
        tag_tuple = schema.id3_tag_to_tuple(fingerprint, timestamp, tag)
        _insert(conn, "id3_tags", tag_tuple)


'''
def _modify_tag(conn, fingerprint, frame_id: str, val: str) -> bool:
    Update a tag value of a given audio file into the database.

    Args:
      conn: The database connection.
      fingerprint: The audio file's fingerprint.
      frame_id: the frame that need to be modified
      val: the new value of the frame
    
    Nothing will change if the frame_id is not found.
    Unsure about whether to update the timestamp, so haven't implemented it yet.
    Do I need to change the original ID3 file?

    cursor = conn.cursor()
    sql = ("SELECT * FROM id3_tags"
           "WHERE fingerprint = ? AND frame_id = ?")
    cursor.execute(sql, (fingerprint, frame_id))
    result = cursor.fetchall()

    if not result:
        return False
    
    if len(result) >= 2:
        pass
        # there exists duplication inside 
    prevval: str = result[0][3]
    prevrep: str = result[0][4]
    newrep = re.sub(prevval, val, prevrep) # try to update the mutagenrepr

    sql = (
          "UPDATE id3_tags SET value = ? mutagen_repr = ?"
          "WHERE fingerprint = ? AND frame_id = ?")
    conn.execute(sql, (val, fingerprint, frame_id, newrep))
    conn.commit()
    cursor.close()
    return True
'''    
    




def _transform_tag_tuple_to_obj(this_repr, value):
    this_repr = this_repr.replace("data='", "data=b'")
    frame_id = this_repr[0:4]
    id3_class = getattr(mutagen.id3, frame_id)
    tag = ""
    if frame_id == "UFID":
        owner = re.search("owner=u[\'|\"](.+?)[\'|\"]", this_repr).group(1)
        data = b""
        if owner != "http://www.cddb.com/id3/taginfo1.html":
            data = re.search("data=b[\'|\"](.+?)[\'|\"]", this_repr).group(1).encode()
        tag = id3_class(owner=owner, data=data)


    elif frame_id == "TXXX":
        encoding = int(re.search("encoding=(.+?),", this_repr).group(1))
        desc = re.search("desc=u[\'|\"](.+?)[\'|\"]", this_repr).group(1)
        text = value
        tag = id3_class(encoding=encoding,desc=desc,text=text)
    
    else:
        encoding = int(re.search("encoding=(.+?),", this_repr).group(1))
        text = value
        tag = id3_class(encoding=encoding, text=text)
    
    return tag

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
    sql = ("SELECT timestamp, mutagen_repr, value FROM id3_tags"
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
        this_timestamp, this_repr, value = item
        # We only want to return tags from a single timestamp.
        if max_timestamp is None:
            max_timestamp = this_timestamp
        elif max_timestamp != this_timestamp:
            break

        tag = _transform_tag_tuple_to_obj(this_repr, value)
            
        au_file.mutagen_id3.add(tag)
    # max_timestamp is None if and only if we didn't find any
    # matching rows.
    return (max_timestamp is not None)

def _audio_file_with_tags_generator(conn, sql):
    """Executes a SQL Query that returns tuples of the format
    (volume, import_timestamp, fingerprint, album_id, sampling_rate_hz,
    bit_rate_kbps, channels, frame_count, frame_size, duration_ms,
    concatenated_tags_mutagen_repr, concatenated_tags_value)
    and returns a generator over the corresponding audio file objects."""
    cursor = conn.execute(sql)
    item = cursor.fetchone()
    while item is not None:
        au_file_components = item[:-2]
        tag_components = item[-2:]
        au_file = schema.tuple_to_audio_file(au_file_components)

        reprs = tag_components[0].split(TAGS_SEPARATOR)
        values = tag_components[1].split(TAGS_SEPARATOR)
        if len(reprs) != len(values):
            raise ValueError("Repr or value included the delimiter")

        au_file.mutagen_id3 = mutagen.id3.ID3()
        for (mutagen_repr, value) in zip(reprs, values):
            tag = _transform_tag_tuple_to_obj(mutagen_repr, value)
            au_file.mutagen_id3.add(tag)

        yield au_file
        item = cursor.fetchone()

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

    def __init__(self, name, auto_migrate=True):
        """Constructor.

        Args:
          name: A string identifying the database to connect to.
        """
        self._name = name
        # All database reads use this shared connection.  Each transaction
        # writes via its own private connection.
        self._shared_conn = self._get_connection()
        # Get the CHIRP database version.
        self._user_version = self._shared_conn.execute("PRAGMA user_version;").fetchone()[0]
        if auto_migrate: self.auto_migrate()

    def close(self):
        self = None

    def _get_connection(self):
        """Construct a new database connection."""
        return sqlite3.connect(self._name)

    def auto_migrate(self):
        """Determine whether the database schema is outdated.
        If so, migrate to the newest version. Otherwise, do nothing"""
        if self._user_version == 0:
            # If the database version is 0,
            # this is either a newly-created database or
            # an unmigrated (old) database.
            # Check if the CHIRP tables already exist; if so,
            # skip initial table creation.
            legacy_table_count = 0
            for table in schema.LEGACY_TABLES:
                cursor = self._shared_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='%s';" % table)
                if cursor.fetchone(): legacy_table_count += 1
            if legacy_table_count == len(schema.LEGACY_TABLES):
                self.migrate(0)
            else:
                # recreate original tables
                self.migrate(-1)
        # Otherwise, migrate only if the schema version is outdated.
        elif self._user_version != schema.LATEST_VERSION:
            self.migrate(self._user_version)

    def migrate(self, from_version):
        """Migrate the database schema from an old version
        to the newest version.

        Args:
          from_version: An integer specifying the current
          version of the database schema (PRAGMA user_version).

        Returns:
          True if the operation succeeds, False otherwise.
        """
        conn = self._get_connection()
        cprint("Migrating database from version %s to version %s" %
               (from_version, schema.LATEST_VERSION))
        # Backup old version, if applicable.
        if from_version != -1:
            if exists(self._name):
                cprint("Backing up old database...")
                copyfile(self._name, join(dirname(self._name),
                                          "OLD_VERSION_%s_%s" %
                                          (from_version,
                                           basename(self._name))))
        cprint("Running migration...")
        try:
            migrations = schema.MIGRATIONS[from_version + 1:]
            for migration in migrations:
                for query in migration: conn.execute(query)
        except sqlite3.OperationalError as ex:
            return False
        conn.execute("PRAGMA application_id = %s;" % schema.APPLICATION_ID)
        conn.execute("PRAGMA user_version = %s;" % schema.LATEST_VERSION)
        self._user_version = schema.LATEST_VERSION
        conn.commit()
        cprint("Migrated successfully.")
        return True

    def get_all(self):
        """Returns a generator over all audio files in the library.

        Audio files are returned in descending import timestamp order,
        grouped by album.
        """
        sql = ("SELECT * FROM audio_files"
               " ORDER BY import_timestamp desc, album_id")
        return _audio_file_generator(self._shared_conn, sql)

    def get_since(self, since_timestamp):
        """Returns a generator over all audio file in the library
        that were last modified since the given timestamp.

        Audio files are returned in descending import timestamp order,
        grouped by album.
        """
        sql = ('SELECT "volume", "import_timestamp", "fingerprint", "album_id",'
               '"sampling_rate_hz", "bit_rate_kbps", "channels", "frame_count",'
               '"frame_size", "duration_ms" FROM audio_files NATURAL JOIN'
               ' last_modified WHERE modified_timestamp > %d'
               ' ORDER BY import_timestamp desc, album_id;' % since_timestamp)
        return _audio_file_generator(self._shared_conn, sql)
    
    def get_all_less_queries(self):
        """Same behavior as get_all.

        This version is a bit faster, but raises a ValueError if
        one of the values contains TAGS_SEPARATOR"""
        sql = ("WITH concat_tags AS ("
                    "SELECT fingerprint, timestamp, "
                        f"GROUP_CONCAT(mutagen_repr, '{TAGS_SEPARATOR}') AS concat_reprs, "
                        f"GROUP_CONCAT(value, '{TAGS_SEPARATOR}') AS concat_vals "
                    "FROM id3_tags "
                    "GROUP BY fingerprint, timestamp "
                ") "
                "SELECT * FROM audio_files "
                "NATURAL JOIN ("
                    "SELECT fingerprint, concat_reprs, concat_vals "
                    "FROM concat_tags AS a "
                    "WHERE a.timestamp = ("
                        "SELECT MAX(timestamp) "
                        "FROM concat_tags AS b "
                        "WHERE a.fingerprint = b.fingerprint"
                    ")"
                ") "
                "ORDER BY import_timestamp DESC, album_id")
        return _audio_file_with_tags_generator(self._shared_conn, sql)
    
    def get_since_less_queries(self, since_timestamp):
        """Same behavior as get_since.

        This version is a bit faster, but raises a ValueError if
        one of the values contains TAGS_SEPARATOR"""
        sql = ("WITH concat_tags AS ("
                    "SELECT fingerprint, timestamp, "
                        f"GROUP_CONCAT(mutagen_repr, '{TAGS_SEPARATOR}') AS concat_reprs, "
                        f"GROUP_CONCAT(value, '{TAGS_SEPARATOR}') AS concat_vals "
                    "FROM id3_tags "
                    "GROUP BY fingerprint, timestamp "
                ") "
                "SELECT volume, import_timestamp, fingerprint, album_id, "
                    "sampling_rate_hz, bit_rate_kbps, channels, frame_count, "
                    "frame_size, duration_ms, concat_reprs, concat_vals "
                "FROM audio_files "
                "NATURAL JOIN last_modified "
                "NATURAL JOIN ("
                    "SELECT fingerprint, concat_reprs, concat_vals "
                    "FROM concat_tags AS a "
                    "WHERE a.timestamp = ("
                        "SELECT MAX(timestamp) "
                        "FROM concat_tags AS b "
                        "WHERE a.fingerprint = b.fingerprint"
                    ")"
                ") "
                f"WHERE modified_timestamp > {since_timestamp} "
                "ORDER BY import_timestamp DESC, album_id")
        return _audio_file_with_tags_generator(self._shared_conn, sql)

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


    def _modify_tag(self, fingerprint, frame_id: str, val: str) -> bool:
      '''
      Update a tag value of a given audio file into the database.

      Args:
        conn: The database connection.
        fingerprint: The audio file's fingerprint.
        frame_id: the frame that need to be modified
        val: the new value of the frame
      
      Nothing will change if the frame_id is not found.
      Unsure about whether to update the timestamp, so haven't implemented it yet.
      Do I need to change the original ID3 file?
      '''
      conn = self._get_connection()
      cursor = conn.cursor()
      sql = ("SELECT * FROM id3_tags"
            "WHERE fingerprint = ? AND frame_id = ?")
      cursor.execute(sql, (fingerprint, frame_id))
      result = cursor.fetchall()

      if not result:
          return False
      
      if len(result) >= 2:
          pass
          # there exists duplication inside 
      prevval: str = result[0][3]
      prevrep: str = result[0][4]
      newrep = re.sub(prevval, val, prevrep) # try to update the mutagenrepr

      sql = (
            "UPDATE id3_tags SET value = ? mutagen_repr = ?"
            "WHERE fingerprint = ? AND frame_id = ?")
      conn.execute(sql, (val, fingerprint, frame_id, newrep))
      conn.commit()
      cursor.close()
      return True



    def _extract_fingerprint(self, title: str, artist: str) -> list[str]:
        '''
        Extract a list of fingerprints that matches the user's input of title and artist.

        Args:
            title: User input of the song title.
            artist: User input of the artist.

        Return a list of fingerprints in the database that matches the user's
        input of title and artist.
        '''
        fingerprints: list[str] = []
        conn = self._get_connection()
        cursor = conn.cursor()
        sql = ("SELECT  a.fingerprint, b.fingerprint "
                "FROM id3_tags a "
                "JOIN id3_tags  b ON a.fingerprint = b.fingerprint "
                "WHERE a.frame_id = 'TIT2' AND a.value = ? "
                "AND b.frame_id = 'TPE1' AND b.value = ? ;")
        cursor.execute(sql, (title, artist))

        result = cursor.fetchall()
        for row in result:
            fingerprints.append(row[0])

        cursor.close()
        return fingerprints


    def _fingerprint_display(self, fingerprint) -> dict:
        '''
        Given a fingerprint, display important information about the Mutagen
        information.
        We include information about: TIT2, TALB (album title), TRCK (track
        number in set), TLEN (length of audio in ms), TPE1 (lead artist),
        TDRC (Recording Time), TFLT (file type).

        Args:
            fingerprint: a fingerprint for a file

        Return a list of important characterstics of the file. This feature is
        used when there are multiple entries corresponding to the same title
        and artist, and the web interface needs to print out information
        about each entry, based on the fingerprint.
        '''
        songinfo: dict[str, str | None] = {}
        idframesinfo: list[str] = ['TIT2', 'TPE1', 'TALB', 'TRCK', 'TDRC', 
                                   'TLEN', 'TFLT']
        conn = self._get_connection()
        cursor = conn.cursor()

        for frame_id in idframesinfo:
            sql = ("SELECT value FROM id3_tags "
                "where fingerprint = ? AND frame_id = ?")
            cursor.execute(sql, (fingerprint, frame_id))
            result = cursor.fetchall()
            if not result:
                songinfo[frame_id] = None
            else:
                songinfo[frame_id] = result[0]
        cursor.close()
        conn.close()

        return songinfo








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
        _insert(self._conn, "last_modified",
                schema.audio_file_to_last_modified(au_file))
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
        self._conn.close()
        self._conn = None

    def revert(self):
        """Revert the transaction.

        This method may be called at most once.  It is an error to call
        revert() after calling commit().
        """
        assert self._conn is not None
        self._conn.rollback()
        self._conn.close()
        self._conn = None
