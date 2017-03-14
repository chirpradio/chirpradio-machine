import os.path as op


# For importing files:
SAMBA = "/samba"
LIBRARY_PREFIX = op.join(SAMBA, "traktor/Library")
LIBRARY_DB = op.join(LIBRARY_PREFIX, "catalog.sqlite3_db")
LIBRARY_TMP_PREFIX = op.join(LIBRARY_PREFIX, "tmp")
MUSIC_DROPBOX = op.join(SAMBA,
                 "public/public/Departments/Music Dept/New Music Dropbox/")
# When an album needs fixing, it gets moved here:
MUSIC_DROPBOX_FIX = op.join(SAMBA, "public/Departments/Music Dept/Needs-Fixing")


# Path to checkout of App Engine code, from
# http://code.google.com/p/chirpradio/
CHIRPRADIO_PATH = op.expanduser('~/chirpradio')
CHIRPRADIO_HOST = 'chirpradio.appspot.com'
GOOGLE_APPENGINE_SDK_PATH = '/usr/local/google_appengine'


# Stream Archiver.
# Daemon that writes archives
ARCHIVER_PORT = 16000
# Top-level directory containing 2011, 2012, ...
ARCHIVES_DIR = '/archives'
# This is the IP address of the on-air studio's Barix box:
STREAM_HOST = "192.168.80.5"
# This port is reserved internally for the archiver to connect to:
STREAM_PORT = 12346
STREAM_PATH = "/broadcast"
# For monitoring the stream:
STREAM_PROXY_HOST = "192.168.80.10"
STREAM_PROXY_PORT = 17001


# Monitoring Barix
# The actual daemon that does monitoring:
BARIX_STATUS_HOST = "192.168.80.10"
BARIX_STATUS_PORT = 9111
# The way it connects to Barix:
BARIX_HOST = STREAM_HOST
BARIX_PORT = 80


# For auto-mounting:
MOUNT_BY_HDSN_ROOT = "/mnt/by_hdsn/"

# You can create a new service account key on the API manager credentials page:
# https://console.cloud.google.com/apis/credentials
# This service key is needed when using the Remote API:
# https://cloud.google.com/appengine/docs/python/tools/remoteapi
GOOGLE_APPLICATION_CREDENTIALS = op.expanduser('~/.chirpradio_service_account_key.json')

# This is the location where Traktor users expect to find the new NML file:
TRAKTOR_NML_FILE = '/mnt/disk_array/traktor/TraktorProRootDirectory/new-collection.nml'
