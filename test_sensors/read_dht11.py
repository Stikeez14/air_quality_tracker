import time
import board
import adafruit_dht

# Use DHT11 on GPIO4 (pin 7)
dhtDevice = adafruit_dht.DHT11(board.D4)

while True:
    try:
        temperature_c = dhtDevice.temperature
        humidity = dhtDevice.humidity
        print(f"Temp: {temperature_c}C, Humidity: {humidity}%")
    except RuntimeError as error:
        print("Reading error:", error.args[0])
    time.sleep(2)
