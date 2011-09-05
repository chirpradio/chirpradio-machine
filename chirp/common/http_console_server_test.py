#!/usr/bin/env python

import unittest
import urllib2

from chirp.common import http_console_server


class HttpConsoleServerTest(unittest.TestCase):

    def open(self, path):
        return urllib2.urlopen(http_console_server.url(path))

    def setUp(self):
        # Set a short timeout to speed up this test.
        http_console_server._HttpConsoleServer._TIMEOUT_S = 0.1

        # Start the server.
        http_console_server.start()

    def tearDown(self):
        # Stop the server.
        try:
            http_console_server.stop()
        except:
            # Showing the test failure is more important than this.
            import traceback
            traceback.print_exc()

        # Kumar: these are not 2.6 compatible (I think)...

        # Remember the /ok URL.
        # ok_url = http_console_server.url("/ok")

        # Since the server has stopped, we shouldn't be able to connect
        # to the socket.
        # self.assertRaises(IOError, lambda: urllib2.urlopen(ok_url).read())

    def test_basics(self):
        # Check that we can hit "/ok".
        f = self.open("/ok")
        self.assertEqual("ok", f.read())
        self.assertEqual("text/plain", f.info().type)

        # Smoke-test /sysinfo.
        f = self.open("/sysinfo")
        self.assertTrue("System Information" in f.read())

        # This should 404.
        try:
            self.open("/foo")
            self.assertTrue(False)
        except urllib2.URLError, ex:
            self.assertEqual(404, ex.code)

        # Now register a simple page handler and a POST-only handler.
        test_string = "This is not HTML"
        http_console_server.register("/foo", lambda x: test_string)
        post_only_string = "This is only fetchable via a POST"
        http_console_server.register("/bar", lambda x: post_only_string,
                                     require_post=True)

        # Re-registering the same path is not allowed.
        self.assertRaises(ValueError,
                          http_console_server.register,
                          "/foo", lambda x: test_string)

        # We should now be able to hit "/foo" and get back out test string.
        f = self.open("/foo")
        self.assertEqual(test_string, f.read())
        self.assertEqual("text/html", f.info().type)

        # Trying to get /bar with a GET will fail with a 405.
        try:
            self.open("/bar")
            self.assertTrue(False)
        except urllib2.URLError, ex:
            self.assertEqual(405, ex.code)

        # We should be able to fetch /bar if we force a POST.
        request = urllib2.Request(http_console_server.url("/bar"), "")
        self.assertEqual("POST", request.get_method())
        self.assertEqual(post_only_string, urllib2.urlopen(request).read())


if __name__ == "__main__":
    unittest.main()


