#!/usr/bin/python
import sys
import signal
import logging
import threading

from flask import Flask, appcontext_tearing_down
from flask import json
from flask import request as freq
import zeroconf
import jsonpickle

import BurnerControl

app = Flask(__name__)
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)

thermLogger = logging.getLogger('Adafruit_MAX31855.MAX31855')
thermLogger.setLevel(logging.WARN)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
rootLogger.addHandler(ch)

fileLogger = logging.FileHandler("/tmp/server.log")
fileLogger.setLevel(logging.WARN)
fileLogger.setFormatter(formatter)
rootLogger.addHandler(fileLogger)

PORT = 8088


@app.route('/', methods=['GET'])
def sayHello():
    return json.dumps({'greeting': 'Howdy, World!!'})


@app.route('/status', methods=['GET'])
def status():
    global burner_control
    return jsonpickle.encode(burner_control.get_status())


@app.route('/mode', methods=['POST'])
def set_mode():
    global burner_control
    new_mode = BurnerControl.MODES[freq.args.get('mode')]
    burner_control.set_mode(new_mode)

    return jsonpickle.encode(burner_control.get_status())


@app.route('/setpoints', methods=['POST'])
def set_temps():
    global burner_control
    new_low = freq.args.get('low_temp')
    new_high = freq.args.get('high_temp')

    if new_low:
        burner_control.set_low(float(new_low))
    if new_high:
        burner_control.set_high(float(new_high))

    return jsonpickle.encode(burner_control.get_status())


class SigHandler:
    def __init__(self, burner_control):
        self.burner_control = burner_control

    def handle_ctrlc(self, signal, frame):
        logging.debug("processing signal")
        self.burner_control.stop()
        sys.exit(0)


def register_zeroconf():
    try:
        type = "_roboburn._tcp"
        info = zeroconf.ServiceInfo(name="pyburn-avahi._roboburn._tcp",
                                    type=type,
                                    port="%d" % PORT)
        zc = zeroconf.Zeroconf().register_service(info=info)
    except Exception as ex:
        logging.error("unable to register", exc_info=True)


def unregister_zeroconf():
    print "unregister"


global burner_control
burner_control = BurnerControl.BurnerControl(gpio_pin=17)
burner_thread = threading.Thread(target=burner_control.run)
burner_thread.start()

signal_handler = SigHandler(burner_control=burner_control)
signal.signal(signal.SIGINT, signal_handler.handle_ctrlc)
logging.warn("sighandler started.")

appcontext_tearing_down.connect(unregister_zeroconf, app)
register_zeroconf()

app.run(host='0.0.0.0', port=PORT, debug=True, use_reloader=False)
