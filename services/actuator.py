import time
import RPi.GPIO as GPIO

# Setup GPIO mode
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Dictionary to track GPIO pin setup status
initialized_pins = {}

def initialize_pin(pin):
    """Initializes a GPIO pin as output if not already set up."""
    if pin not in initialized_pins:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)  # Relays are typically active-low
        initialized_pins[pin] = True

def set_pump_duration(pump_name, duration, pin):
    """
    Activates a pump on the specified GPIO pin for the given duration.
    """
    try:
        initialize_pin(pin)
        print(f"Activating {pump_name} on GPIO {pin} for {duration:.2f} seconds")
        GPIO.output(pin, GPIO.LOW)  # Activate relay
        time.sleep(duration)
        GPIO.output(pin, GPIO.HIGH)  # Deactivate
    except Exception as e:
        print(f"Error activating {pump_name} on GPIO {pin}: {e}")

def set_misting_interval(misting_name, on_time, off_time, pin):
    """
    Activates misting for on_time, then waits off_time before the next cycle.
    This runs one cycle per call; for continuous cycling, use a separate thread.
    """
    try:
        initialize_pin(pin)
        print(f"Starting misting cycle on GPIO {pin}: {on_time / 60:.1f} min on, {off_time / 60:.1f} min off")
        GPIO.output(pin, GPIO.LOW)  # Activate misting
        time.sleep(on_time)
        GPIO.output(pin, GPIO.HIGH)  # Deactivate
        print(f"Misting off, waiting {off_time / 60:.1f} minutes until next cycle")
        time.sleep(off_time)  # Wait off time before next cycle (simulated here)
    except Exception as e:
        print(f"Error in misting on GPIO {pin}: {e}")

def cleanup():
    """Cleans up GPIO settings on program exit."""
    GPIO.cleanup()
    initialized_pins.clear()