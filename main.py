import adafruit_bme280
import adafruit_tsl2561
import analogio
import board
import busio
import ujson
import network
import time

from umqtt import MQTTClient
from machine import Pin

## Functions

def led_flip():
    """
Invert the state of the status LED.
    """
    global ledvalue
    ledvalue = not ledvalue

    if ledvalue:
        led.on()
    else:
        led.off()

def maprange(value, leftMin, leftMax, rightMin, rightMax):
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)

def mqtt_send (topic, message):
    client = MQTTClient ('iot-envsensor', 'MQTT_SERVER_HOSTNAME');
    client.connect()
    client.publish(topic, message)
    client.disconnect()

def sensor_read():
    """
Read the sensor values.
    """
    return bme280.temperature, bme280.pressure, bme280.humidity, tsl.lux

def wifi_configure():
    """
Perform initial (one-time) configuration of the WiFi adapter.
    """
    global wlan
    wlan = network.WLAN(network.STA_IF)
    wlan.config(dhcp_hostname='iot-envsensor')
    wlan.active(True)

def wifi_connect():
    """
If not presently connected, connect.
    """
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect('WIFI_SSID', 'WIFI_PASSWD')
        while not wlan.isconnected():
            pass

    print('network config:', wlan.ifconfig())

## Main program. Do the work.

calls = 0

# Initialize WiFi adapter
wlan = None
wifi_configure()

# Configure I2C bus and devices
i2c = busio.I2C (board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C (i2c)
tsl = adafruit_tsl2561.TSL2561(i2c)

tsl.integration_time = 1 # 101 ms

# Configure pins

led = Pin (0, Pin.OUT)
ledvalue = False

batt = analogio.AnalogIn(board.ADC)

# Main loop
while True:

    # Count calls
    calls = calls + 1
    if calls == 121:
        calls = 0

    print ('iteration: ', calls)

    # Reconnect wireless network if disconnected
    if not wlan.isconnected():
        wifi_connect()

    # Every 60 seconds - watchdog
    if ((calls % 60) == 0):
        watchdog = { 'device' : 'iot-envsensor', 'notify' : 'bark', 'uptime' : time.monotonic() }
        mqtt_send ('watchdog/devices', ujson.dumps(watchdog))

    # Every 120 seconds - battery
    if ((calls % 120) == 0):
        raw = batt.value
        percent = maprange(raw, 58000, 77400, 0, 100)
        formatted = { 'device' : 'iot-envsensor', 'level' : percent }
        mqtt_send ('status/battery', ujson.dumps(formatted))

    # Every 15 seconds - sensor run
    if ((calls % 15) == 0):
        reading = sensor_read()
        formatted = { 'temperature' : reading[0], 'pressure' : reading[1], 'humidity' : reading[2], 'light-level' : reading[3]}
        mqtt_send ('environment/SENSOR_LOCATION/data', ujson.dumps(formatted))

    # Flip LED
    led_flip()

    # Wait one second.
    time.sleep (1)
