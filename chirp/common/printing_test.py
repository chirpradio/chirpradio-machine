import unittest

from chirp.common.printing import cprint


class TestCustomPrint(unittest.TestCase):

    def test_print_unicode(self):
        cprint(u'Ivan Krsti\u0107')

    def test_print_bytes(self):
        cprint(u'Ivan Krsti\u0107'.encode('utf8'))

    def test_print_numbers(self):
        cprint(1000)
