
import unittest
from chirp.common import http
from chirp.stream import barix

class RemoveTagsTestCase(unittest.TestCase):

    def test_basic(self):
        self.assertEqual("foo bar",
                         barix._remove_tags("foo bar"))
        self.assertEqual("foo bar baz",
                         barix._remove_tags("foo <tag>bar</tag> baz"))


_TEST_STATUS_PAGE = """<html>
<head>
<meta http-equiv=refresh content="2; url=uistatusl.html">
</head>
<body><font face="Arial, Helvetica, sans-serif"><font size=2>
<p><br><font size=4><b>

<font color=#8F2635>SENDING</b></font></font><br><br>
<b>5610<br>
5422<br><br>
<img src=d2.gif width=28 height=12>&nbsp;<br><br><br>
<img src=d0.gif width=28 height=12>&nbsp;<br><br>
<img src=d0.gif width=28 height=12>&nbsp;<br><br>

        <!--
<img src=d1.gif width=28 height=12>&nbsp;<br>
        
<img src=d1.gif width=28 height=12>&nbsp;<br>
        
<img src=d1.gif width=28 height=12>&nbsp;<br>
        
<img src=d1.gif width=28 height=12>&nbsp;<br>
        
<img src=d1.gif width=28 height=12>&nbsp;<br>
        
<img src=d1.gif width=28 height=12>&nbsp;<br>
        
<img src=d1.gif width=28 height=12>&nbsp;<br>
        
<img src=d1.gif width=28 height=12>&nbsp;<br>
        
        -->
</body>
</html>
"""

_TEST_CLIENTS_PAGE = """<html><head><meta http-equiv=refresh content="2; url=clients.cgi"></head><body>
<h3>BRTP clients: 0</h3><pre></pre><h3>TCP connections</h3><pre>64.81.140.198:src port 80 :dst port 43624
216.235.91.36:src port 11111 :dst port 52770
192.168.80.10:src port 22222 :dst port 60320
10.0.99.98:src port 33333 :dst port 42911
</pre></body></html>
"""

def _mock_get_with_timeout(host, port, path, timeout_s):
    if path == "/clients.cgi":
        return _TEST_CLIENTS_PAGE
    if path == "/uistatusl.html":
        return _TEST_STATUS_PAGE
    assert False

# Monkey-patch in our mock of get_with_timeout.
http.get_with_timeout = _mock_get_with_timeout


class BarixTestCase(unittest.TestCase):

    def test_basic(self):
        barix_obj = barix.Barix("test.url.com", 666)
        barix_obj.ping()
        self.assertEqual("SENDING", barix_obj.status)
        self.assertEqual("5610", barix_obj.left_level)
        self.assertEqual("5422", barix_obj.right_level)
        print barix_obj.clients
        self.assertEqual(3, len(barix_obj.clients))
        self.assertEqual(("216.235.91.36", "52770"),
                         barix_obj.clients["11111"])
        self.assertEqual(("192.168.80.10", "60320"),
                         barix_obj.clients["22222"])
        self.assertEqual(("10.0.99.98", "42911"),
                         barix_obj.clients["33333"])


if __name__ == "__main__":
    unittest.main()
