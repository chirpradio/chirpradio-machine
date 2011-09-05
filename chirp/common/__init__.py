import os

# The root directory of the chirp module, one that contains __init__, etc.
ROOT_DIR = os.path.join(os.path.dirname(__file__), '..')

# Sanity check:
for f in ('__init__.py', 'library'):
    assert os.path.exists(os.path.join(ROOT_DIR, f)), (
                'Is ROOT_DIR correct? Unexpected path: %s' % ROOT_DIR)
