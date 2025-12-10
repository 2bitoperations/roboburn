import logging
import os
import threading
import time
from collections import deque
import bisect

from flask import Flask, jsonify, render_template, request
from flask_assets import Bundle, Environment
from simple_pid import PID
from background_workers import temperature_worker, burner_control_worker

KEY_OIL_TEMP = "oil_temp"
KEY_TURKEY_TEMP = "turkey_temp"
KEY_TIME = "time"
KEY_RUNNING = "running"
KEY_TARGET_TEMP = "target_temp"
KEY_BURNER_ON = "burner_on"
KEY_PID_OUTPUT = "pid_output"
KEY_LAST_TOGGLE_TIME = "last_toggle_time"
# Two-stage burner additions
KEY_STAGE1_ON = "burner_stage1_on"
KEY_STAGE2_ON = "burner_stage2_on"
KEY_BURNER_REQUEST_STAGE = "burner_request_stage"  # 0,1,2
KEY_CONNECTED = "connected"
KEY_LAST_TOGGLE_TIME_STAGE1 = "last_toggle_time_stage1"
KEY_LAST_TOGGLE_TIME_STAGE2 = "last_toggle_time_stage2"

SECOND = 1
MINUTE = 60
HOUR = 60 * MINUTE
FIVE_MINUTES_MS = 5 * MINUTE * 1000
RAW_HISTORY_SECONDS = 60 * MINUTE  # 1 hour of 1s samples
LOG_MAX_LEN = 100
DEFAULT_TARGET_TEMP = 176.7  # 350°F in Celsius

# PID Configuration for 5gal oil & 250k BTU burner
# Kp: Lowered to reduce aggressive overcorrection with the high-power burner.
# Ki: Lowered to build the integral term slowly, preventing overshoot in a high thermal mass system.
# Kd: Increased significantly to act as a strong brake, anticipating and damping rapid temperature changes.
PID_KP = 5.0
PID_KI = 0.05
PID_KD = 20.0
PID_OUT_MIN, PID_OUT_MAX = 0, 100

# --- Logging Setup ---
log_messages = deque(maxlen=LOG_MAX_LEN)
log_lock = threading.Lock()


class DequeHandler(logging.Handler):
    def __init__(self, deque_instance):
        super().__init__()
        self.deque_instance = deque_instance
        self.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )

    def emit(self, record):
        log_entry = self.format(record)
        with log_lock:
            self.deque_instance.append(log_entry)


# --- Data Structures & PID Controller ---
temperature_data = {KEY_OIL_TEMP: 21.1, KEY_TURKEY_TEMP: 21.1}  # 70°F in Celsius
# Store raw temperature data with timestamps
temperature_history = deque(maxlen=RAW_HISTORY_SECONDS)

