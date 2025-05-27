from re import L
from config import PUMP_PINS as PUMP_PINS

import sys
import time

# This module handles the actuators for the system. Tries to import gpiozero for Raspberry Pi GPIO control.
# If gpiozero is not available, it runs in mock mode.
# If running on a Raspberry Pi, it will use the GPIO pins defined in PUMP_PINS.
try:
    from gpiozero import OutputDevice
    ON_PI = True
except (ImportError, RuntimeError):
    ON_PI = False
    print("[WARN] gpiozero not available. Running in mock mode")

# Dictionary to hold pump OutputDevices or mocks
pumps = {}

# Setup
if ON_PI:
    for pump_name, pin in PUMP_PINS.items():
        pumps[pump_name] = OutputDevice(pin, active_high = True, initial_value=False)
    print("[ACTUATORS] Initialized gpiozero OutputDevices")
else:
    for pump_name in PUMP_PINS:
        pumps[pump_name] = None #Placeholder for mock
    print("[MOCK] Pumps initialized as mock devices.")

def activate_pump(pump_name: str, duration: float = 5.0):
    if pump_name not in pumps:
        raise ValueError(f"[ERROR] Unknown pump: {pump_name}")
    
    if ON_PI:
        pump = pumps[pump_name]
        pump.on()
        print(f"[ACTUATOR] Pump {pump_name}' ON")
        time.sleep(duration)
        pump.off()
        print(f"[Actuator] Pump '{pump_name}' OFF")
    else:
        print(f"[MOCK] Simulating pump '{pump_name}' for {duration}s")
        time.sleep(duration)

# our function for activating the peristaltic pumps and the diaphragm pump will be different. the operation of the misting pump will be dependent on the growth stage and the 