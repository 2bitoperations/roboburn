import logging
import os
import threading
import time
from collections import deque

from flask import Flask, jsonify, render_template, request
from flask_assets import Bundle, Environment
from simple_pid import PID
from background_workers import temperature_worker, burner_control_worker

# --- Logging Setup ---
log_messages = deque(maxlen=100)
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
temperature_data = {"oil_temp": 70.0, "turkey_temp": 70.0}
# Store raw temperature data with timestamps
temperature_history = deque(
    maxlen=3600
)  # Increased size to store more raw data before decimation

# Store decimated data for different time windows
decimated_history = {
    "5min": {"data": deque(maxlen=300), "interval": 1},  # 5 minutes at 1s resolution
    "30min": {"data": deque(maxlen=500), "interval": 3},  # 25 minutes at 3s resolution
    "2hr": {"data": deque(maxlen=600), "interval": 10},  # 1.7 hours at 10s resolution
    "8hr": {"data": deque(maxlen=720), "interval": 40},  # 8 hours at 40s resolution
}

# Track the last time we added to each decimated history
decimated_last_update = {key: 0 for key in decimated_history}
data_lock = threading.Lock()

control_status = {
    "running": False,
    "target_temp": 350.0,
    "burner_on": False,
    "pid_output": 0.0,
    "last_toggle_time": 0,
}
control_lock = threading.Lock()

# Guard to ensure background threads start exactly once per process
threads_started = False
threads_lock = threading.Lock()

# PID Configuration for 5gal oil & 250k BTU burner
# Kp: Lowered to reduce aggressive overcorrection with the high-power burner.
# Ki: Lowered to build the integral term slowly, preventing overshoot in a high thermal mass system.
# Kd: Increased significantly to act as a strong brake, anticipating and damping rapid temperature changes.
pid = PID(
    Kp=5.0,
    Ki=0.05,
    Kd=20.0,
    setpoint=control_status["target_temp"],
    output_limits=(0, 100),
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
        five_min_ago = (current_time - 300) * 1000  # 5 minutes ago in ms

        # Get recent high-resolution data
        recent_data = [
            entry for entry in temperature_history if entry["time"] >= five_min_ago
        ]

        # Get decimated historical data
        historical_data = []
        for key in ["30min", "2hr", "8hr"]:
            historical_data.extend(decimated_history[key]["data"])

        # Combine and sort all data
        all_data = recent_data + historical_data
        all_data.sort(key=lambda x: x["time"])

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
            control_status["target_temp"] = float(temp)
        app.logger.info(f"Target temperature set to: {temp}°F")
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid temperature"})


@app.route("/toggle_run_state", methods=["POST"])
def toggle_run_state():
    with control_lock:
        control_status["running"] = not control_status["running"]
        new_state = "RUNNING" if control_status["running"] else "STOPPED"
    app.logger.info(f"System state changed to: {new_state}")
    return jsonify({"success": True, "running": control_status["running"]})


if __name__ == "__main__":
    # When running directly, start threads immediately.
    start_background_threads()
    app.run(debug=True, host="0.0.0.0", use_reloader=False)
