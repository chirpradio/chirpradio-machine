"""Integration hooks for chirpradio."""

import getpass
import os
import sys
import json

from chirp.common import conf


# Add the Google App Engine SDK to sys.path.
_appengine_sdk_path = conf.GOOGLE_APPENGINE_SDK_PATH
if _appengine_sdk_path not in sys.path:
    sys.path.append(_appengine_sdk_path)
    import dev_appserver
    dev_appserver.fix_sys_path()    # otherwise fancy_urllib will not be found

from google.appengine.ext.remote_api import remote_api_stub

# Add the chirpradio tree to sys.path.
if conf.CHIRPRADIO_PATH not in sys.path:
    sys.path.append(conf.CHIRPRADIO_PATH)


# This is a very light-weight chirpradio file that we import immediately
# to check that everything is OK.
from auth import roles


def connect():
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = conf.GOOGLE_APPLICATION_CREDENTIALS

    with open(conf.GOOGLE_APPLICATION_CREDENTIALS) as fp:
        project_id = json.load(fp)['project_id']

    # You will get UnicodeDecodeError if servername is a unicode string.
    servername = str('%s.appspot.com' % project_id)
    remote_api_stub.ConfigureRemoteApiForOAuth(servername, '/_ah/remote_api')
