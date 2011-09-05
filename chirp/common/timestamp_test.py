#!/usr/bin/env python

import unittest
from chirp.common import timestamp


class TimestampTest(unittest.TestCase):

    def test_basics(self):
        now = timestamp.now()
        self.assertTrue(timestamp.is_valid(now))
        # Check that we can round-trip the timestamp produced by now()
        # through the human-readable format.
        human_readable = timestamp.get_human_readable(now)
        parsed = timestamp.parse_human_readable(human_readable)
        self.assertEqual(now, parsed)
        # Now check that a known example encodes correctly.
        ts = 1228080954
        self.assertTrue(timestamp.is_valid(ts))
        human_readable = timestamp.get_human_readable(ts)
        self.assertEqual("20081130-153554", human_readable)
        parsed = timestamp.parse_human_readable(human_readable)
        self.assertEqual(ts, parsed)

        # Make sure that calling timestamp.get_human_readable w/o an
        # argument returns a value for now.  We retry a few times just
        # in case we are very unlucky and call timestamp.now() for the
        # second time after the second has incremented.
        for _ in range(3):
            now_str = timestamp.get_human_readable(timestamp.now())
            no_arg_str = timestamp.get_human_readable()
            if no_arg_str == now_str:
                break
        else:
            self.assertTrue(False)

        # Check that is_valid will reject bad timestamps.
        self.assertFalse(timestamp.is_valid(-1))
        self.assertFalse(timestamp.is_valid(0))
        self.assertFalse(timestamp.is_valid(1000))  # The distant past
        self.assertFalse(timestamp.is_valid(1000000000000))  # The far future
        self.assertFalse(
            timestamp.is_valid(timestamp._MIN_REASONABLE_TIMESTAMP-1))
        self.assertFalse(
            timestamp.is_valid(timestamp._MAX_REASONABLE_TIMESTAMP+1))

        # Should raise ValueError on bad inputs.
        self.assertRaises(
            ValueError,
            timestamp.get_human_readable, 0)
        self.assertRaises(
            ValueError,
            timestamp.parse_human_readable, "malformed")
        self.assertRaises(
            ValueError,
            timestamp.parse_human_readable, "20081356-999999")

    def test_process_start_time(self):
        # Mostly just a smoke test.
        start_t_ms = timestamp.process_start_time_ms()
        age_ms = timestamp.process_age_ms()
        now = timestamp.now_ms()
        self.assertTrue(start_t_ms < now)
        self.assertTrue(((start_t_ms + age_ms) - now) < 10)

    def test_human_readable_durations(self):
        self.assertEqual("17.000 secs",
                         timestamp.get_human_readable_duration(17))
        self.assertEqual("1 min, 0.000 secs",
                         timestamp.get_human_readable_duration(60))
        self.assertEqual("1 min, 17.000 secs",
                         timestamp.get_human_readable_duration(77))
        self.assertEqual("2 mins, 0.000 secs",
                         timestamp.get_human_readable_duration(120))
        self.assertEqual("1 hr, 0.000 secs",
                         timestamp.get_human_readable_duration(3600))
        self.assertEqual("3 hrs, 25 mins, 45.000 secs",
                         timestamp.get_human_readable_duration(12345))
        self.assertEqual("1 day, 10 hrs, 17 mins, 36.000 secs",
                         timestamp.get_human_readable_duration(123456))


if __name__ == "__main__":
    unittest.main()
