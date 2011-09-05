"""
A base class to handle the details of looping a method in a thread.
"""

import logging
import threading
import time


class Looper(object):
    """A base class to handle the details of looping a method in a thread."""

    # Keep a record of this many trapped exceptions.
    MAX_TRAPPED_EXCEPTIONS = 100

    def __init__(self):
        self._finished = threading.Event()
        self._looped_once = threading.Event()
        self._looping = False
        # Trapped exceptions are stored here.
        self.trapped_exceptions = []

    def _begin_looping(self):
        """Called before looping begins."""
        pass

    def _loop_once(self):
        """Perform a single iteration of the loop.

        This must be added by implementors of this class.
        """
        raise NotImplementedError

    def _done_looping(self):
        """Called when exiting the loop."""
        pass

    def _trap_exceptions(self, callable_to_wrap):
        """Execute a callable, trapping any raised exceptions.

        A list of the last MAX_TRAPPED_EXCEPTIONS exceptions is
        maintained.
        """
        try:
            callable_to_wrap()
        except Exception, err:
            logging.exception("Swallowed Exception in %s" % self)
            # We save the current exception as well as the timestamp
            # it occurred at.
            self.trapped_exceptions.append((time.time(), err))
            if len(self.trapped_exceptions) > self.MAX_TRAPPED_EXCEPTIONS:
                self.trapped_exceptions.pop(0)

    def loop(self):
        """Runs this object's loop.

        This may only be called once.  It returns when the loop is 
        terminated via a call to the stop() method.
        """
        assert not self._finished.isSet()
        assert not self._looping
        self._looping = True
        self._trap_exceptions(self._begin_looping)
        first = True
        while self._looping:
            self._trap_exceptions(self._loop_once)
            # If this is the first iteration of the loop, signal that
            # looping has begun.
            if first:
                self._looped_once.set()
                first = False
        # We've left the loop, so now it is time to call self._done_looping.
        self._trap_exceptions(self._done_looping)
        # Signal that the loop has finished.
        self._finished.set()

    def stop(self):
        """Stop looping."""
        self._looping = False

    def loop_in_thread(self):
        """Run the object's loop inside of a thread."""
        th = threading.Thread(target=self.loop, name="-%r" % self)
        th.start()

    def wait(self):
        """Wait for the object's loop to terminate."""
        self._finished.wait()

    def wait_until_looped_once(self):
        """Wait for at least one iteration of the loop to be processed.

        This is useful in unit tests.
        """
        self._looped_once.wait()
