import time
import threading
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import math
from gpiozero import OutputDevice

# measured points from weber igrill ambient probe (these are cheap and plentiful)
# Point 1: 33.1F, 324.7k
# Point 2: 67.5F, 89k
# Point 3: 170.6F, 13.26k
CALIBRATION_DATA = [
    (324700, 33.1),
    (89000, 67.5),
    (13260, 170.6)
]

def derive_coefficients(data):
    """Solves Steinhart-Hart A, B, C from 3 resistance/temp points."""
    # Convert temps to Kelvin and take ln(R)
    L = [math.log(r) for r, t in data]
    Y = [1.0 / ((t - 32.0) * 5.0 / 9.0 + 273.15) for r, t in data]

    # Solve linear system for A, B, C (Determinant method for 3x3)
    # Eq: A + B*L + C*L^3 = 1/T
    D  = (L[0] - L[1]) * (L[1]**3 - L[2]**3) - (L[1] - L[2]) * (L[0]**3 - L[1]**3)

    # Calculate C
    inv_T_diff1 = Y[0] - Y[1]
    inv_T_diff2 = Y[1] - Y[2]
    C = (inv_T_diff1 * (L[1] - L[2]) - inv_T_diff2 * (L[0] - L[1])) / D

    # Calculate B
    B = (inv_T_diff1 - C * (L[0]**3 - L[1]**3)) / (L[0] - L[1])

    # Calculate A
    A = Y[0] - B * L[0] - C * L[0]**3

    return A, B, C

# Calculate defaults based on probe
try:
    DEF_A, DEF_B, DEF_C = derive_coefficients(CALIBRATION_DATA)
except Exception as e:
    logger.error(f"Error calculating coefficients: {e}")
    DEF_A, DEF_B, DEF_C = 0, 0, 0

def get_temp_celsius(voltage, r_fixed=10000, system_voltage=3.3,
                     sh_a=DEF_A, sh_b=DEF_B, sh_c=DEF_C):
    """
    Converts measured Voltage to Celsius using Steinhart-Hart equation.

    Args:
        voltage (float): The actual voltage measured at the pin (e.g., 2.15).
        r_fixed (float): The fixed resistor value in Ohms (default 10k).
        system_voltage (float): The voltage powering the divider (default 3.3V).
        sh_a, sh_b, sh_c (float): Thermistor Steinhart-Hart coefficients.

    Returns:
        float: Temperature in Celsius.
    """
    # 1. Safety check: voltage cannot be 0 (infinite resistance)
    #    or equal to system_voltage (0 resistance/short).
    if voltage <= 0 or voltage >= system_voltage:
        return None

    # 2. Calculate Resistance of Thermistor
    # Formula derived from V_out = V_in * (R_therm / (R_fixed + R_therm))
    # Becomes: R_therm = R_fixed * (V_out / (V_in - V_out))
    r_thermistor = r_fixed * (voltage / (system_voltage - voltage))

    # 3. Apply Steinhart-Hart Equation
    ln_r = math.log(r_thermistor)
    inv_temp_kelvin = sh_a + (sh_b * ln_r) + (sh_c * (ln_r ** 3))

    # 4. Convert Kelvin to Celsius
    temp_celsius = (1.0 / inv_temp_kelvin) - 273.15

    return temp_celsius

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
    i2c = busio.I2C(board.SCL, board.SDA)

    # Create the ADS object and specify the gain
    ads = ADS.ADS1115(i2c)
    ads.gain = 1
    adc_chan_oil = AnalogIn(ads, ADS.P0)
    adc_chan_turkey = AnalogIn(ads, ADS.P1)

    logger.info(f"ADS open, current reading oil {adc_chan_oil.voltage}v, turkey {adc_chan_turkey.voltage}")
    while True:
        with data_lock:
            # Store raw voltages for debugging
            oil_voltage = adc_chan_oil.voltage
            turkey_voltage = adc_chan_turkey.voltage
            
            temperature_data["oil_temp"] = get_temp_celsius(oil_voltage)
            temperature_data["turkey_temp"] = get_temp_celsius(turkey_voltage)
            temperature_data["oil_voltage"] = oil_voltage
            temperature_data["turkey_voltage"] = turkey_voltage

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
    BURNER_PIN = 21
    
    # Initialize the burner relay (active high)
    burner_relay = OutputDevice(BURNER_PIN, active_high=True, initial_value=False)
    logger.info(f"Initialized burner control on GPIO {BURNER_PIN}")

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
                    burner_relay.off()
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
                    burner_relay.off()
                    logger.info(f"Burner OFF. PID Output: {pid_output:.1f}")
            # Turning ON is only allowed after cooldown
            elif desired_burner_state is True and time_since_last_toggle > BURNER_ON_COOLDOWN:
                with control_lock:
                    control_status["burner_on"] = True
                    control_status["last_toggle_time"] = time.time()
                    burner_relay.on()
                    logger.info(f"Burner ON. PID Output: {pid_output:.1f}")

        with control_lock:
            control_status["pid_output"] = pid_output

        time.sleep(1)
