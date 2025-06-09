#!/usr/bin/python3
import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_dht

# Initialize I2C bus and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
ads.gain = 1  # ±4.096V gain

# Set up channels for TDS and pH sensors
tds_channel = AnalogIn(ads, ADS.P1)  # TDS sensor on P1 (A1)
ph_channel = AnalogIn(ads, ADS.P0)   # pH sensor on P0 (A0)

# Set up DHT11 sensor
DHT_SENSOR = adafruit_dht.DHT11(board.D17)  # GPIO17 (BCM numbering)

# Calibration coefficients for pH
m = -5.339286  # Slope
b = 20.294821  # Intercept

# Conversion factor for EC calculation
CONVERSION_FACTOR = 0.5  # EC (μS/cm) = TDS (ppm) / 0.5, best for distilled water.

def read_tds():
    """
    Reads the TDS sensor voltage, averages multiple samples, calculates TDS,
    and calculates EC.

    Returns:
        dict: Contains 'voltage', 'tds', and 'ec' values.
    """
    buf = []
    for _ in range(10):
        buf.append(tds_channel.voltage)
        time.sleep(0.1)  # Small delay between readings
    buf.sort()
    buf = buf[2:-2]  # Discard highest and lowest two
    voltage = sum(buf) / 6
    print(f"Raw TDS Voltage: {voltage:.3f} V")  # Debug print
    tds = (133.42 * voltage**3 - 255.86 * voltage**2 + 857.39 * voltage) * 0.5
    tds = max(0, tds)
    ec_micro = tds / CONVERSION_FACTOR
    ec = ec_micro / 1000
    return {'voltage': voltage, 'tds': tds, 'ec': ec}

def read_ph():
    """
    Reads the pH sensor voltage, averages multiple samples, and calculates pH.

    Returns:
        dict: Contains 'voltage' and 'ph' values.
    """
    buf = []
    for _ in range(10):
        buf.append(ph_channel.voltage)
        time.sleep(0.1)
    buf.sort()
    buf = buf[2:-2]
    voltage = sum(buf) / 6
    print(f"Raw pH Voltage: {voltage:.3f} V")  # Debug print
    ph = m * voltage + b
    return {'voltage': voltage, 'ph': ph}

def read_dht11():
    """
    Reads temperature and humidity from DHT11 sensor on GPIO17, averaging multiple samples.

    Returns:
        dict: Contains 'temperature' and 'humidity' values, or None if reading fails.
    """
    temp_buf = []
    hum_buf = []
    for _ in range(10):
        try:
            DHT_SENSOR.measure()  # Trigger measurement
            temperature = DHT_SENSOR.temperature
            humidity = DHT_SENSOR.humidity
            if humidity is not None and temperature is not None:
                hum_buf.append(humidity)
                temp_buf.append(temperature)
        except RuntimeError:
            pass  # Ignore transient errors
        time.sleep(.5)  # DHT11 requires at least 1-2s between readings
    if len(temp_buf) >= 6 and len(hum_buf) >= 6:
        temp_buf.sort()
        hum_buf.sort()
        temp_buf = temp_buf[2:-2]  # Discard highest and lowest two
        hum_buf = hum_buf[2:-2]
        temperature = sum(temp_buf) / len(temp_buf)
        humidity = sum(hum_buf) / len(hum_buf)
        print(f"Raw Temperature: {temperature:.2f} °C, Humidity: {humidity:.2f} %")  # Debug print
        return {'temperature': temperature, 'humidity': humidity}
    else:
        print("Failed to read DHT11 data")
        return {'temperature': None, 'humidity': None}

# Take single readings
if __name__ == "__main__":
    try:
        tds_data = read_tds()
        time.sleep(0.1)  # Delay between channel readings
        ph_data = read_ph()
        dht_data = read_dht11()
        print(f"TDS Voltage: {tds_data['voltage']:.3f} V, TDS: {tds_data['tds']:.2f} ppm, EC: {tds_data['ec']:.2f} mS/cm")
        print(f"pH Voltage: {ph_data['voltage']:.3f} V, pH: {ph_data['ph']:.2f}")
        if dht_data['temperature'] is not None and dht_data['humidity'] is not None:
            print(f"Temperature: {dht_data['temperature']:.2f} °C, Humidity: {dht_data['humidity']:.2f} %")
        else:
            print("DHT11 reading failed")
    except Exception as e:
        print(f"Error reading sensors: {e}")