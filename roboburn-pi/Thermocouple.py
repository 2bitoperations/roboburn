import logging
import time
from Adafruit_MAX31855 import MAX31855

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
        self.thermo = MAX31855.MAX31855(spi=spiDev)

    def read(self):
        state = self.thermo.readState()
        probe_temp = self.thermo.readLinearizedTempC()
        int_temp = self.thermo.readInternalC()

        return Status(connected=not state['openCircuit'],
                      gnd_short=state['shortGND'],
                      vcc_short=state['shortVCC'],
                      fault=state['fault'],
                      int_temp=int_temp,
                      probe_temp=probe_temp)