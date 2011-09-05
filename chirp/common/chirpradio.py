"""Integration hooks for chirpradio."""

import getpass
import os
import sys

from chirp.common import settings


# Add the Google App Engine SDK to sys.path.
_appengine_sdk_path = settings.GOOGLE_APPENGINE_SDK_PATH
if _appengine_sdk_path not in sys.path:
    sys.path.append(_appengine_sdk_path)
    sys.path.append(os.path.join(_appengine_sdk_path, "lib/yaml/lib"))
    sys.path.append(os.path.join(_appengine_sdk_path, "lib/fancy_urllib"))

from google.appengine.ext.remote_api import remote_api_stub

# Add the chirpradio tree to sys.path.
if settings.CHIRPRADIO_PATH not in sys.path:
    sys.path.append(settings.CHIRPRADIO_PATH)
    sys.path.append(os.path.join(settings.CHIRPRADIO_PATH, "django.zip"))

# This is a very light-weight chirpradio file that we import immediately
# to check that everything is OK.
from auth import roles


def _auth_func():
    if settings.CHIRPRADIO_AUTH:
        fields = settings.CHIRPRADIO_AUTH.strip().split()
        if len(fields) == 2:
            return fields
        sys.stderr.write("Malformed authorization read from %s\n"
                         % _chirpradio_auth)
    return raw_input("Username:"), getpass.getpass("Password:")


def connect(host=None):
    if host is None:
        host = settings.CHIRPRADIO_HOST
    remote_api_stub.ConfigureRemoteDatastore(
        "chirpradio", "/remote_api", _auth_func, host)


