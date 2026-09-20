# ==========================================
# KONFIGURATION
# ==========================================

# ---------- KNAPPAR ----------
# GPIO-numren för de två knappar
# Knappar är wired med pull-up: GPIO.LOW = pressed, GPIO.HIGH = released

SWITCH_1_GPIO =
SWITCH_2_GPIO =


# ---------- LED ----------
# GPIO-numren för de två lysdioder

LED_1_GPIO =
LED_2_GPIO =


# ---------- TEMPERATURLARM ----------
# GPIO från MCP6271 Vout
TEMP_ALARM_GPIO =

# Sätt till True på den ENDA Raspberry Pi
# som faktiskt har temperaturlarmet anslutet.
#
# På övriga Raspberry Pi:
# HAS_TEMP_ALARM = False

HAS_TEMP_ALARM = True

# Hur ofta temperaturlarmets GPIO kontrolleras
TEMP_CHECK_INTERVAL = 0.1

# Blinkfrekvens:
# 1 Hz = en kompletten blinkcykel per sekund
BLINK_INTERVAL = 0.5

# ---------- MQTT ----------
MQTT_BROKER = "localhost"
MQTT_PORT = 1337

MQTT_USERNAME = ""
MQTT_PASSWORD = ""

# Topic som används enligt uppgiften
MQTT_LIGHT_TOPIC = ""

# Topic för temperaturlarmet
MQTT_ALARM_TOPIC = ""
