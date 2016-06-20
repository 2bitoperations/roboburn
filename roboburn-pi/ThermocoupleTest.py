import unittest
from Thermocouple import Thermocouple


class ThermocoupleTest(unittest.TestCase):
    def testReallyLowTemp(self):
        self.assertEquals(0, Thermocouple.convert_bytes_to_temp([0x00, 0x00]))
        # 0110 0100 0000 0000
        self.assertEquals(1600.0, Thermocouple.convert_bytes_to_temp([0x64, 0x00]))
        # 0000 0110 0100 1100
        self.assertEquals(100.75, Thermocouple.convert_bytes_to_temp([0x06, 0x4c]))
        self.assertEquals(-0.25, Thermocouple.convert_bytes_to_temp([0xff, 0xff]))
        # 1111 1111 1111 0000
        self.assertEquals(-1.0, Thermocouple.convert_bytes_to_temp([0xff, 0xf0]))
        # 1111 0000 0110 0000
        self.assertEquals(-250.0, Thermocouple.convert_bytes_to_temp([0xf0, 0x60]))

