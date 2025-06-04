from re import L
from config import PUMP_PINS as PUMP_PINS

import sys
import time

# This module handles the actuators for the system. Tries to import gpiozero for Raspberry Pi GPIO control.
# If gpiozero is not available, it runs in mock mode.
# If running on a Raspberry Pi, it will use the GPIO pins defined in PUMP_PINS.
try:
    import RPi.GPIO as GPIO
    ON_PI = True
except (ImportError, RuntimeError):
    ON_PI = False
    print("[WARN] RPi.GPIO not available. Running in mock mode")

# Dictionary to hold pump pin numbers
pumps = {}

# Setup
if ON_PI:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pump_name, pin in PUMP_PINS.items():
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        pumps[pump_name] = pin
    print("[ACTUATORS] Initialized RPi.GPIO pins for pumps")
else:
    for pump_name in PUMP_PINS:
        pumps[pump_name] = None # Placeholder for mock
    print("[MOCK] Pumps initialized as mock devices.")

def activate_pump(pump_name: str, duration: float = 5.0):
    if pump_name not in pumps:
        raise ValueError(f"[ERROR] Unknown pump: {pump_name}")
    
    if ON_PI:
        pin = pumps[pump_name]
        GPIO.output(pin, GPIO.HIGH)
        print(f"[ACTUATOR] Pump '{pump_name}' ON")
        time.sleep(duration)
        GPIO.output(pin, GPIO.LOW)
        print(f"[ACTUATOR] Pump '{pump_name}' OFF")
    else:
        print(f"[MOCK] Simulating pump '{pump_name}' for {duration}s")
        time.sleep(duration)

def cleanup():
    if ON_PI:
        GPIO.cleanup()
        print("[ACTUATORS] Cleaned up GPIO pins")