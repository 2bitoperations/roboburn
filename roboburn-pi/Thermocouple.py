import logging
import time

class Status:
    def __init__(self, connected, gnd_short, vcc_short, int_temp, fault, probe_temp):
        self.connected = connected
        self.gnd_short = gnd_short
        self.vcc_short = vcc_short
        self.int_temp = int_temp
        self.fault = fault
        self.probe_temp = probe_temp
        self.time = time.time()

class Thermocouple:

    def __init__(self, spiDev, chip):
        self.logger = logging.getLogger("thermocouple-%s" % chip)
        self.spiDev = spiDev
        self.chip = chip

    def read(self):
        self.spiDev.open(0, self.chip)
        read_bytes = self.spiDev.readbytes(4)
        self.spiDev.close()

        out = ""
        for byte in read_bytes:
            out += "%x" % byte

        #self.logger.debug("%s" % out)

        if read_bytes[3] & 0x1 == 1:
            connected = False
        else:
            connected = True

        if read_bytes[3] & 0x2 == 1:
            gnd_short = True
        else:
            gnd_short = False

        if read_bytes[3] & 0x4 == 1:
            vcc_short = True
        else:
            vcc_short = False

        ref_temp_high_byte = ( read_bytes[2] & 0xFF ) << 4
        ref_temp_low_byte = ( read_bytes[3] & 0xF0 ) >> 4
        ref_temp_unscaled = Thermocouple.handle_twos_complement(ref_temp_high_byte | ref_temp_low_byte, 12)
        ref_temp = ref_temp_unscaled * 0.0625

        if read_bytes[1] & 0x1 == 1:
            fault = True
        else:
            fault = False

        probe_temp = self.convert_bytes_to_temp(read_bytes)

        return Status(connected=connected,
                      gnd_short=gnd_short,
                      vcc_short=vcc_short,
                      int_temp=ref_temp,
                      fault=fault,
                      probe_temp=probe_temp)

    @staticmethod
    def convert_bytes_to_temp(read_bytes):
        # two bytes, two's complement format
        # S = sign
        # v = temp bits
        # R = reserved, F = fault
        # SVVV VVVV VVVV VVRF
        bits_from_high_byte = read_bytes[0] & 0xFF
        bits_from_high_byte = bits_from_high_byte << 6
        bits_from_low_byte = read_bytes[1] & 0xFC
        bits_from_low_byte = bits_from_low_byte >> 2

        just_temp_bits = bits_from_high_byte | bits_from_low_byte
        unscaled_probe_temp = Thermocouple.handle_twos_complement(just_temp_bits, 14)
        probe_temp = unscaled_probe_temp * 0.25
        return probe_temp

    # shamelessly pulled from stackoverflow here:
    # http://stackoverflow.com/questions/1604464/twos-complement-in-python
    # thanks travc
    @staticmethod
    def handle_twos_complement(val, bits):
        if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
            val = val - (1 << bits)        # compute negative value
        return val                         # return positive value as is