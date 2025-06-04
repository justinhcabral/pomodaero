#!/usr/bin/python3
import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Initialize I2C bus and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
ads.gain = 1  # ±4.096V gain

# Set up channels for TDS and pH sensors
tds_channel = AnalogIn(ads, ADS.P1)  # TDS sensor on P1 (A1)
ph_channel = AnalogIn(ads, ADS.P0)   # pH sensor on P0 (A0)

# Calibration coefficients for pH
m = -5.339286  # Slope
b = 20.294821  # Intercept

# Conversion factor for EC calculation
CONVERSION_FACTOR = 0.5  # EC (μS/cm) = TDS (ppm) / 0.5

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

# Take single readings
if __name__ == "__main__":
    try:
        tds_data = read_tds()
        time.sleep(0.1)  # Delay between channel readings
        ph_data = read_ph()
        print(f"TDS Voltage: {tds_data['voltage']:.3f} V, TDS: {tds_data['tds']:.2f} ppm, EC: {tds_data['ec']:.2f} mS/cm")
        print(f"pH Voltage: {ph_data['voltage']:.3f} V, pH: {ph_data['ph']:.2f}")
    except Exception as e:
        print(f"Error reading sensors: {e}")
