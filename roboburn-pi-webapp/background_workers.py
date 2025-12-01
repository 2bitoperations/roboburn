import time
import threading


def temperature_worker(
    logger,
    temperature_data,
    temperature_history,
    decimated_history,
    decimated_last_update,
    data_lock,
    control_status,
    control_lock,
):
    """Worker thread to simulate temperature sensor readings and record history."""
    logger.info("Temperature worker thread started.")
    while True:
        with data_lock:
            with control_lock:
                is_burner_on = control_status["burner_on"]

            if is_burner_on:
                temperature_data["oil_temp"] += 1.5
            else:
                temperature_data["oil_temp"] -= 0.25

            if temperature_data["turkey_temp"] < temperature_data["oil_temp"]:
                temperature_data["turkey_temp"] += 0.1

            current_time = time.time()
            timestamp = current_time * 1000  # ms for frontend
            history_entry = {"time": timestamp, **temperature_data}

            # Add to full resolution history
            temperature_history.append(history_entry)

            # Update decimated histories if needed
            for key, history in decimated_history.items():
                if current_time - decimated_last_update[key] >= history["interval"]:
                    # Average all points since last update for this history
                    recent_points = [
                        (entry["time"], entry["oil_temp"], entry["turkey_temp"])
                        for entry in temperature_history
                        if entry["time"] / 1000 > decimated_last_update[key]
                    ]

                    if recent_points:
                        times, oil_temps, turkey_temps = zip(*recent_points)
                        avg_entry = {
                            "time": sum(times) / len(times),
                            "oil_temp": sum(oil_temps) / len(oil_temps),
                            "turkey_temp": sum(turkey_temps) / len(turkey_temps),
                        }
                        history["data"].append(avg_entry)
                        decimated_last_update[key] = current_time

        time.sleep(1)


def burner_control_worker(
    logger,
    temperature_history,
    data_lock,
    control_status,
    control_lock,
    pid,
):
    """Worker thread for controlling the burner with a 5-second toggle constraint for turning ON."""
    logger.info("Burner control worker started.")
    BURNER_ON_COOLDOWN = 5  # seconds

    while True:
        with control_lock:
            is_running = control_status["running"]
            target = control_status["target_temp"]
            pid.setpoint = target
            current_burner_state = control_status["burner_on"]
            last_toggle = control_status["last_toggle_time"]

        if not is_running:
            if current_burner_state:
                with control_lock:
                    control_status["burner_on"] = False
                    control_status["last_toggle_time"] = time.time()
                    logger.warning("System stopped. Turning burner OFF immediately.")
                pid.reset()
            time.sleep(1)
            continue

        with data_lock:
            current_oil_temp = (
                temperature_history[-1]["oil_temp"] if temperature_history else 70.0
            )

        pid_output = pid(current_oil_temp)
        desired_burner_state = pid_output > 50

        time_since_last_toggle = time.time() - last_toggle

        # Logic for state change
        if current_burner_state != desired_burner_state:
            if desired_burner_state is False:  # Turning OFF is always allowed
                with control_lock:
                    control_status["burner_on"] = False
                    control_status["last_toggle_time"] = time.time()
                    logger.info(f"Burner OFF. PID Output: {pid_output:.1f}")
            # Turning ON is only allowed after cooldown
            elif desired_burner_state is True and time_since_last_toggle > BURNER_ON_COOLDOWN:
                with control_lock:
                    control_status["burner_on"] = True
                    control_status["last_toggle_time"] = time.time()
                    logger.info(f"Burner ON. PID Output: {pid_output:.1f}")

        with control_lock:
            control_status["pid_output"] = pid_output

        time.sleep(1)
