from dataclasses import dataclass
import time
import threading
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import math
from gpiozero import OutputDevice
from typing import Optional


@dataclass
class TemperatureReading:
    """A class to hold temperature and resistance readings from a thermistor."""
    temperature_celsius: Optional[float]
    resistance_ohms: Optional[float]
    
    @property
    def is_valid(self) -> bool:
        """Check if the reading is valid (both temperature and resistance are not None)."""
        return self.temperature_celsius is not None and self.resistance_ohms is not None

# measured points from weber igrill ambient probe (these are cheap and plentiful)
# resistance in ohms, temp in F
CALIBRATION_DATA = [
    (303950, 32.9),
    (324700, 33.1),
    (89000, 67.5),
    (27810, 134.2),
    (13260, 170.6),
]

def derive_coefficients(data):
    """
    Fits Steinhart-Hart A, B, C coefficients to N data points using
    Least Squares Regression. (Pure Python, no numpy).

    Model: 1/T = A + B*ln(R) + C*(ln(R)^3)
    """
    N = len(data)
    if N < 3:
        raise ValueError("Need at least 3 data points for Steinhart-Hart regression.")

    # 1. Prepare the Sums for the Normal Equation Matrix (X.T * X)
    # We are solving Ax = b where x is [A, B, C]
    sum_1 = N
    sum_L = 0.0    # Sum of ln(R)
    sum_L2 = 0.0   # Sum of ln(R)^2
    sum_L3 = 0.0   # Sum of ln(R)^3
    sum_L4 = 0.0
    sum_L6 = 0.0

    sum_Y = 0.0    # Sum of 1/T
    sum_YL = 0.0   # Sum of (1/T) * ln(R)
    sum_YL3 = 0.0  # Sum of (1/T) * ln(R)^3

    for r, t_f in data:
        # Convert T to Kelvin
        t_k = (t_f - 32.0) * 5.0 / 9.0 + 273.15
        y = 1.0 / t_k
        L = math.log(r)

        # Accumulate powers of L
        L2 = L * L
        L3 = L2 * L
        L4 = L2 * L2
        L6 = L3 * L3

        sum_L += L
        sum_L2 += L2
        sum_L3 += L3
        sum_L4 += L4
        sum_L6 += L6

        # Accumulate cross terms with Y
        sum_Y += y
        sum_YL += y * L
        sum_YL3 += y * L3

    # 2. Construct the Matrix (Symmetric) and Vector
    # Matrix M = [[sum_1, sum_L, sum_L3],
    #             [sum_L, sum_L2, sum_L4],
    #             [sum_L3, sum_L4, sum_L6]]
    M = [
        [sum_1, sum_L,  sum_L3],
        [sum_L, sum_L2, sum_L4],
        [sum_L3, sum_L4, sum_L6]
    ]

    # Vector V = [sum_Y, sum_YL, sum_YL3]
    V = [sum_Y, sum_YL, sum_YL3]

    # 3. Solve M * [A,B,C] = V using Gaussian Elimination (Standard Linear Algebra)
    # We pivot to solve for unknowns.

    n_vars = 3
    # Forward Elimination
    for i in range(n_vars):
        # Pivot
        pivot = M[i][i]
        for j in range(i + 1, n_vars):
            factor = M[j][i] / pivot
            V[j] -= factor * V[i]
            for k in range(i, n_vars):
                M[j][k] -= factor * M[i][k]

    # Back Substitution
    solution = [0.0] * n_vars
    for i in range(n_vars - 1, -1, -1):
        sum_ax = sum(M[i][j] * solution[j] for j in range(i + 1, n_vars))
        solution[i] = (V[i] - sum_ax) / M[i][i]

    # Unpack coefficients
    A, B, C = solution
    return A, B, C

# Calculate defaults based on probe
try:
    DEF_A, DEF_B, DEF_C = derive_coefficients(CALIBRATION_DATA)
    print(f"New Coeffs -> A: {DEF_A:.9f}, B: {DEF_B:.9f}, C: {DEF_C:.9f}")
except Exception as e:
    print(f"Calibration failed: {e}")

def get_temp_celsius(voltage: float, r_fixed: float = 10000, system_voltage: float = 3.3,
                     sh_a: float = DEF_A, sh_b: float = DEF_B, sh_c: float = DEF_C) -> TemperatureReading:
    """
    Converts measured Voltage to Celsius using Steinhart-Hart equation.

    Args:
        voltage: The actual voltage measured at the pin (e.g., 2.15).
        r_fixed: The fixed resistor value in Ohms (default 10k).
        system_voltage: The voltage powering the divider (default 3.3V).
        sh_a, sh_b, sh_c: Thermistor Steinhart-Hart coefficients.

    Returns:
        TemperatureReading: An object containing temperature in Celsius and resistance in ohms.
    """
    # Safety check: voltage cannot be 0 (infinite resistance)
    # or equal to system_voltage (0 resistance/short).
    if voltage <= 0 or voltage >= system_voltage:
        return TemperatureReading(temperature_celsius=None, resistance_ohms=None)

    # Calculate Resistance of Thermistor
    # Formula derived from V_out = V_in * (R_therm / (R_fixed + R_therm))
    # Becomes: R_therm = R_fixed * (V_out / (V_in - V_out))
    r_thermistor = r_fixed * (voltage / (system_voltage - voltage))

    # Apply Steinhart-Hart Equation
    try:
        ln_r = math.log(r_thermistor)
        inv_temp_kelvin = sh_a + (sh_b * ln_r) + (sh_c * (ln_r ** 3))
        temp_celsius = (1.0 / inv_temp_kelvin) - 273.15
    except (ValueError, ZeroDivisionError):
        return TemperatureReading(temperature_celsius=None, resistance_ohms=None)

    return TemperatureReading(temperature_celsius=temp_celsius, resistance_ohms=r_thermistor)

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
            # Get temperature and resistance for both probes
            oil_voltage = adc_chan_oil.voltage
            turkey_voltage = adc_chan_turkey.voltage
            
            oil_reading = get_temp_celsius(oil_voltage)
            turkey_reading = get_temp_celsius(turkey_voltage)
            
            temperature_data["oil_temp"] = oil_reading.temperature_celsius
            temperature_data["turkey_temp"] = turkey_reading.temperature_celsius
            temperature_data["oil_voltage"] = oil_voltage
            temperature_data["turkey_voltage"] = turkey_voltage
            temperature_data["oil_resistance"] = oil_reading.resistance_ohms
            temperature_data["turkey_resistance"] = turkey_reading.resistance_ohms

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
