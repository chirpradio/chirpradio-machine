"""Remove an album from the dropbox when it has errors.
It will get moved into the Needs-Fixing directory.
You must run this script with sudo for the correct permissions.
"""
import optparse
import os

from chirp.common import conf


def main():
    op = optparse.OptionParser(usage='%prog [options] /path/to/dir/to/remove'
                                     + "\n\n" + __doc__)
    (options, args) = op.parse_args()
    if not len(args) == 1:
        op.error('incorrect args')
    dir = args[0]
    if dir.endswith('/'):
        dir = dir[0:-1]
    if not os.path.exists(dir):
        op.error('directory does not exist: %r; it must be an absolute path'
                 % dir)
    if not os.path.isdir(dir):
        op.error('path %r is not a directory' % dir)
    base = os.path.basename(dir)
    if not os.path.exists(conf.MUSIC_DROPBOX_FIX):
        op.error('the fixit dir %r does not exist; check your settings'
                 % conf.MUSIC_DROPBOX_FIX)
    dest = os.path.join(conf.MUSIC_DROPBOX_FIX, base)
    if os.path.exists(dest):
        op.error('This album %r has already been set aside! It needs to be '
                 'removed from the Needs-Fixing dir first' % dest)
    os.rename(dir, dest)
    os.system('chown -R musiclib "%s"' % dest)
    os.system('chgrp -R traktor "%s"' % dest)
    os.system('chmod -R 0775 "%s"' % dest)
    print 'move %r -> %r' % (dir, dest)


if __name__ == '__main__':
    main()
