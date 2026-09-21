#!/usr/bin/env python3
"""
Distribuerat Raspberry Pi-system för MQTT-baserad styrning av lysdioder och temperaturlarm
"""

import time
import threading
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

import config


# ============================================================
# GPIO-SETUP
# ============================================================

GPIO.setmode(GPIO.BCM)

# Buttons: pull-up means GPIO reads HIGH when released, LOW when pressed
GPIO.setup(config.SWITCH_2_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(config.SWITCH_1_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# LEDs: start LOW (off)
GPIO.setup(config.LED_1_GPIO, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(config.LED_2_GPIO, GPIO.OUT, initial=GPIO.LOW)

# Temperature alarm input (only read on the alarm Pi)
if config.HAS_TEMP_ALARM:
    GPIO.setup(config.TEMP_ALARM_GPIO, GPIO.IN)


# ============================================================
# STATE VARIABLES
# ============================================================

# Tracks whether the temperature alarm is active
alarm_active = False
alarm_lock = threading.Lock()

# Tracks the last published button value (prevents duplicate MQTT sends)
last_button_value = None

# Controls the main loop
running = True


# ============================================================
# LED CONTROL
# ============================================================

def set_leds(message):
    """
    Turn LEDs on/off based on MQTT message (0-3).

    0 = neither switch
    1 = right switch
    2 = left switch
    3 = both switches
    """
    if message == "0":
        GPIO.output(config.LED_1_GPIO, GPIO.LOW)
        GPIO.output(config.LED_2_GPIO, GPIO.LOW)
    elif message == "1":
        GPIO.output(config.LED_1_GPIO, GPIO.HIGH)
        GPIO.output(config.LED_2_GPIO, GPIO.LOW)
    elif message == "2":
        GPIO.output(config.LED_1_GPIO, GPIO.LOW)
        GPIO.output(config.LED_2_GPIO, GPIO.HIGH)
    elif message == "3":
        GPIO.output(config.LED_1_GPIO, GPIO.HIGH)
        GPIO.output(config.LED_2_GPIO, GPIO.HIGH)


# ============================================================
# MQTT CALLBACKS
# ============================================================

def on_connect(client, userdata, flags, reason_code, properties):
    """Called automatically when connected to the MQTT broker."""
    if reason_code == 0:
        print("Ansluten till MQTT-broker!")
        client.subscribe(config.MQTT_LED_TOPIC)
        client.subscribe(config.MQTT_ALARM_TOPIC)
        print("Prenumerar på:")
        print(" -", config.MQTT_LED_TOPIC)
        print(" -", config.MQTT_ALARM_TOPIC)
    else:
        print("Kunde inte ansluta till MQTT.")
        print("Anledning:", reason_code)


def on_message(client, userdata, message):
    """Called automatically when an MQTT message is received."""
    topic = message.topic
    data = message.payload.decode("utf-8")
    print("MQTT:", topic, "->", data)

    # ---- Normal LED message (0-3) ----
    if topic == config.MQTT_LED_TOPIC:
        if data in ("0", "1", "2", "3"):
            # Only update LEDs if no alarm is active
            if not alarm_active:
                set_leds(data)
        else:
            print("Ogiltigt LED-meddelande:", data)

    # ---- Temperature alarm message ----
    elif topic == config.MQTT_ALARM_TOPIC:
        if data == "ALARM":
            start_alarm()
        elif data == "NORMAL":
            stop_alarm()


# ============================================================
# TEMPERATURE ALARM
# ============================================================

def start_alarm():
    """Activate LED blinking."""
    global alarm_active
    with alarm_lock:
        alarm_active = True
    print("TEMPERATURLARM AKTIV!")


def stop_alarm():
    """Stop blinking and reset LEDs."""
    global alarm_active
    with alarm_lock:
        alarm_active = False
    print("Temperatur normal.")
    GPIO.output(config.LED_1_GPIO, GPIO.LOW)
    GPIO.output(config.LED_2_GPIO, GPIO.LOW)


def alarm_blink_thread():
    """
    Blink both LEDs at 1 Hz while alarm_active is True.

    1 Hz = one complete ON/OFF cycle per second:
      0.5 s ON, 0.5 s OFF
    """
    while running:
        if alarm_active:
            GPIO.output(config.LED_1_GPIO, GPIO.HIGH)
            GPIO.output(config.LED_2_GPIO, GPIO.HIGH)
            time.sleep(config.BLINK_INTERVAL)
            GPIO.output(config.LED_1_GPIO, GPIO.LOW)
            GPIO.output(config.LED_2_GPIO, GPIO.LOW)
            time.sleep(config.BLINK_INTERVAL)
        else:
            time.sleep(0.1)


def temperature_thread():
    """
    Runs ONLY on the Pi with the temperature alarm connected.

    GPIO_MCP comes from the MCP6271 Vout.
    HIGH = alarm, LOW = normal.
    Publishes to the alarm topic only when the state changes.
    """
    last_state = None
    while running:
        current_state = (
            "ALARM" if GPIO.input(config.TEMP_ALARM_GPIO) == GPIO.HIGH
            else "NORMAL"
        )
        if current_state != last_state:
            client.publish(config.MQTT_ALARM_TOPIC, current_state)
            print("Temperaturstatus:", current_state)
            last_state = current_state
        time.sleep(config.TEMP_CHECK_INTERVAL)


# ============================================================
# PUBLISH BUTTON STATE
# ============================================================

def publish_button_status():
    """
    Read both buttons and publish the bitmask state via MQTT.

    Button wiring: pull-up resistors.
    GPIO.LOW = pressed, GPIO.HIGH = released.
    """
    right_pressed = GPIO.input(config.SWITCH_2_GPIO) == GPIO.LOW
    left_pressed = GPIO.input(config.SWITCH_1_GPIO) == GPIO.LOW

    if not right_pressed and not left_pressed:
        value = "0"
        msg = "Ingen knapp nedtryckt"
    elif right_pressed and not left_pressed:
        value = "1"
        msg = "Höger switch nedtryckt"
    elif not right_pressed and left_pressed:
        value = "2"
        msg = "Vänster switch nedtryckt"
    else:
        value = "3"
        msg = "Bägge switcharna nedtryckt"

    global last_button_value
    if value != last_button_value:
        client.publish(config.MQTT_LED_TOPIC, value)
        last_button_value = value
        print(msg)


# ============================================================
# MQTT CLIENT
# ============================================================

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message


# ============================================================
# STARTUP
# ============================================================

print("Ansluter till MQTT-broker...")
client.connect(config.MQTT_BROKER, config.MQTT_PORT)
client.loop_start()

# Start alarm blink thread
alarm_thread = threading.Thread(target=alarm_blink_thread, daemon=True)
alarm_thread.start()

# Start temperature thread (only on the alarm Pi)
if config.HAS_TEMP_ALARM:
    print("Denna Raspberry Pi har temperaturlarm.")
    temp_thread = threading.Thread(target=temperature_thread, daemon=True)
    temp_thread.start()
else:
    print("Denna Raspberry Pi har inget temperaturlarm.")

print("Systemet startat.")
print("Tryck on knapparna for att se MQTT-meddelanden.")
print()


# ============================================================
# MAIN LOOP
# ============================================================

try:
    while running:
        publish_button_status()
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nProgrammet avslutat...")

finally:
    running = False
    client.loop_stop()
    client.disconnect()
    GPIO.output(config.LED_1_GPIO, GPIO.LOW)
    GPIO.output(config.LED_2_GPIO, GPIO.LOW)
    GPIO.cleanup()
    print("Programmet avslutat.")
