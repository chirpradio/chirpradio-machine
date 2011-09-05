#!/usr/bin/env python

import unittest
import mutagen.id3

from chirp.library import order


class OrderTest(unittest.TestCase):

    def test_decode(self):
        test_cases = (("1", 1, None),
                      ("  6", 6, None),
                      ("006", 6, None),
                      ("1/2", 1, 2),
                      ("3 of 7", 3, 7),
                      ("03anything04", 3, 4))
        for text, order_num, max_num in test_cases:
            self.assertEqual((order_num, max_num), order.decode(text))
        # These should not be parseable.
        error_test_cases = ("", "xxx", "0", "-1", "0/3", "3/", "3/0", "6/5",
                            "-1/4", "2/-1", "2/-", "3-4", "3/0")
        for text in error_test_cases:
            self.assertRaises(order.BadOrderError, order.decode, text)

    def test_encode(self):
        test_cases = ((1, 3, "1/3"), (7, None, "7"))
        for order_num, total_num, expected_text in test_cases:
            self.assertEqual(expected_text, order.encode(order_num, total_num))
        error_test_cases = ((7, 5), (0, 3), (-1, 3), (4, 0), (4, -1))
        for order_num, total_num in error_test_cases:
            self.assertRaises(order.BadOrderError,
                              order.encode, order_num, total_num)

    def test_standardize_str(self):
        self.assertEqual("3", order.standardize_str(" 3   "))
        self.assertEqual("3/7", order.standardize_str("3 of 7"))

    def test_standardize(self):
        tag = mutagen.id3.TRCK(text=["3 of 7"])
        order_num, max_num = order.standardize(tag)
        self.assertEqual(["3/7"], tag.text)
        self.assertEqual(3, order_num)
        self.assertEqual(7, max_num)

    def test_is_archival(self):
        self.assertTrue(order.is_archival("3/7"))
        self.assertFalse(order.is_archival("bad"))
        self.assertFalse(order.is_archival("3"))
        self.assertFalse(order.is_archival("3 of 7"))
        self.assertFalse(order.is_archival("7/3"))
        self.assertFalse(order.is_archival("  3/7"))

    def test_verify_and_standardize_str_list(self):
        # Check the simplest valid case.
        self.assertEqual(["1/1"], order.verify_and_standardize_str_list(["1"]))
        # Check an already-standardized set.
        self.assertEqual(
            ["1/4", "3/4", "2/4", "4/4"],
            order.verify_and_standardize_str_list(
                ["1/4", "3/4", "2/4", "4/4"]))
        # Check strings without a max number.
        self.assertEqual(
            ["1/4", "3/4", "2/4", "4/4"],
            order.verify_and_standardize_str_list(["1", "3", "2", "4"]))
        # Check mixed formats.
        self.assertEqual(
            ["1/4", "3/4", "2/4", "4/4"],
            order.verify_and_standardize_str_list(["1", "3/4", "2", "4 of 4"]))
        # Check empty list.
        self.assertRaises(order.BadOrderError,
                          order.verify_and_standardize_str_list, [])
        # Check garbage in list.
        self.assertRaises(order.BadOrderError,
                          order.verify_and_standardize_str_list, ["xxx"])
        # Check treatment of gaps.
        self.assertRaises(order.BadOrderError,
                          order.verify_and_standardize_str_list,
                          ["1", "2", "4"])
        # Check bad max number.
        self.assertRaises(order.BadOrderError,
                          order.verify_and_standardize_str_list,
                          ["1/5", "3/5", "2/5", "4/5"])


if __name__ == "__main__":
    unittest.main()

