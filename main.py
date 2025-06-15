import logging
import sys
import os
from firebase_sync import listen_for_start_signal
from decision_engine import run_decision_engine
import actuator

# Add the services directory to the module search path
sys.path.append(os.path.join(os.path.dirname(__file__), "services"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("Waiting for start signal from mobile app via Firebase...")
    while True:
        if listen_for_start_signal():
            logger.info("Start signal received, initiating control loop")
            run_decision_engine()
        time.sleep(1)  # Poll every second

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
        actuator.cleanup()




# #test code for opening pumps

# import RPi.GPIO as GPIO
# from time import sleep

# GPIO.setwarnings(False)
# GPIO.setmode(GPIO.BCM)

# # All pump pins
# pumps = [23, 24, 25, 16, 20, 18]
# # 23, 24, 25, 16, 20, 18 pump pin order

# # Setup all pump pins as outputs and turn them OFF (HIGH = OFF for active-LOW relay)
# for pump in pumps:
#     GPIO.setup(pump, GPIO.OUT)
#     GPIO.output(pump, GPIO.HIGH)

# try:
#     while True:
#         for i, pump in enumerate(pumps):
#             # Turn all pumps OFF
#             for p in pumps:
#                 GPIO.output(p, GPIO.HIGH)
#             # Turn the current pump ON (LOW = ON for active-LOW)
#             GPIO.output(pump, GPIO.LOW)
#             print(f"Pump {i+1} (GPIO {pump}) ON")
#             sleep(1)

# except KeyboardInterrupt:
#     print("Cleaning up...")
#     for p in pumps:
#         GPIO.output(p, GPIO.HIGH)
#     GPIO.cleanup()
