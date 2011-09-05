#!/usr/bin/env python

# do_automount: Simple automated mounting and unmounting
#
# Attempts to mount all data drives in a tree where the mount point name
# is the drive's serial number.
#
# We only attempt to mount drives that have a single partition numbered "1".
# This has the nice property of excluding drives with standard Linux installs,
# since they will have swap partitions.
#
# If run with --unmount-all, all currently-mounted data drives will be
# unmounted.

import getopt
import os
import re
import subprocess
import sys

from chirp.common.conf import MOUNT_BY_HDSN_ROOT


NOT_MOUNTED_MARKER = "_NOT_MOUNTED"

HDPARM_BIN = "/sbin/hdparm"
MOUNT_BIN = "/bin/mount"
UMOUNT_BIN = "/bin/umount"


def get_all_partitions():
    """Return a list of all partitions mentioned in /proc/partitions."""
    proc_partitions = open('/proc/partitions').read()
    all_names = re.findall("sd[a-z][1-9]$", proc_partitions, re.MULTILINE)
    return ["/dev/" + name for name in all_names]


def get_serial_number(dev_name):
    """Get a hard drive's serial number by using hdparm."""
    hdparm_cmd = [HDPARM_BIN, "-I", dev_name]
    hdparm = subprocess.Popen(hdparm_cmd, stdout=subprocess.PIPE)
    ret_code = hdparm.wait()
    assert ret_code == 0
    match = re.search("Serial Number:\s+(.+)$",
                     hdparm.stdout.read(), re.MULTILINE)
    return match and  match.group(1)


def do_mount():
    """Mount all data drives."""
    sys.stderr.write("+++ Mounting CHIRP data drives\n")

    # Compute the list of partitions that are alone on a device.
    # These are the only ones we attempt to mount.
    all_partitions = get_all_partitions()
    has_other_parts = set(p[:-1] for p in all_partitions
                          if not p.endswith("1"))
    part1_only = [p for p in all_partitions
                  if p.endswith("1") and not p[:-1] in has_other_parts]

    for dev_name in part1_only:
        serial_num = get_serial_number(dev_name)
        assert serial_num

        mount_dir = os.path.join(MOUNT_BY_HDSN_ROOT, serial_num)
        not_mounted_fn = os.path.join(mount_dir, NOT_MOUNTED_MARKER)

        # If it isn't already there, create a new mount directory
        # containing a not-mounted marker file.
        if not os.path.exists(mount_dir):
            sys.stderr.write("Creating new mount directory %s\n" % mount_dir)
            os.makedirs(mount_dir)
            open(not_mounted_fn, "w").close()

        # If we can't see the not-mounted marker file, something is already
        # mounted at that directory.
        # TODO(trow): Check that the correct drive is mounted?
        if not os.path.exists(not_mounted_fn):
            sys.stderr.write("%s: already mounted\n" % dev_name)
            continue

        mount_cmd = [MOUNT_BIN, dev_name, mount_dir]
        ret_code = subprocess.call(mount_cmd)
        if ret_code:
            sys.stderr.write("%s: FAILED\n" % dev_name)
            continue
        sys.stderr.write("%s: mounted as %s\n" % (dev_name, mount_dir))

    sys.stderr.write("+++ Mounting CHIRP data drives: complete\n")


def do_unmount():
    """Unmount all data drives."""
    sys.stderr.write("+++ Unmounting CHIRP data drives\n")
    for serial_num in os.listdir(MOUNT_BY_HDSN_ROOT):
        mount_dir = os.path.join(MOUNT_BY_HDSN_ROOT, serial_num)
        umount_cmd = [UMOUNT_BIN, mount_dir]
        umount = subprocess.Popen(umount_cmd, stderr=subprocess.PIPE)
        ret_code = umount.wait()
        umount_stderr = umount.stderr.read()
        if ret_code:
            if "not mounted" in umount_stderr:
                sys.stderr.write("%s: not mounted\n" % mount_dir)
                continue
            sys.stderr.write("ERROR: Unmount of %s failed: %s\n" % (
                    mount_dir, umount_stderr))
            continue
        sys.stderr.write("%s: successfully unmounted\n" % mount_dir)
    sys.stderr.write("+++ Unmounting CHIRP data drives: complete\n")


def main():
    options, other_args = getopt.getopt(sys.argv[1:],
                                        "",
                                        ["unmount-all"])
    if "--unmount-all" in set(opt[0] for opt in options):
        do_unmount()
        return
    do_mount()


if __name__ == "__main__":
    main()

