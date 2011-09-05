#!/bin/bash

# TODO(Kumar) convert to daemontools or something.

source ~/.virtualenvs/chirpradio-machine/bin/activate

# Keep running forever.
while [ true ]; do
    do_archive_stream \
        >> ~/archiver.log \
        2>&1 \
        < /dev/null
done
