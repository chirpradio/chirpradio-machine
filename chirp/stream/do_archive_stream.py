"""
Pulls an MP3 stream and archives it to disk.
"""

import sys
import time

from chirp.common import http_console_server
from chirp.common.conf import (ARCHIVER_PORT, STREAM_HOST, STREAM_PORT,
                               STREAM_PATH, ARCHIVES_DIR)

from chirp.stream import archiver
from chirp.stream import frame_splitter
from chirp.stream import http_puller
from chirp.stream import message
from chirp.stream import statistics


def run_pipeline():
    hp = http_puller.HttpPuller(STREAM_HOST, STREAM_PORT, STREAM_PATH)

    fs = frame_splitter.FrameSplitter(hp)

    fs_tee = message.MessageTee(fs, 2)
    fs_1, fs_2 = fs_tee.outputs

    arch = archiver.Archiver(fs_1)
    arch.ROOT_DIR = ARCHIVES_DIR
 
    stats = statistics.Statistics(fs_2)
    stats.export()

    all_objects = (hp, fs, fs_tee, arch, stats)
    for obj in all_objects:
        obj.loop_in_thread()

    sys.stderr.write(">>> pipeline running\n")

    # Wait indefinitely.
    try:
        while True: time.sleep(1 << 20)  # 2^20 seconds = ~12 days
    except KeyboardInterrupt:
        pass

    sys.stderr.write(">>> shutting down pipeline\n")
    hp.stop()
    for obj in all_objects:
        obj.wait()


def main():
    http_console_server.start(port=ARCHIVER_PORT)
    sys.stderr.write(">>> starting pipeline\n")
    try:
        run_pipeline()
    finally:
        http_console_server.stop()
    sys.stderr.write(">>> shutdown complete\n")


if __name__ == "__main__":
    main()
