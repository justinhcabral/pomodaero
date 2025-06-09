#!/usr/bin/python3
import time
from fuzzy_logic_controller import run_fuzzy_controller
import actuator

def determine_misting_interval(growth_stage):
    """
    Determines misting interval (on time and off time) based on growth stage from YOLOv11 mock data.
    Args:
        growth_stage (str): Mock growth stage ('Stage 1', 'Stage 2', 'Stage 3')
    Returns:
        tuple: (on_time in seconds, off_time in seconds)
    """
    misting_patterns = {
        'Stage 1': (60, 600),  # 1 minute on, 10 minutes off
        'Stage 2': (60, 300),  # 1 minute on, 5 minutes off
        'Stage 3': (60, 120)   # 1 minute on, 2 minutes off
    }
    return misting_patterns.get(growth_stage, (60, 300))  # Default to 1 min on, 5 min off

def send_nutrient_replacement_notification():
    """
    Simulates sending a notification to the user to replace the nutrient solution.
    (Firebase functionality removed, just prints a message for now)
    """
    print("Notification: Please replace the nutrient solution within 10 minutes.")

def run_decision_engine():
    """
    Coordinates decisions, enforces sequential relay activation, and handles nutrient replacement.
    Returns:
        dict: Control instructions including misting interval and pump durations
    """
    try:
        # Step 1: Mock YOLOv11 data for growth stage
        growth_stages = ['Stage 1', 'Stage 2', 'Stage 3']
        current_stage = growth_stages[int(time.time() % 3)]  # Cycle through stages for simulation
        print(f"Simulated Growth Stage: {current_stage}")

        # Step 2: Determine misting interval based on growth stage
        mist_on_time, mist_off_time = determine_misting_interval(current_stage)
        print(f"Misting Pattern: {mist_on_time / 60:.1f} min on, {mist_off_time / 60:.1f} min off")

        # Step 3: Get pump durations from fuzzy logic controller
        fuzzy_outputs = run_fuzzy_controller()
        pH_up_duration = fuzzy_outputs['pH_up']
        pH_down_duration = fuzzy_outputs['pH_down']
        nutrients_duration = fuzzy_outputs['nutrients']
        water_duration = fuzzy_outputs['water']

        # Step 4: Check if nutrient replacement is needed (e.g., after 24 hours or EC too low)
        # Mock condition: Replace if nutrients_duration is high and time-based check
        if nutrients_duration > 5.0 and time.time() % 86400 < 10:  # Simulate every 24 hours
            send_nutrient_replacement_notification()
            print("Waiting for nutrient replacement (10-minute window)...")
            time.sleep(600)  # 10-minute pause for manual replacement
            print("Nutrient replacement window complete, resuming automation.")

        # Step 5: Define sequence of relay activations
        relay_tasks = [
            ('pH_up', pH_up_duration, 23),         # in1: GPIO 23
            ('pH_down', pH_down_duration, 24),      # in2: GPIO 24
            ('nutrient_a', nutrients_duration, 25), # in3: GPIO 25
            ('nutrient_b', nutrients_duration, 16), # in4: GPIO 16
            ('water', water_duration, 20),         # in5: GPIO 20
            ('misting', mist_on_time, 21)          # in6: GPIO 21 (on time only)
        ]

        # Step 6: Execute tasks sequentially, turning off misting if nutrients/water are active
        total_delay = 0
        for task_name, duration, pin in relay_tasks:
            if duration > 0:
                # Turn off misting if nutrient or water pump is active to avoid dilution
                if task_name in ['nutrient_a', 'nutrient_b', 'water']:
                    actuator.set_pump_duration('misting', 0.0, pin=21)  # Turn off misting
                    print(f"Turned off misting for {task_name} activation.")
                
                # Activate the current relay
                actuator.set_pump_duration(task_name, duration, pin)
                print(f"Activated {task_name} on GPIO {pin} for {duration:.2f} seconds")
                
                # Calculate total delay for next cycle
                total_delay += duration
                time.sleep(duration)  # Ensure sequential execution

        # Step 7: Restore misting after all other tasks with the full cycle
        if mist_on_time > 0:
            actuator.set_misting_interval('misting', mist_on_time, mist_off_time, pin=21)
            print(f"Restored misting with {mist_on_time / 60:.1f} min on, {mist_off_time / 60:.1f} min off")

        # Return control instructions for logging
        return {
            'misting_on_time': mist_on_time,
            'misting_off_time': mist_off_time,
            'pH_up': pH_up_duration,
            'pH_down': pH_down_duration,
            'nutrients': nutrients_duration,
            'water': water_duration
        }

    except Exception as e:
        print(f"Error in decision engine: {e}")
        # Default to no action in case of error
        for pin in [23, 24, 25, 16, 20, 21]:
            actuator.set_pump_duration('default', 0.0, pin)
        actuator.set_misting_interval('misting', 60, 300, pin=21)  # Default: 1 min on, 5 min off
        return {
            'misting_on_time': 60,
            'misting_off_time': 300,
            'pH_up': 0.0,
            'pH_down': 0.0,
            'nutrients': 0.0,
            'water': 0.0
        }

if __name__ == "__main__":
    # Run the decision engine in a loop
    while True:
        try:
            result = run_decision_engine()
            print("Control Instructions:", result)
            time.sleep(60)  # Check every 60 seconds
        except KeyboardInterrupt:
            print("Stopped by user")
            actuator.cleanup()  # Clean up GPIO on exit
            break