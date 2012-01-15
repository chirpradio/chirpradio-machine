"""
Utility functions related to timestamps.
"""

import time


_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"
_PRETTY_FORMAT = "%c"

PROCESS_START_TIME = time.time()  # time of importing this file


def now():
    """Return an integer timestamp corresponding to the current time.

    Returns:
      An integer containing the number of seconds since the Unix epoch.
    """
    return int(time.time())


def now_ms():
    """Returns an integer millisecond timestamp for the current time.

    Returns:
      An integer containing the number of milliseconds since the Unix
      epoch.
    """
    return int(time.time() * 1000)


def process_start_time_ms():
    """Returns the process start-time as a millisecond timestamp."""
    return int(PROCESS_START_TIME * 1000)


def process_age_ms():
    """Returns the number of milliseconds the process has been running."""
    return int(1000 * (time.time() - PROCESS_START_TIME))


def get_human_readable(ts=None):
    """Convert an integral timestamp into a human-readable string.

    Args:
      ts: A timestamp, probably produced by calling now().  If omitted
      now() is called and the return value is used.
      
    Returns:
      A string that encodes the timestamp as a human-readable
      string.  The format of the string is:
      YYYYMMDD-HHMMSS

      The time is given in the local time zone.
    """
    if ts is None:
        ts = now()
    if not is_valid(ts):
        raise ValueError("Bad timestamp \"%s\"" % ts)
    return time.strftime(_TIMESTAMP_FORMAT, time.localtime(ts))


def get_human_readable_ms(ms_ts):
    """Convert a millisecond timestamp into a human-readable string."""
    ts = ms_ts / 1000
    if not is_valid(ts):
        raise ValueError("Bad milli-timestamp \"%s\"" % ms_ts)
    return "%s.%03d" % (get_human_readable(ts), ms_ts % 1000)


def get_pretty(ts=None):
    if ts is None:
        ts = now()
    if not is_valid(ts):
        raise ValueError("Bad timestamp \"%s\"" % ts)
    return time.strftime(_PRETTY_FORMAT, time.localtime(ts))


def get_pretty_ms(ms_ts):
    ts = int(ms_ts / 1000)
    if not is_valid(ts):
        raise ValueError("Bad milli-timestamp \"%s\"" % ms_ts)
    return time.strftime(_PRETTY_FORMAT, time.localtime(ts))    
    

def parse_human_readable(human_readable_str):
    """Convert the human-readable form of a timestamp into an integer.

    Args:
      human_readable_str: A string produced by a previous call to
        the get_human_readable function.
      
    Returns:
      An integer timestamp.
    """
    parsed = time.strptime(human_readable_str, _TIMESTAMP_FORMAT)
    return int(time.mktime(parsed))


# Nov 30th, 2008
_MIN_REASONABLE_TIMESTAMP = parse_human_readable("20081130-000000")

# Jan 19, 2038 <- end of the [Unix] world, Y2K38
_MAX_REASONABLE_TIMESTAMP = parse_human_readable("20380119-000000")

def is_valid(ts):
    """Check if a timestamp appears to be valid."""
    return (isinstance(ts, (int, long))
            and (_MIN_REASONABLE_TIMESTAMP < ts < _MAX_REASONABLE_TIMESTAMP))
            

_SECONDS_PER_MINUTE = 60
_SECONDS_PER_HOUR = 60 * _SECONDS_PER_MINUTE
_SECONDS_PER_DAY = 24 * _SECONDS_PER_HOUR

def get_human_readable_duration(duration_s):
    days = int(duration_s / _SECONDS_PER_DAY)
    duration_s %= _SECONDS_PER_DAY
    hours = int(duration_s / _SECONDS_PER_HOUR)
    duration_s %= _SECONDS_PER_HOUR
    minutes = int(duration_s / _SECONDS_PER_MINUTE)
    duration_s %= _SECONDS_PER_MINUTE

    def _pluralize(n, unit):
        if n > 1:
            return "%d %ss" % (n, unit)
        return "%d %s" % (n, unit)

    output = []
    if days: output.append(_pluralize(days, "day"))
    if hours: output.append(_pluralize(hours, "hr"))
    if minutes: output.append(_pluralize(minutes, "min"))
    output.append("%.3f secs" % duration_s)
    return ", ".join(output)


def get_human_readable_duration_ms(duration_ms):
    return get_human_readable_duration(duration_ms / 1000.0)
