#!/usr/bin/python
# sudo pip install enum34
from enum import Enum
import Thermocouple
import spidev
import logging
import time
from threading import RLock
import RPi.GPIO as GPIO
import collections
import jsonpickle
import datetime

class Status:
    def __init__(self, mode, low_temp, high_temp, burn, wait, temp_sense, history_sense, temp_food, history_food):
        self.mode = mode.name
        self.low_temp = low_temp
        self.high_temp = high_temp
        self.burn = burn
        self.wait = wait
        self.temp_sense = temp_sense
        self.history_sense = self.transform_deque_to_interleaved_list(history_sense)
        self.temp_food = temp_food
        self.history_food = self.transform_deque_to_interleaved_list(history_food)

    def transform_deque_to_interleaved_list(self, input):
        out = dict()
        for v in list(input):
            if v and not v.fault:
                out[v.time] = v.probe_temp

        return out

class MODES(Enum):
    AUTO='AUTO'
    OFF='OFF'
    ON='ON'

class BurnerControl:
    def __init__(self, gpio_pin, low_temp=0, high_temp=100, history_samples=256, history_time=datetime.timedelta(minutes=5).total_seconds(), polltime=.25, onoff_wait=6):
        self.shutdown_requested = False
        self.gpio_pin = gpio_pin
        self.low_temp = low_temp
        self.high_temp = high_temp
        self.history_time = datetime.timedelta(seconds=history_time)
        self.history_samples = history_samples
        self.last_history_time = 0
        self.burn = False
        self.burn_start_time = 0
        self.burn_stop_time = 0
        self.burn_wait = False
        self.burn_deadband = False
        self.burn_total_secs = 0
        self.mode = MODES.OFF
        self.mode_time = time.time()
        self.poll_time = polltime
        self.onoff_wait = onoff_wait
        self.sense_lock = RLock()

        spi = spidev.SpiDev()

        self.sense = Thermocouple.Thermocouple(spiDev=spi, chip=0)
        self.food = Thermocouple.Thermocouple(spiDev=spi, chip=1)

        self.sense_history = collections.deque([], maxlen=history_samples)
        self.sense_last = None
        self.food_history = collections.deque([], maxlen=history_samples)
        self.food_last = None

        self.logger = logging.getLogger("burner")

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio_pin, GPIO.OUT)
        GPIO.output(self.gpio_pin, True)

    def get_status(self):
        return Status(mode=self.mode,
                      low_temp=self.low_temp,
                      high_temp=self.high_temp,
                      burn=self.burn,
                      wait=self.burn_deadband,
                      temp_sense=self.sense_last,
                      history_sense=self.sense_history,
                      temp_food=self.food_last,
                      history_food=self.food_history)

    def get_burn_total_time(self):
        if self.burn:
            return self.burn_total_secs + time.time() - self.burn_start_time

    def set_burn(self, burn):
        if self.burn != burn:
            self.logger.warn("state changing from %s to %s" %(self.burn, burn))

            if burn:
                self.burn_start_time = time.time()
            else:
                self.burn_stop_time = time.time()
                self.burn_total_secs += time.time() - self.burn_start_time

        self.burn = burn
        # RPI gpio is active low
        GPIO.output(self.gpio_pin, not burn)

    def set_mode(self, mode):
        self.logger.warn("mode change from %s to %s" %(self.mode, mode))
        if self.mode != MODES.AUTO and mode == MODES.AUTO:
            self.logger.warn("entering auto mode, setting times")
            self.burn_wait = False
            self.burn_deadband = False

        elif self.mode != MODES.OFF and mode == MODES.OFF:
            self.set_burn(False)

        elif self.mode != MODES.ON and mode == MODES.ON:
            self.set_burn(True)

        else:
            self.logger.error("unexpected state transition?")


        self.mode = mode

    def set_low(self, low_temp):
        self.low_temp = low_temp

    def set_high(self, high_temp):
        self.high_temp = high_temp

    def set_temps(self, low_temp, high_temp):
        self.low_temp = low_temp
        self.high_temp = high_temp

    def read_internal(self):
        with self.sense_lock:
            self.food_last = self.food.read()
            self.sense_last = self.sense.read()

            # has it been enough time since our last log?
            if time.time() - self.last_history_time > (self.history_time.total_seconds() / self.history_samples):
                self.log_status(name="food", status=self.food_last, history=self.food_history)
                self.log_status(name="sense", status=self.sense_last, history=self.sense_history)
                self.last_history_time = time.time()

    def log_status(self, name, status, history):
            self.logger.debug("%s-%s" % (name, jsonpickle.encode(status)))
            history.append(status)

    def auto(self):
        # do we have any data?
        if not self.sense_last:
            self.logger.warn("in auto, no sense data")
            return

        if self.sense_last.fault:
            self.logger.warn("last read was fault")
            return

        if self.high_temp <= self.low_temp:
            self.logger.warn("high temp %s is less than equal to %s - shuttin' er down." % (self.high_temp, self.low_temp))
            self.set_burn(False)
            return

        last_sense_temp = self.sense_last.probe_temp

        # are we currently burning?
        if self.burn:
            # we are currently burning.
            # if the last sense temp is greater than our "high" temp, stop burning.
            if last_sense_temp >= self.high_temp:
                self.logger.warn("hit high mark %s - currently %s" %(self.high_temp, last_sense_temp))
                self.burn_wait = True
                self.set_burn(False)

            # we haven't hit our high burn mark.
            else:
                self.logger.debug("burning to %s - currently %s" %(self.high_temp, last_sense_temp))

        else:
            # not currently burning. are we in wait mode?
            if self.burn_wait:
                # ok in wait mode. low water mark?
                if last_sense_temp <= self.low_temp:
                    # has it been enough time since our last burn?
                    since_burn = time.time() - self.burn_stop_time
                    if since_burn >= self.onoff_wait:
                        self.logger.warn("hit low mark %s, wait time done, burning to %s - currently %s" %(self.low_temp, self.high_temp, last_sense_temp))
                        self.burn_wait = False
                        self.burn_deadband = False
                        self.set_burn(True)
                    else:
                        self.logger.debug("hit low mark %s, wait %s, waited %s - currently %s" %(self.low_temp, since_burn, self.onoff_wait, last_sense_temp))
                        self.burn_deadband = True
                else:
                    self.logger.debug("cooling to %s - currently %s" %(self.low_temp, last_sense_temp))
            else:
                # not in burn wait. need to burn?
                if last_sense_temp <= self.low_temp:
                    self.logger.warn("hit low mark %s, burning to %s - currently %s" %(self.low_temp, self.high_temp, last_sense_temp))
                    self.set_burn(True)
                else:
                    self.logger.debug("cooling to %s - currently %s" %(self.low_temp, last_sense_temp))

    def stop(self):
        self.logger.warn("stop requested")
        self.shutdown_requested = True

    def run(self):
        self.logger.warn("entering run loop")
        while not self.shutdown_requested:
            self.read_internal()

            if self.mode == MODES.ON:
                self.set_burn(True)
            elif self.mode == MODES.AUTO:
                self.auto()
            else:
                self.set_burn(False)

            time.sleep(self.poll_time)

        self.logger.warn("shutting down")

