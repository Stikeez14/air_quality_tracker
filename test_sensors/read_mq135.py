import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)  # SPI bus 0, device 0 (CE0)
spi.max_speed_hz = 1350000

def read_adc(channel):
    if not 0 <= channel <= 7:
        return -1
    # MCP3008 SPI transaction
    r = spi.xfer2([1, (8 + channel) << 4, 0])
    # Convert response to 10-bit value
    value = ((r[1] & 3) << 8) + r[2]
    return value

try:
    while True:
        adc_value = read_adc(0)  # MQ135 connected to CH0
        voltage = adc_value * 3.3 / 1023
        print(f"MQ135 ADC Value: {adc_value}, Voltage: {voltage:.2f} V")
        time.sleep(1)
except KeyboardInterrupt:
    spi.close()
    print("Program stopped")

