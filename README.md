````
 ## Raspberry Pi + MQTT

 ### Specifikation

Projektet består av flera Raspberry Pi-system som kommunicerar med varandra via MQTT och kursens MQTT-broker.

Varje Raspberry Pi-system har:

- 2 brytare
- 2 lysdioder
- MQTT-kommunikation

En av Raspberry Pi-enheterna har även en temperaturindikator som är konstruerad med hjälp av en MCP6271-komparator.

 ### Användning

```bash
python3 -m venv .venv

source .venv/bin/activate

pip3 install paho-mqtt gpiozero rpi-lgpio

python3 main.py
```
