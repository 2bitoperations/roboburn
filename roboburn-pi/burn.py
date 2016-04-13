#!/usr/bin/python
import socket
import sys
import signal
from flask import Flask, appcontext_tearing_down
from flask import json
from flask import request as freq
from zeroconf import Zeroconf
from netifaces import interfaces, ifaddresses, AF_INET
import time
import zeroconf
import BurnerControl
import logging
import jsonpickle
import threading

app = Flask(__name__)
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)

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
zeroconf_instance = Zeroconf()

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
        register_time = time.time()*1000
        for ifaceName in interfaces():
            for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':None}]):
                if i['addr'] is not None:
                    ip = i['addr']
                    hostname = socket.gethostbyaddr(ip)[0]
                    type = "_roboburn._tcp.local."
                    logging.info("registering service type %s on ip %s at host %s",
                                 type,
                                 ip,
                                 hostname)
                    service_info = zeroconf.ServiceInfo(type=type,
                                                        name="pyburn:%s.%s" % (PORT, type),
                                                        address=socket.inet_aton(i['addr']),
                                                        port=PORT,
                                                        weight=0,
                                                        priority=0,
                                                        properties={'version':'1', 'time':"%d" % register_time},
                                                        server=hostname
                                                        )
        zeroconf_instance.register_service(info=service_info, ttl=5)
    except Exception as ex:
        logging.error("unable to register", exc_info=True)

def unregister_zeroconf():
    zeroconf_instance.unregister_all_services()

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