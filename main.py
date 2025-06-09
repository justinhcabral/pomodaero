# from services import sensors
# from services import actuators

# def main():
#     temp, humidity = sensors.read_dht11()
#     ph = sensors.read_ph()
#     ec = sensors.read_ec()

#     # print(f"Temperature: {temp}")
#     # print(f"Humidity: {humidity}%")
#     # print(f"pH Level: {ph}")
#     # print(f"EC Level: {ec} mS/cm")

#     # actuators.activate_pump("diaphragm", duration=10)
#     actuators.activate_pump("peristaltic_3", duration=10)

# if __name__ == "__main__":
#     main()

#test code for opening pumps

import RPi.GPIO as GPIO
from time import sleep

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# All pump pins
pumps = [23, 24, 25, 16, 20, 21]
# 23, 24, 25, 16, 20, 21 pump pin order

# Setup all pump pins as outputs and turn them OFF (HIGH = OFF for active-LOW relay)
for pump in pumps:
    GPIO.setup(pump, GPIO.OUT)
    GPIO.output(pump, GPIO.HIGH)

try:
    while True:
        for i, pump in enumerate(pumps):
            # Turn all pumps OFF
            for p in pumps:
                GPIO.output(p, GPIO.HIGH)
            # Turn the current pump ON (LOW = ON for active-LOW)
            GPIO.output(pump, GPIO.LOW)
            print(f"Pump {i+1} (GPIO {pump}) ON")
            sleep(2)

except KeyboardInterrupt:
    print("Cleaning up...")
    for p in pumps:
        GPIO.output(p, GPIO.HIGH)
    GPIO.cleanup()


# from services.fuzzy_logic_controller import run_fuzzy_controller

# if __name__ == "__main__":
#     mock_ec = 2.0
#     mock_ph = 6.0
#     mock_humidity = 40
#     mock_baseline_misting = 10  # example baseline in seconds

#     pump_dur, ph_act, mist_int = run_fuzzy_controller(mock_ec, mock_ph, mock_humidity, mock_baseline_misting)

#     print(f"Pump Duration: {pump_dur} seconds")
#     print(f"pH Action: {ph_act}")
#     print(f"Misting Interval (adjusted): {mist_int} seconds")