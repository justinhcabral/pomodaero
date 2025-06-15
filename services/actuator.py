import time
import RPi.GPIO as GPIO
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define pump-to-pin mapping (BCM GPIO pins from your setup)
PUMP_PINS = {
    'pH_up': 23,      # GPIO pin for pH up pump
    'pH_down': 24,    # GPIO pin for pH down pump
    'nutrients_a': 25,  # GPIO pin for first nutrients pump
    'nutrients_b': 16,  # GPIO pin for second nutrients pump
    'water': 20       # GPIO pin for water pump
}

# Define misting-to-pin mapping (BCM GPIO pin from your setup)
MISTING_PINS = {
    'diaphragm_misting': 18  # GPIO pin for diaphragm misting pump
}

# Validate GPIO pins for duplicates
all_pins = list(PUMP_PINS.values()) + list(MISTING_PINS.values())
if len(all_pins) != len(set(all_pins)):
    logger.error(f"Duplicate GPIO pins detected: {all_pins}")
    raise ValueError("Duplicate GPIO pins configured")

# Setup GPIO mode
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Dictionary to track GPIO pin setup status
initialized_pins = {}

def initialize_pin(pin):
    """Initializes a GPIO pin as output if not already set up."""
    try:
        if pin not in initialized_pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH)  # Relays are active-low
            initialized_pins[pin] = True
            logger.debug(f"Initialized GPIO pin {pin} as output")
    except ValueError as ve:
        logger.error(f"Invalid GPIO pin {pin}: {ve}")
        raise
    except Exception as e:
        logger.error(f"Error initializing GPIO pin {pin}: {e}")
        raise

def activate_pump_on_pin(pump_name, pin, duration):
    """Helper function to activate a single pump on a specific pin for the given duration."""
    try:
        initialize_pin(pin)
        logger.info(f"Activating {pump_name} on GPIO {pin} for {duration:.2f} seconds")
        GPIO.output(pin, GPIO.LOW)  # Activate relay
        time.sleep(duration)
        GPIO.output(pin, GPIO.HIGH)  # Deactivate
    except Exception as e:
        logger.error(f"Error activating {pump_name} on GPIO {pin}: {e}")
        raise

def set_pump_duration(pump_name, duration):
    """
    Activates a dosing pump for the given duration using its predefined GPIO pin(s).
    For 'nutrients', activates both nutrients_a and nutrients_b concurrently.
    Args:
        pump_name (str): Name of the pump ('pH_up', 'pH_down', 'nutrients', 'water')
        duration (float): Duration to activate the pump in seconds
    Raises:
        ValueError: If pump_name is unknown or duration is invalid
    """
    try:
        if pump_name not in ['pH_up', 'pH_down', 'nutrients', 'water']:
            raise ValueError(f"Unknown pump: {pump_name}")
        if not isinstance(duration, (int, float)) or duration < 0:
            raise ValueError(f"Invalid duration for {pump_name}: {duration}")

        if pump_name == 'nutrients':
            # Run both nutrient pumps concurrently
            if 'nutrients_a' not in PUMP_PINS or 'nutrients_b' not in PUMP_PINS:
                raise ValueError("Both nutrients_a and nutrients_b pins must be configured")
            
            threads = []
            for nutrient_pump in ['nutrients_a', 'nutrients_b']:
                pin = PUMP_PINS[nutrient_pump]
                t = threading.Thread(target=activate_pump_on_pin, args=(nutrient_pump, pin, duration))
                threads.append(t)
                t.start()
            for t in threads:
                t.join()  # Wait for both pumps to finish
        else:
            # Single pump activation
            if pump_name not in PUMP_PINS:
                raise ValueError(f"Unknown pump: {pump_name}")
            pin = PUMP_PINS[pump_name]
            activate_pump_on_pin(pump_name, pin, duration)
            
    except ValueError as ve:
        logger.error(f"Error activating {pump_name}: {ve}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error activating {pump_name}: {e}")
        raise

def execute_pump_commands(commands):
    """
    Executes pump commands received from the fuzzy logic controller concurrently.
    Args:
        commands (dict): Dictionary of pump durations {'pH_up': float, 'pH_down': float, 
                         'nutrients': float, 'water': float}
    Raises:
        ValueError: If commands contain invalid pump names or durations
    """
    try:
        valid_pumps = ['pH_up', 'pH_down', 'nutrients', 'water']
        if not all(pump in valid_pumps for pump in commands):
            raise ValueError(f"Invalid pump names in commands: {commands}")
        if not all(isinstance(duration, (int, float)) and duration >= 0 for duration in commands.values()):
            raise ValueError(f"Invalid durations in commands: {commands}")

        threads = []
        for pump, duration in commands.items():
            if duration > 0:
                t = threading.Thread(target=set_pump_duration, args=(pump, duration))
                threads.append(t)
                t.start()
        for t in threads:
            t.join()  # Wait for all pumps to finish

        logger.info(f"Executed pump commands: {commands}")
    except ValueError as ve:
        logger.error(f"Error executing pump commands: {ve}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error executing pump commands: {e}")
        raise

def set_misting_interval(misting_name, on_time, off_time):
    """
    Activates a misting pump for one cycle (on_time on, off_time off) using its predefined GPIO pin.
    Args:
        misting_name (str): Name of the misting pump (e.g., 'diaphragm_misting')
        on_time (float): Duration to activate the pump in seconds
        off_time (float): Duration to keep the pump off in seconds
    Raises:
        ValueError: If misting_name is unknown or times are invalid
    """
    try:
        if misting_name not in MISTING_PINS:
            raise ValueError(f"Unknown misting pump: {misting_name}")
        if not isinstance(on_time, (int, float)) or on_time < 0:
            raise ValueError(f"Invalid on_time for {misting_name}: {on_time}")
        if not isinstance(off_time, (int, float)) or off_time < 0:
            raise ValueError(f"Invalid off_time for {misting_name}: {off_time}")
        
        pin = MISTING_PINS[misting_name]
        initialize_pin(pin)
        logger.info(f"Starting misting cycle for {misting_name} on GPIO {pin}: "
                    f"{on_time / 60:.1f} min on, {off_time / 60:.1f} min off")
        GPIO.output(pin, GPIO.LOW)  # Activate misting
        time.sleep(on_time)
        GPIO.output(pin, GPIO.HIGH)  # Deactivate
        logger.info(f"Misting off for {misting_name}, waiting {off_time / 60:.1f} minutes")
        time.sleep(off_time)
    except ValueError as ve:
        logger.error(f"Error in misting for {misting_name}: {ve}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in misting for {misting_name} on GPIO {pin}: {e}")
        raise

def cleanup():
    """Cleans up GPIO settings on program exit."""
    try:
        GPIO.cleanup()
        initialized_pins.clear()
        logger.info("GPIO cleanup completed")
    except Exception as e:
        logger.error(f"Error during GPIO cleanup: {e}")