#!/usr/bin/python3
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from sensors import read_tds, read_ph

# Define nutrient fuzzy logic (EC, pH -> nutrient pumps)
ec = ctrl.Antecedent(np.arange(0, 5.1, 0.1), 'ec')  # EC: 0-5 mS/cm
ph = ctrl.Antecedent(np.arange(4.0, 8.1, 0.1), 'ph')  # pH: 4-8
pump_duration = ctrl.Consequent(np.arange(0, 31, 1), 'pump_duration')  # 0-30 seconds
ph_action = ctrl.Consequent(np.arange(-1, 2, 1), 'ph_action')  # -1 to 1

ec['low'] = fuzz.trimf(ec.universe, [0, 0, 2.0])
ec['optimal'] = fuzz.trimf(ec.universe, [1.5, 2.5, 3.5])
ec['high'] = fuzz.trimf(ec.universe, [3.0, 5.0, 5.0])

ph['acidic'] = fuzz.trimf(ph.universe, [4.0, 4.0, 5.5])
ph['neutral'] = fuzz.trimf(ph.universe, [5.0, 6.0, 7.0])
ph['alkaline'] = fuzz.trimf(ph.universe, [6.5, 8.0, 8.0])

pump_duration['short'] = fuzz.trimf(pump_duration.universe, [0, 0, 10])
pump_duration['medium'] = fuzz.trimf(pump_duration.universe, [5, 15, 25])
pump_duration['long'] = fuzz.trimf(pump_duration.universe, [20, 30, 30])

ph_action['add_down'] = fuzz.trimf(ph_action.universe, [-1, -1, 0])
ph_action['no_action'] = fuzz.trimf(ph_action.universe, [-0.5, 0, 0.5])
ph_action['add_up'] = fuzz.trimf(ph_action.universe, [0, 1, 1])

rule1 = ctrl.Rule(ec['low'] & ph['neutral'], (pump_duration['long'], ph_action['no_action']))
rule2 = ctrl.Rule(ec['optimal'] & ph['acidic'], (pump_duration['medium'], ph_action['add_up']))
rule3 = ctrl.Rule(ec['high'] & ph['alkaline'], (pump_duration['short'], ph_action['add_down']))

nutrient_ctrl = ctrl.ControlSystem([rule1, rule2, rule3])
nutrient_sim = ctrl.ControlSystemSimulation(nutrient_ctrl)

# Define humidity fuzzy logic (humidity -> mist interval adjustment)
humidity = ctrl.Antecedent(np.arange(0, 101, 1), 'humidity')  # 0-100%
adjustment = ctrl.Consequent(np.arange(-60, 61, 1), 'adjustment')  # +/- 60 sec

humidity['low'] = fuzz.trimf(humidity.universe, [0, 0, 40])
humidity['medium'] = fuzz.trimf(humidity.universe, [30, 50, 70])
humidity['high'] = fuzz.trimf(humidity.universe, [60, 100, 100])

adjustment['reduce'] = fuzz.trimf(adjustment.universe, [-60, -60, 0])
adjustment['none'] = fuzz.trimf(adjustment.universe, [-10, 0, 10])
adjustment['increase'] = fuzz.trimf(adjustment.universe, [0, 60, 60])

rule_low = ctrl.Rule(humidity['low'], adjustment['reduce'])
rule_medium = ctrl.Rule(humidity['medium'], adjustment['none'])
rule_high = ctrl.Rule(humidity['high'], adjustment['increase'])

adjustment_ctrl = ctrl.ControlSystem([rule_low, rule_medium, rule_high])
adjustment_sim = ctrl.ControlSystemSimulation(adjustment_ctrl)

def run_fuzzy_controller(humidity_val, growth_stage):
    """
    Runs the fuzzy logic controller using sensor readings and humidity input.
    
    Args:
        humidity_val (float): Humidity percentage (0-100).
        growth_stage (str): Plant growth stage ('seedling', 'vegetative', 'flowering', 'fruiting').
    
    Returns:
        dict: {'pump_duration': float, 'ph_action': float, 'mist_interval_sec': float}
    """
    try:
        # Read sensor data
        tds_data = read_tds()
        ph_data = read_ph()

        # Extract and convert values (EC from μS/cm to mS/cm)
        ec_value = tds_data['ec']
        ph_value = ph_data['ph']
        humidity_value = humidity_val

        # Clamp inputs to valid ranges
        ec_value = min(max(ec_value, 0), 5.0)  # 0-5 mS/cm
        ph_value = min(max(ph_value, 4.0), 8.0)  # 4-8
        humidity_value = min(max(humidity_value, 0), 100)  # 0-100%

        # Print sensor readings for verification
        print(f"EC: {ec_value:.2f} mS/cm, pH: {ph_value:.2f}, Humidity: {humidity_value:.2f}%")

        # Set baseline mist interval based on growth stage
        baseline_mist_intervals = {
            'seedling': 60,   # seconds
            'vegetative': 120,
            'flowering': 180,
            'fruiting': 240
        }
        baseline_mist = baseline_mist_intervals.get(growth_stage, 120)  # Default 120s

        # Run nutrient fuzzy
        nutrient_sim.input['ec'] = ec_value
        nutrient_sim.input['ph'] = ph_value
        nutrient_sim.compute()

        # Run humidity fuzzy for mist adjustment
        adjustment_sim.input['humidity'] = humidity_value
        adjustment_sim.compute()

        # Get outputs
        pump_duration = nutrient_sim.output['pump_duration']
        ph_action = nutrient_sim.output['ph_action']
        mist_adjustment = adjustment_sim.output['adjustment']

        # Calculate misting interval
        mist_interval_sec = max(10, baseline_mist + mist_adjustment)

        # Return results as dictionary
        result = {
            'pump_duration': float(pump_duration),
            'ph_action': float(ph_action),
            'mist_interval_sec': float(mist_interval_sec)
        }
        print(f"EC: {ec_value}, PH: {ph_value}")
        print(f"Pump Duration: {result['pump_duration']:.2f} s, pH Action: {result['ph_action']:.2f}, "
              f"Mist Interval: {result['mist_interval_sec']:.2f} s")

        return result

    except Exception as e:
        print(f"Error in fuzzy controller: {e}")
        return {
            'pump_duration': 0.0,
            'ph_action': 0.0,
            'mist_interval_sec': 120.0  # Default mist interval
        }

if __name__ == "__main__":
    # Example usage with sensor readings
    try:
        result = run_fuzzy_controller(humidity_val=45.0, growth_stage='vegetative')
        print("Result:", result)
    except KeyboardInterrupt:
        print("Stopped by user")

