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

class Status:
    def __init__(self, mode, on_temp, off_temp, burn, wait, temp_sense, history_sense, temp_food, history_food):
        self.mode = mode
        self.on_temp = on_temp
        self.off_temp = off_temp
        self.burn = burn
        self.wait = wait
        self.temp_sense = temp_sense
        self.history_sense = history_sense
        self.temp_food = temp_food
        self.history_food = history_food

class MODES(Enum):
    AUTO='AUTO'
    OFF='OFF'
    ON='ON'

class BurnerControl:
    def __init__(self, gpio_pin, low_temp=0, high_temp=100, samples=4096, polltime=.25, onoff_wait=6):
        self.shutdown_requested = False
        self.gpio_pin = gpio_pin
        self.low_temp = low_temp
        self.high_temp = high_temp
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

        self.sense_history = collections.deque([], maxlen=samples)
        self.food_history = collections.deque([], maxlen=samples)

        self.logger = logging.getLogger("burner")

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio_pin, GPIO.OUT)
        GPIO.output(self.gpio_pin, True)

    def get_status(self):
        return Status(mode=self.mode,
                      on_temp=self.low_temp,
                      off_temp=self.high_temp,
                      burn=self.burn,
                      wait=self.burn_deadband,
                      temp_sense=0,
                      history_sense=self.sense_history,
                      temp_food=0,
                      history_food=self.food_history)

    def get_burn_total_time(self):
        if self.burn:
            return self.burn_total_secs + time.time() - self.burn_start_time

    def burn(self, burn):
        if self.burn != burn:
            self.logger.info("state changing from %s to %s" %(self.burn, burn))

            if burn:
                self.burn_start_time = time.time()
            else:
                self.burn_stop_time = time.time()
                self.burn_total_secs += time.time() - self.burn_start_time

        self.burn = burn
        # RPI gpio is active low
        GPIO.output(self.gpio_pin, not burn)

    def set_mode(self, mode):
        self.logger.info("mode change from %s to %s" %(self.mode, mode))
        if self.mode != MODES.AUTO and mode == MODES.AUTO:
            self.logger.info("entering auto mode, setting times")
            self.burn_wait = False
            self.burn_deadband = False

        elif self.mode != MODES.OFF and mode == MODES.OFF:
            self.burn(False)

        elif self.mode != MODES.ON and mode == MODES.ON:
            self.burn(True)

        else:
            self.logger.error("unexpected state transition?")


        self.mode = mode

    def set_temps(self, low_temp, high_temp):
        self.low_temp = low_temp
        self.high_temp = high_temp

    def read_internal(self):
        with self.sense_lock:
            food_status = self.food.read()
            self.log_status(food_status, self.food_history)
            sense_status = self.sense.read()
            self.log_status(sense_status, self.sense_history)

    def log_status(self, sense, history):
        history.append(sense)

    def auto(self):
        # do we have any data?
        if len(self.sense_history) < 1:
            self.logger.warn("in auto, no sense data")
            return

        last_sense_temp = self.sense_history[-1].probe_temp
        # are we currently burning?
        if self.burn:
            # we are currently burning.
            # if the last sense temp is greater than our "high" temp, stop burning.
            if last_sense_temp >= self.high_temp:
                self.logger.info("hit high mark %s - currently %s" %(self.high_temp, last_sense_temp))
                self.burn_wait = True
                self.burn(False)

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
                        self.logger.info("hit low mark %s, wait time done, burning to %s - currently %s" %(self.low_temp, self.high_temp, last_sense_temp))
                        self.burn_wait = False
                        self.burn_deadband = False
                        self.burn(True)
                    else:
                        self.logger.debug("hit low mark %s, wait %s, waited %s - currently %s" %(self.low_temp, since_burn, self.onoff_wait, last_sense_temp))
                        self.burn_deadband = True
                else:
                    self.logger.debug("cooling to %s - currently %s" %(self.low_temp, last_sense_temp))
            else:
                # not in burn wait. need to burn?
                if last_sense_temp <= self.low_temp:
                    self.logger.info("hit low mark %s, burning to %s - currently %s" %(self.low_temp, self.high_temp, last_sense_temp))
                    self.burn(True)
                else:
                    self.logger.debug("cooling to %s - currently %s" %(self.low_temp, last_sense_temp))

    def stop(self):
        self.logger.info("stop requested")
        self.shutdown_requested = True

    def run(self):
        self.logger.info("entering run loop")
        while not self.shutdown_requested:
            self.read_internal()

            if self.mode == MODES.ON:
                self.burn(True)
            elif self.mode == MODES.AUTO:
                self.auto()
            else:
                self.burn(False)

            time.sleep(self.poll_time)

        self.logger.info("shutting down")

