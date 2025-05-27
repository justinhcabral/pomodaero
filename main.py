from services import sensors
from services import actuators

def main():
    temp, humidity = sensors.read_dht11()
    ph = sensors.read_ph()
    ec = sensors.read_ec()

    # print(f"Temperature: {temp}")
    # print(f"Humidity: {humidity}%")
    # print(f"pH Level: {ph}")
    # print(f"EC Level: {ec} mS/cm")

    actuators.activate_pump("diaphragm", duration=2)
    actuators.actiavte_pump("peristaltic_1", duration=1)

if __name__ == "__main__":
    main()