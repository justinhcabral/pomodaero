#!/usr/bin/python3
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from sensors import read_tds, read_ph
import actuator  # Import actuator module for sending commands
import logging
import atexit

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Register cleanup on exit
atexit.register(actuator.cleanup)

# Define the antecedents (inputs)
pH = ctrl.Antecedent(np.arange(0, 14.01, 0.01), 'pH')  # pH: 0-14
EC = ctrl.Antecedent(np.arange(0, 2.301, 0.01), 'EC')  # EC: 0-2.3 mS/cm

# Define the consequents (outputs)
pH_up = ctrl.Consequent(np.arange(0, 1.01, 0.01), 'pH_up')      # 0-1.0 s
pH_down = ctrl.Consequent(np.arange(0, 1.01, 0.01), 'pH_down')  # 0-1.0 s
nutrients = ctrl.Consequent(np.arange(0, 3.01, 0.01), 'nutrients')  # 0-3.0 s
water = ctrl.Consequent(np.arange(0, 3.01, 0.01), 'water')     # 0-3.0 s

# Define membership functions for pH (trapezoidal, from simulation)
pH['low'] = fuzz.trapmf(pH.universe, [0, 0, 5.5, 5.8])
pH['normal'] = fuzz.trapmf(pH.universe, [5.5, 5.8, 6.2, 6.5])
pH['high'] = fuzz.trapmf(pH.universe, [6.2, 6.5, 14, 14])

# Define membership functions for EC (trapezoidal, from simulation)
EC['low'] = fuzz.trapmf(EC.universe, [0, 0, 1.8, 2.0])
EC['normal'] = fuzz.trapmf(EC.universe, [1.8, 2.0, 2.3, 2.3])
EC['high'] = fuzz.trapmf(EC.universe, [2.2, 2.3, 2.3, 2.3])

# Define membership functions for pH_up and pH_down (trapezoidal, from simulation)
for output in [pH_up, pH_down]:
    output['off'] = fuzz.trapmf(output.universe, [0, 0, 0.05, 0.1])
    output['short'] = fuzz.trapmf(output.universe, [0.05, 0.2, 0.4, 0.6])
    output['long'] = fuzz.trapmf(output.universe, [0.4, 0.7, 1.0, 1.0])

# Define membership functions for nutrients and water (trapezoidal, from simulation)
for output in [nutrients, water]:
    output['off'] = fuzz.trapmf(output.universe, [0, 0, 0.1, 0.2])
    output['short'] = fuzz.trapmf(output.universe, [0.1, 0.5, 1.0, 1.5])
    output['long'] = fuzz.trapmf(output.universe, [1.0, 2.0, 3.0, 3.0])

# Define the rule base (from simulation, prevents conflicting pH pumps)
rules = [
    ctrl.Rule(pH['low'] & EC['low'], 
              [pH_up['short'], pH_down['off'], nutrients['long'], water['off']]),
    ctrl.Rule(pH['low'] & EC['normal'], 
              [pH_up['short'], pH_down['off'], nutrients['off'], water['off']]),
    ctrl.Rule(pH['low'] & EC['high'], 
              [pH_up['short'], pH_down['off'], nutrients['off'], water['long']]),
    ctrl.Rule(pH['normal'] & EC['low'], 
              [pH_up['off'], pH_down['off'], nutrients['short'], water['off']]),
    ctrl.Rule(pH['normal'] & EC['normal'], 
              [pH_up['off'], pH_down['off'], nutrients['off'], water['off']]),
    ctrl.Rule(pH['normal'] & EC['high'], 
              [pH_up['off'], pH_down['off'], nutrients['off'], water['short']]),
    ctrl.Rule(pH['high'] & EC['low'], 
              [pH_up['off'], pH_down['long'], nutrients['short'], water['off']]),
    ctrl.Rule(pH['high'] & EC['normal'], 
              [pH_up['off'], pH_down['long'], nutrients['off'], water['off']]),
    ctrl.Rule(pH['high'] & EC['high'], 
              [pH_up['off'], pH_down['long'], nutrients['off'], water['short']]),
]

# Create the control system
control_system = ctrl.ControlSystem(rules)
sim = ctrl.ControlSystemSimulation(control_system)

def compute_fuzzy_commands(ph_value=None, ec_value=None):
    """
    Computes pump duration commands based on sensor readings or provided values.
    Returns a dictionary of pump durations and max duration, or zeros on error.
    
    Args:
        ph_value (float, optional): pH value to use instead of reading from sensors.
        ec_value (float, optional): EC value to use instead of reading from sensors.
    """
    try:
        # Read sensor data if values not provided
        if ph_value is None or ec_value is None:
            tds_data = read_tds()
            ph_data = read_ph()
            if tds_data is None or ph_data is None:
                logger.error("Sensor reading failed, skipping control cycle")
                return {'pH_up': 0.0, 'pH_down': 0.0, 'nutrients': 0.0, 'water': 0.0}, 0.0
            ec_value = tds_data.get('ec', 1.8)  # Default to safe value
            ph_value = ph_data.get('ph', 6.0)  # Default to safe value
        else:
            ec_value = float(ec_value)
            ph_value = float(ph_value)

        # Validate input ranges
        if ec_value < 0.01:
            logger.warning(f"Suspicious EC reading: {ec_value:.2f} mS/cm, using default 1.8")
            ec_value = 1.8
        ec_value = max(0, min(ec_value, 2.3))  # Clamp to 0-2.3 mS/cm
        ph_value = max(0, min(ph_value, 14.0))  # Clamp to 0-14

        # Log sensor readings
        logger.info(f"Input Readings - EC: {ec_value:.2f} mS/cm, pH: {ph_value:.2f}")

        # Set inputs to fuzzy system
        sim.input['pH'] = ph_value
        sim.input['EC'] = ec_value

        # Compute fuzzy outputs
        sim.compute()

        # Extract control instructions
        result = {
            'pH_up': sim.output['pH_up'],
            'pH_down': sim.output['pH_down'],
            'nutrients': sim.output['nutrients'],
            'water': sim.output['water']
        }

        # Safety check: prevent conflicting pH pumps
        if result['pH_up'] > 0.1 and result['pH_down'] > 0.1:
            logger.warning("Conflicting pH pumps detected, disabling both")
            result['pH_up'] = 0.0
            result['pH_down'] = 0.0

        # Limit durations for safety
        max_durations = {'pH_up': 1.0, 'pH_down': 1.0, 'nutrients': 3.0, 'water': 3.0}
        max_duration = 0.0
        for pump, duration in result.items():
            result[pump] = max(0, min(duration, max_durations[pump]))  # Ensure non-negative
            max_duration = max(max_duration, result[pump])

        # Log computed durations
        logger.info(f"Computed Commands - pH Up: {result['pH_up']:.2f} s, "
                    f"pH Down: {result['pH_down']:.2f} s, Nutrients: {result['nutrients']:.2f} s, "
                    f"Water: {result['water']:.2f} s")

        return result, max_duration

    except ValueError as ve:
        logger.error(f"Invalid sensor data: {ve}")
        return {'pH_up': 0.0, 'pH_down': 0.0, 'nutrients': 0.0, 'water': 0.0}, 0.0
    except RuntimeError as re:
        logger.error(f"Fuzzy computation error: {re}")
        return {'pH_up': 0.0, 'pH_down': 0.0, 'nutrients': 0.0, 'water': 0.0}, 0.0
    except Exception as e:
        logger.error(f"Unexpected error in fuzzy controller: {e}")
        return {'pH_up': 0.0, 'pH_down': 0.0, 'nutrients': 0.0, 'water': 0.0}, 0.0