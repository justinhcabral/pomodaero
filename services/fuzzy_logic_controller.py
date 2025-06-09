#!/usr/bin/python3
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from sensors import read_tds, read_ph
import actuator  # Import actuator module for pump control

# Define the antecedents (inputs)
pH = ctrl.Antecedent(np.arange(0, 14.01, 0.01), 'pH')  # pH: 0-14
EC = ctrl.Antecedent(np.arange(0, 2.51, 0.01), 'EC')   # EC: 0-2.5 mS/cm

# Define the consequents (outputs)
pH_up = ctrl.Consequent(np.arange(0, 1.01, 0.01), 'pH_up')      # 0-1.0 s
pH_down = ctrl.Consequent(np.arange(0, 1.01, 0.01), 'pH_down')  # 0-1.0 s
nutrients = ctrl.Consequent(np.arange(0, 10.01, 0.01), 'nutrients')  # 0-10.0 s
water = ctrl.Consequent(np.arange(0, 10.01, 0.01), 'water')     # 0-10.0 s

# Define membership functions for pH
pH['low'] = fuzz.trimf(pH.universe, [0, 0, 5.8])
pH['normal'] = fuzz.trimf(pH.universe, [5.8, 6.0, 6.2])
pH['high'] = fuzz.trimf(pH.universe, [6.2, 14, 14])

# Define membership functions for EC
EC['low'] = fuzz.trimf(EC.universe, [0, 0, 2.0])
EC['normal'] = fuzz.trimf(EC.universe, [2.0, 2.1, 2.2])
EC['high'] = fuzz.trimf(EC.universe, [2.2, 2.3, 2.3])

# Define membership functions for pH_up and pH_down
for output in [pH_up, pH_down]:
    output['off'] = fuzz.trimf(output.universe, [0, 0, 0.1])
    output['short'] = fuzz.trimf(output.universe, [0.1, 0.25, 0.4])
    output['long'] = fuzz.trimf(output.universe, [0.4, 0.7, 1.0])

# Define membership functions for nutrients and water
for output in [nutrients, water]:
    output['off'] = fuzz.trimf(output.universe, [0, 0, 1.0])
    output['short'] = fuzz.trimf(output.universe, [1.0, 3.0, 5.0])
    output['long'] = fuzz.trimf(output.universe, [5.0, 7.5, 10.0])

# Define the rule base
rules = [
    ctrl.Rule(pH['low'] & EC['low'], [pH_up['long'], pH_down['short'], nutrients['long'], water['short']]),
    ctrl.Rule(pH['low'] & EC['normal'], [pH_up['long'], pH_down['short'], nutrients['off'], water['off']]),
    ctrl.Rule(pH['low'] & EC['high'], [pH_up['long'], pH_down['short'], nutrients['short'], water['long']]),
    ctrl.Rule(pH['normal'] & EC['low'], [pH_up['off'], pH_down['off'], nutrients['long'], water['short']]),
    ctrl.Rule(pH['normal'] & EC['normal'], [pH_up['off'], pH_down['off'], nutrients['off'], water['off']]),
    ctrl.Rule(pH['normal'] & EC['high'], [pH_up['off'], pH_down['off'], nutrients['short'], water['long']]),
    ctrl.Rule(pH['high'] & EC['low'], [pH_up['short'], pH_down['long'], nutrients['long'], water['short']]),
    ctrl.Rule(pH['high'] & EC['normal'], [pH_up['short'], pH_down['long'], nutrients['off'], water['off']]),
    ctrl.Rule(pH['high'] & EC['high'], [pH_up['short'], pH_down['long'], nutrients['short'], water['long']]),
]

# Create the control system
control_system = ctrl.ControlSystem(rules)
sim = ctrl.ControlSystemSimulation(control_system)

def run_fuzzy_controller():
    """
    Runs the fuzzy logic controller using sensor readings, computes control instructions,
    and sends them to the actuator module.
    """
    try:
        # Read sensor data
        tds_data = read_tds()
        ph_data = read_ph()

        # Extract and validate values
        ec_value = tds_data.get('ec', 0.0)  # Default to 0 if not found
        ph_value = ph_data.get('ph', 0.0)   # Default to 0 if not found

        # Clamp inputs to valid ranges
        ec_value = max(0, min(ec_value, 2.5))  # Limit to 0-2.5 mS/cm
        ph_value = max(0, min(ph_value, 14.0))  # Limit to 0-14

        # Print sensor readings for verification
        print(f"Sensor Readings - EC: {ec_value:.2f} mS/cm, pH: {ph_value:.2f}")

        # Set inputs to fuzzy system
        sim.input['pH'] = ph_value
        sim.input['EC'] = ec_value

        # Compute fuzzy outputs
        sim.compute()

        # Extract control instructions
        pH_up_duration = sim.output['pH_up']
        pH_down_duration = sim.output['pH_down']
        nutrients_duration = sim.output['nutrients']
        water_duration = sim.output['water']

        # Print computed durations for verification
        print(f"Computed Durations - pH Up: {pH_up_duration:.2f} s, "
              f"pH Down: {pH_down_duration:.2f} s, Nutrients: {nutrients_duration:.2f} s, "
              f"Water: {water_duration:.2f} s")

        # Send control instructions to actuator
        actuator.set_pump_duration('pH_up', pH_up_duration)
        actuator.set_pump_duration('pH_down', pH_down_duration)
        actuator.set_pump_duration('nutrients', nutrients_duration)  # Controls both A and B
        actuator.set_pump_duration('water', water_duration)

        return {
            'pH_up': pH_up_duration,
            'pH_down': pH_down_duration,
            'nutrients': nutrients_duration,
            'water': water_duration
        }

    except Exception as e:
        print(f"Error in fuzzy controller: {e}")
        # Default to no action in case of error
        actuator.set_pump_duration('pH_up', 0.0)
        actuator.set_pump_duration('pH_down', 0.0)
        actuator.set_pump_duration('nutrients', 0.0)
        actuator.set_pump_duration('water', 0.0)
        return {'pH_up': 0.0, 'pH_down': 0.0, 'nutrients': 0.0, 'water': 0.0}

if __name__ == "__main__":
    # Run the controller in a loop (e.g., every minute)
    import time
    while True:
        try:
            result = run_fuzzy_controller()
            print("Control Instructions:", result)
            time.sleep(60)  # Check every 60 seconds
        except KeyboardInterrupt:
            print("Stopped by user")
            break

