import serial
import time

# Configure serial port (adjust baudrate/port as needed)
ser = serial.Serial('/dev/ttyUSB0', baudrate=9600, timeout=1)

try:
    while True:
        # Read 10 bytes in one go (adjust for your protocol)
        data = ser.read(10)
        
        if len(data) >= 6:  # Ensure enough bytes for PM2.5/PM10
            pm25 = int.from_bytes(data[2:4], byteorder='little') / 10
            pm10 = int.from_bytes(data[4:6], byteorder='little') / 10
            print(f"PM2.5: {pm25} μg/m³, PM10: {pm10} μg/m³")
        else:
            print("Incomplete data packet")
        
        time.sleep(1)  # Adjust delay as needed (or remove for max speed)

except KeyboardInterrupt:
    print("Stopping...")
except serial.SerialException as e:
    print(f"Serial error: {e}")
finally:
    ser.close()  # Always close the port!
