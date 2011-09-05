
import sys
import time

from chirp.common import http_console_server
from chirp.common.conf import (STREAM_HOST, STREAM_PORT, STREAM_PATH,
                                   STREAM_PROXY_HOST, STREAM_PROXY_PORT)

from chirp.stream import frame_splitter
from chirp.stream import http_proxy
from chirp.stream import http_puller
from chirp.stream import logger
from chirp.stream import message
from chirp.stream import statistics


def main():
    http_console_server.start()

    hp = http_puller.HttpPuller(STREAM_HOST, STREAM_PORT, STREAM_PATH)

    hp_tee = message.MessageTee(hp, 2)
    hp_proxy, hp_fs = hp_tee.outputs

    proxy = http_proxy.HttpProxy(hp_proxy, STREAM_PROXY_HOST,
                                 STREAM_PROXY_PORT)
    fs = frame_splitter.FrameSplitter(hp_fs)

    fs_tee = message.MessageTee(fs, 2)
    fs_stats, fs_arch = fs_tee.outputs

    stats = statistics.Statistics(fs_stats)
    stats.export()

    # TODO(trow): Ultimately we'll put the archiver here.
    arch = logger.Logger(fs_arch)

    all_objects = (hp, hp_tee, proxy, fs, fs_tee, stats, arch)
    for obj in all_objects:
        obj.loop_in_thread()

    try:
        while True: time.sleep(1 << 20)  # 2^20 seconds = ~12 days
    except KeyboardInterrupt:
        pass

    sys.stderr.write(">>> stopping\n")
    hp.stop()
    for obj in all_objects:
        obj.wait()

    http_console_server.stop()
    sys.stderr.write(">>> shutdown complete\n")

if __name__ == "__main__":
    main()
