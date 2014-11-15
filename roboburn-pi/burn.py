#!/usr/bin/python
import sys
import signal
from flask import Flask
from flask import json
from flask import request as freq
import BurnerControl
import logging
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
fileLogger.setLevel(logging.INFO)
fileLogger.setFormatter(formatter)
rootLogger.addHandler(fileLogger)


@app.route('/', methods=['GET'])
def sayHello():
    return json.dumps({'greeting': 'Howdy, World!!'})

@app.route('/status', methods=['GET'])
def status():
    global burner_control
    return json.dumps(burner_control.get_status())

@app.route('/mode', methods=['POST'])
def set_mode():
    global burner_control
    new_mode = BurnerControl.MODES[json.loads(freq.data)['mode']]
    burner_control.set_mode(new_mode)

@app.route('/setpoints', methods=['POST'])
def set_temps():
    global burner_control
    new_temps = json.loads(freq.data)

    burner_control.set_temps(low_temp=float(new_temps['low_temp']), high_temp=float(new_temps['high_temp']))

class SigHandler:
    def __init__(self, burner_control):
        self.burner_control = burner_control

    def handle_ctrlc(self, signal, frame):
        self.burner_control.stop()
        sys.exit(0)

global burner_control
burner_control = BurnerControl.BurnerControl(gpio_pin=20)
burner_thread = threading.Thread(target=burner_control.run)
burner_thread.start()

signal_handler = SigHandler(burner_control=burner_control)
signal.signal(signal.SIGINT, signal_handler.handle_ctrlc)
logging.warn("sighandler started.")

app.run(host='0.0.0.0', port=8088, debug=True, use_reloader=False)