# Store decimated data for different time windows (name, duration_s, interval_s)
_DECIMATION_WINDOWS = [
    ("5min", 5 * MINUTE, 1 * SECOND),
    ("30min", 30 * MINUTE, 3 * SECOND),
    ("2hr", 2 * HOUR, 10 * SECOND),
    ("8hr", 8 * HOUR, 40 * SECOND),
]
_DECIMATED_RESPONSE_WINDOWS = [name for (name, _, _) in _DECIMATION_WINDOWS if name != "5min"]
decimated_history = {
    name: {"data": deque(maxlen=max(1, duration // interval)), "interval": interval}
    for name, duration, interval in _DECIMATION_WINDOWS
}

# Track the last time we added to each decimated history
decimated_last_update = {key: 0 for key in decimated_history}
data_lock = threading.Lock()

control_status = {
    KEY_RUNNING: False,
    KEY_TARGET_TEMP: DEFAULT_TARGET_TEMP,
    KEY_BURNER_ON: False,
    KEY_PID_OUTPUT: 0.0,
    KEY_LAST_TOGGLE_TIME: 0,
    # Two-stage burner state
    KEY_STAGE1_ON: False,
    KEY_STAGE2_ON: False,
    KEY_BURNER_REQUEST_STAGE: 0,
    KEY_CONNECTED: False,
    KEY_LAST_TOGGLE_TIME_STAGE1: 0,
    KEY_LAST_TOGGLE_TIME_STAGE2: 0,
}
control_lock = threading.Lock()

# Guard to ensure background threads start exactly once per process
threads_started = False
threads_lock = threading.Lock()

pid = PID(
    Kp=PID_KP,
    Ki=PID_KI,
    Kd=PID_KD,
    setpoint=control_status[KEY_TARGET_TEMP],
    output_limits=(PID_OUT_MIN, PID_OUT_MAX),
)


# --- Worker Threads ---



# --- Flask App ---
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure webassets
assets = Environment(app)

# Tell webassets where to output built files and their URL base
assets.directory = "static"
assets.url = app.static_url_path

# Add load paths so bundles can reference files relative to these roots
assets.append_path(os.path.join(app.root_path, "node_modules"))
assets.append_path(os.path.join(app.root_path, "static"))

with app.app_context():
    # Create bundles
    css_bundle = Bundle("bootstrap/dist/css/bootstrap.min.css", output="gen/packed.css")

    js_bundle = Bundle(
        "bootstrap/dist/js/bootstrap.bundle.min.js",
        "chart.js/dist/chart.umd.min.js",
        # Use the bundled adapter that includes date-fns to avoid missing dependency errors
        "chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js",
        "chartjs-plugin-annotation/dist/chartjs-plugin-annotation.min.js",
        output="gen/packed.js",
    )

    assets.register("css_all", css_bundle)
    assets.register("js_all", js_bundle)

handler = DequeHandler(log_messages)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)


def start_background_threads():
    """Start background workers once per process."""
    global threads_started
    with threads_lock:
        if threads_started:
            return
        temp_worker = threading.Thread(
            target=temperature_worker,
            args=(
                app.logger,
                temperature_data,
                temperature_history,
                decimated_history,
                decimated_last_update,
                data_lock,
                control_status,
                control_lock,
            ),
        )
        temp_worker.daemon = True
        temp_worker.start()

        burner_worker = threading.Thread(
            target=burner_control_worker,
            args=(
                app.logger,
                temperature_history,
                data_lock,
                control_status,
                control_lock,
                pid,
            ),
        )
        burner_worker.daemon = True
        burner_worker.start()

        threads_started = True
        app.logger.info("Background threads started.")


@app.before_request
def _ensure_threads_started():
    # Ensure background threads are started before handling any request.
    start_background_threads()


@app.route("/")
def index():
    app.logger.info("Main page loaded.")
    return render_template("index.html")


@app.route("/temperatures")
def get_temperatures():
    with data_lock:
        if temperature_history:
            return jsonify(temperature_history[-1])
        return jsonify({})


@app.route("/temperature_history")
def get_temperature_history():
    with data_lock:
        current_time = time.time()
        five_min_ago_ms = current_time * 1000 - FIVE_MINUTES_MS

        # Get recent high-resolution data
        recent_data = [entry for entry in temperature_history if entry[KEY_TIME] >= five_min_ago_ms]

        # Get decimated historical data
        historical_data = []
        for key in _DECIMATED_RESPONSE_WINDOWS:
            historical_data.extend(decimated_history[key]["data"])

        # Combine and sort all data
        all_data = recent_data + historical_data
        all_data.sort(key=lambda x: x[KEY_TIME])

        # Optional downsampling by requested count, evenly distributed across timeline
        req_count = request.args.get("count", type=int)
        if req_count and req_count > 0 and len(all_data) > req_count:
            times = [x[KEY_TIME] for x in all_data]
            t_min = times[0]
            t_max = times[-1]
            if t_max == t_min:
                sampled = [all_data[-1]]
            else:
                step = (t_max - t_min) / max(1, (req_count - 1))
                chosen_indices = []
                last_idx = -1
                for i in range(req_count):
                    target_t = t_min + i * step
                    idx = bisect.bisect_left(times, target_t)
                    if idx >= len(times):
                        idx = len(times) - 1
                    if idx > 0:
                        # choose closer between idx-1 and idx
                        if abs(times[idx] - target_t) >= abs(target_t - times[idx - 1]):
                            idx = idx - 1
                    if idx != last_idx:
                        chosen_indices.append(idx)
                        last_idx = idx
                sampled = [all_data[i] for i in chosen_indices]
            return jsonify(sampled)

        return jsonify(all_data)


@app.route("/status")
def get_status():
    with control_lock:
        return jsonify(control_status)


@app.route("/logs")
def get_logs():
    with log_lock:
        return jsonify(list(log_messages))


@app.route("/set_target_temp", methods=["POST"])
def set_target_temp():
    temp = request.json.get("temp")
    if temp is not None:
        with control_lock:
            control_status[KEY_TARGET_TEMP] = float(temp)
        app.logger.info(f"Target temperature set to: {temp}°F")
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid temperature"})


@app.route("/toggle_run_state", methods=["POST"])
def toggle_run_state():
    with control_lock:
        control_status[KEY_RUNNING] = not control_status[KEY_RUNNING]
        new_state = "RUNNING" if control_status[KEY_RUNNING] else "STOPPED"
    app.logger.info(f"System state changed to: {new_state}")
    return jsonify({"success": True, "running": control_status[KEY_RUNNING]})


if __name__ == "__main__":
    # When running directly, start threads immediately.
    start_background_threads()
    app.run(debug=True, host="0.0.0.0", use_reloader=False)
