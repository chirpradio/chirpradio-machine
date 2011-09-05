
import time
import unittest
from chirp.stream import looper


class MockLooper(looper.Looper):

    # How many times _loop_once() has been called.
    loop_count = 0

    # Set to true when _begin_looping() has been called.
    begin_looping_called = False

    # Set to true when _done_looping() has been called.
    done_looping_called = False

    # If true, always raise an exception when _loop_once() or _done_looping()
    # is called.
    raise_exception = False

    def _begin_looping(self):
        self.begin_looping_called = True
        if self.raise_exception:
            raise ValueError("Test of exception handling for _begin_looping")

    def _loop_once(self):
        self.loop_count += 1
        if self.raise_exception:
            raise ValueError("Test of exception handling for _loop_once")

    def _done_looping(self):
        self.done_looping_called = True
        if self.raise_exception:
            raise ValueError("Test of exception handling for _done_looping")


class LooperTestCase(unittest.TestCase):

    def test_basic(self):
        # Make sure we can spin up a looper in a thread, then stop it
        # and wait for it to terminate.
        lpr = MockLooper()
        lpr.loop_in_thread()
        lpr.wait_until_looped_once()
        lpr.stop()
        lpr.wait()
        # Make sure the loop actually ran.
        self.assertTrue(lpr.loop_count > 0)
        # Make sure the begin and done hooks were called.
        self.assertTrue(lpr.begin_looping_called)
        self.assertTrue(lpr.done_looping_called)

    def test_exception_handling(self):
        # Test that exceptions are managed properly.
        lpr = MockLooper()
        lpr.raise_exception = True
        start_t = time.time()
        lpr.loop_in_thread()
        lpr.wait_until_looped_once()
        lpr.stop()
        lpr.wait()
        end_t = time.time()

        # Check that the loop ran as expected.
        self.assertTrue(lpr.loop_count > 0)
        self.assertTrue(lpr.begin_looping_called)
        self.assertTrue(lpr.done_looping_called)
        # Check that we successfully trapped some exceptions.
        self.assertTrue(len(lpr.trapped_exceptions) > 0)
        # Check that the trapped exceptions have the correct type
        # and have sane timestamps.
        for when, what in lpr.trapped_exceptions:
            self.assertTrue(start_t <= when and when <= end_t)
            self.assertTrue(isinstance(what, ValueError))


if __name__ == "__main__":
    unittest.main()
