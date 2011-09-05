import os
import sys


# to import settings / settings_local:
sys.path.append(os.path.abspath(os.getcwd()))


try:
    from settings import *
    from settings_local import *
except ImportError, exc:
    sys.stderr.write(
            '** Trying to import settings.py or settings_local.py in %s\n'
            % os.getcwd())
    raise
