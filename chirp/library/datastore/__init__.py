"""Modern Google Cloud Datastore implementation for chirpradio-machine.

This package replaces the legacy djdb module that relied on App Engine Remote API.
"""

from .connection import connect
from . import models
from . import search

__all__ = ['connect', 'models', 'search']
