"""Clean out the music dropbox after importing.
You must run this script as sudo for the correct permissions.
"""
import optparse
import os
import shutil

from chirp.common import conf


def main():
    op = optparse.OptionParser(usage='%prog [options]' + "\n\n" + __doc__)
    (options, args) = op.parse_args()
    if raw_input('Is everything imported? Are you sure you want to remove all '
                 'albums from the dropbox? Type y: ').lower().startswith('y'):
        for dir in os.listdir(conf.MUSIC_DROPBOX):
            if dir.startswith('.'):
                continue
            fn = os.path.join(conf.MUSIC_DROPBOX, dir)
            if not os.path.isdir(fn):
                continue
            shutil.rmtree(fn)
        print 'removed everything from %r' % conf.MUSIC_DROPBOX
    else:
        print 'nothing removed'


if __name__ == '__main__':
    main()
