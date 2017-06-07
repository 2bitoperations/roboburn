import unittest

import AddressFind


class TestAddressFind(unittest.TestCase):
    def test_happy_path(self):
        best = AddressFind.get_best_if_address()