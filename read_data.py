import serial
import time
import spidev
import math
import requests
from datetime import datetime
import pytz
import os
import sys
import board
import adafruit_dht

session_id = datetime.now().strftime("session_%Y-%m-%d_%H-%M")
print(f"Session ID: {session_id}")

# === Firebase Config ===
FIREBASE_BASE_URL = "https://iotcaproject-6422d-default-rtdb.europe-west1.firebasedatabase.app/air_quality_data"

# === SDS011 Setup ===
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600
ser = serial.Serial(SERIAL_PORT, baudrate=BAUD_RATE, timeout=1)

# === MCP3008 Setup for MQ135 ===
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1350000

VCC = 5.0
RL_VALUE = 10000
R0 = 144020  # default

# === DHT11 Setup ===
dhtDevice = adafruit_dht.DHT11(board.D4)

def read_adc(channel):
    if not 0 <= channel <= 7:
        return -1
    r = spi.xfer2([1, (8 + channel) << 4, 0])
    return ((r[1] & 3) << 8) + r[2]

def get_voltage(adc_value, vref=3.3):
    return adc_value * vref / 1023

def get_rs(voltage, vcc=VCC, rl=RL_VALUE):
    return ((vcc - voltage) / voltage) * rl if voltage != 0 else float('inf')

def get_co2_ppm(rs, r0=R0, a=-0.42, b=1.92):
    try:
        ratio = rs / r0
        return 10 ** (a * math.log10(ratio) + b)
    except (ValueError, ZeroDivisionError):
        return None

def interpret_pm25(pm25):
    if pm25 <= 12: return "Good"
    elif pm25 <= 35.4: return "Moderate"
    elif pm25 <= 55.4: return "Unhealthy (for sensitive)"
    elif pm25 <= 150.4: return "Unhealthy"
    elif pm25 <= 250.4: return "Very Unhealthy"
    else: return "Hazardous"

def interpret_pm10(pm10):
    if pm10 <= 54: return "Good"
    elif pm10 <= 154: return "Moderate"
    elif pm10 <= 254: return "Unhealthy (for sensitive)"
    elif pm10 <= 354: return "Unhealthy"
    elif pm10 <= 424: return "Very Unhealthy"
    else: return "Hazardous"

def interpret_mq135_voltage(voltage):
    if voltage < 0.4: return "Low gas concentration"
    elif voltage < 1.0: return "Moderate gas concentration"
    elif voltage < 1.5: return "High gas concentration"
    else: return "Extreme gas concentration"

def calibrate_r0():
    print("... Calibrating R0 ...\n")
    values = []
    sample_count = 240  # 2 min
    for i in range(sample_count):
        adc_value = read_adc(0)
        voltage = get_voltage(adc_value)
        rs = get_rs(voltage)
        values.append(rs)
        time.sleep(0.5)
    avg_rs = sum(values) / len(values)
    print(f"Calibrated R0 = {avg_rs:.2f}\n")

    try:
        with open("r0_value.txt", "w") as f:
            f.write(str(avg_rs))
    except Exception as e:
        print(f"(x) failed to save R0: {e}")

    return avg_rs

def send_to_firebase(pm25, pm10, mq_voltage, co2, temp_c, humidity):
    romania_tz = pytz.timezone('Europe/Bucharest')
    current_time = datetime.now(romania_tz)
    timestamp = current_time.isoformat()

    data = {
        "PM25": float(pm25) if pm25 is not None else "NaN",
        "PM10": float(pm10) if pm10 is not None else "NaN",
        "MQ135_voltage": round(mq_voltage, 2),
        "Estimated_CO2_ppm": round(co2, 2) if co2 is not None else "NaN",
        "Temperature_C": round(temp_c, 1) if temp_c is not None else "NaN",
        "Humidity_percent": round(humidity, 1) if humidity is not None else "NaN",
        "timestamp": timestamp
    }

    url = f"{FIREBASE_BASE_URL}/{session_id}.json"

    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print("Data sent to firebase successfully!")
        else:
            print("(x) firebase error:", response.status_code, response.text)
    except Exception as e:
        print("(x) exception while sending to firebase:", e)

# === MAIN ===
try:
    choice = 'n'
    if len(sys.argv) > 1:
        choice = sys.argv[1].strip().lower()

    if choice == "y":
        print("... Warming up MQ135 sensor ...")
        time.sleep(20 * 60)  #20 min
        R0 = calibrate_r0()
        print()
    else:
        if os.path.isfile("r0_value.txt"):
            try:
                with open("r0_value.txt", "r") as f:
                    R0 = float(f.read().strip())
                    print(f"Loaded saved R0 = {R0:.2f}")
            except Exception as e:
                print(f"(x) could not load saved R0: {e}")
        else:
            print("No saved R0 found, using default.")

    print("... Gathering Air Quality Data ...")
    while True:
        print()

        # --- SDS011 ---
        data = ser.read(10)
        if len(data) >= 6:
            pm25 = int.from_bytes(data[2:4], byteorder='little') / 10
            pm10 = int.from_bytes(data[4:6], byteorder='little') / 10
            pm25_status = interpret_pm25(pm25)
            pm10_status = interpret_pm10(pm10)
        else:
            pm25 = None
            pm10 = None
            pm25_status = "No valid data"
            pm10_status = "No valid data"

        # --- MQ135 ---
        adc_value = read_adc(0)
        voltage_mq135 = get_voltage(adc_value)
        rs = get_rs(voltage_mq135)
        co2_ppm = get_co2_ppm(rs)
        mq135_status = interpret_mq135_voltage(voltage_mq135)

        # --- DHT11 ---
        try:
            temperature_c = dhtDevice.temperature
            humidity = dhtDevice.humidity
        except RuntimeError as error:
            temperature_c = None
            humidity = None
            print("DHT11 reading error:", error.args[0])

        # --- Console Print ---
        print(f"PM2.5: {pm25 if pm25 is not None else 'N/A'} ug/m3 - {pm25_status}")
        print(f"PM10: {pm10 if pm10 is not None else 'N/A'} ug/m3 - {pm10_status}")
        print(f"MQ135 Voltage: {voltage_mq135:.2f} V - {mq135_status}")
        print(f"Estimated CO2: {f'{co2_ppm:.0f} ppm' if co2_ppm else 'Calculation error'}")
        print(f"Temperature: {temperature_c}'C, Humidity: {humidity}%")
        
        if pm25 is not None and pm10 is not None:
            send_to_firebase(pm25, pm10, voltage_mq135, co2_ppm, temperature_c, humidity)

        time.sleep(1)

except KeyboardInterrupt:
    print("\nProgram stopped by user!")

except serial.SerialException as e:
    print(f"Serial port error: {e}")

finally:
    ser.close()
    spi.close()
