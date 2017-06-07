#!/usr/bin/python
import logging
import signal
import socket
import sys
import threading

import jsonpickle
import zeroconf
from flask import Flask, appcontext_tearing_down
from flask import json
from flask import request as freq

import BurnerControl
from AddressFind import get_best_if_address

app = Flask(__name__)
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)

thermLogger = logging.getLogger('Adafruit_MAX31855.MAX31855')
thermLogger.setLevel(logging.WARN)

zeroconf_logger = zeroconf.log
zeroconf_logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
rootLogger.addHandler(ch)
zeroconf_logger.addHandler(ch)

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
    def __init__(self, local_burner_control, zeroconf):
        self.burner_control = local_burner_control
        self.zeroconf = zeroconf

    def handle_ctrlc(self, signal, frame):
        logging.debug("processing signal")
        self.zeroconf.unregister_all_services()
        self.zeroconf.close()
        self.burner_control.stop()
        sys.exit(0)


def register_zeroconfs():
    try:
        address_to_use = get_best_if_address()
        if address_to_use:
            logging.info("will use address %s for zc" % address_to_use)
            type = "_roboburn._tcp.local."
            info = zeroconf.ServiceInfo(name="roboburn._roboburn._tcp.local.",
                                        type_=type,
                                        address=socket.inet_aton(address_to_use),
                                        port=PORT,
                                        weight=1,
                                        priority=1,
                                        properties={'robo': 'burn'},
                                        server='roboburn.local.')
            zc.register_service(info=info, ttl=120, allow_name_change=True)
        else:
            logging.error("couldn't find ip to bind zeroconf to!")
    except Exception as ex:
        logging.error("unable to register", exc_info=True)


def unregister_zeroconfs(sender, **extra):
    print "unregistering zc sender %s extra %s" % (sender, extra)
    zc.unregister_all_services()
    register_zeroconfs()


zc = zeroconf.Zeroconf()
burner_control = BurnerControl.BurnerControl(gpio_pin=17)
burner_thread = threading.Thread(target=burner_control.run)
burner_thread.start()

signal_handler = SigHandler(local_burner_control=burner_control, zeroconf=zc)
signal.signal(signal.SIGINT, signal_handler.handle_ctrlc)
logging.warn("sighandler started.")

#appcontext_tearing_down.connect(unregister_zeroconfs, app)
register_zeroconfs()

app.run(host='0.0.0.0', port=PORT, debug=True, use_reloader=False)
