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

        int_temp = ( read_bytes[2] & 0x7F ) << 4
        int_temp = int_temp | (( read_bytes[3] & 0xF0 ) >> 4 )
        if read_bytes[2] & 0x80 == 1:
            int_temp = int_temp * -1
        int_temp = int_temp * 0.0625

        if read_bytes[1] & 0x1 == 1:
            fault = True
        else:
            fault = False

        # two "high bytes" format - V's are our temp bits:
        # SVVV VVVV VVVV VVRF
        probe_temp = ( ( read_bytes[0] & 0x7F ) << 6 ) | ( ( read_bytes[1] & 0xFC ) >> 2)
        if read_bytes[0] & 0x80 == 1:
            probe_temp = probe_temp * -1
        probe_temp = probe_temp * 0.25

        return Status(connected=connected,
                      gnd_short=gnd_short,
                      vcc_short=vcc_short,
                      int_temp=int_temp,
                      fault=fault,
                      probe_temp=probe_temp)
