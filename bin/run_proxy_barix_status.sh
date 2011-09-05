#!/bin/bash

# TODO(Kumar) convert to daemontools or something.

source ~/.virtualenvs/chirpradio-machine/bin/activate

# Keep running forever.
while [ true ]; do
    do_proxy_barix_status \
        >> ~/barix_status_proxy.log \
        2>&1 \
        < /dev/null
done
