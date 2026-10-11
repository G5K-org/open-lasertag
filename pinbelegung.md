# Pinbelegung

Konkretisiert [readme.md](readme.md) Abschnitt 2 und 8 sowie Phase 0 aus [roadmap.md](roadmap.md).
Als Schaltplan umgesetzt in [kicad/waffe_elektronik/](kicad/waffe_elektronik/waffe_elektronik.kicad_sch)
(KiCad 10, ERC-geprüft) – siehe dort die README für Hinweise zum Öffnen.

Nur noch **ein Chip** (ESP32-S3, in der Waffe) – die Weste hat keine eigene
Elektronik mehr, nur TSOP-Sensoren am Sensorkabel.

---

## Waffe – ESP32-S3 (zentrale Elektronik)

**Modul: ESP32-S3-WROOM-1-N16R8** direkt auf der Platine, mit eigener USB-C-Buchse
am nativen USB (Flashen, Debuggen, Laden).

Zuordnung layoutgetrieben: Reihenfolge der Modul-Pads entspricht der Lage der Ziele auf
der Platine (kreuzungsfreies Routing).

**Gesperrte Pins** (nicht verwenden): `GPIO0, 3, 19, 20, 43, 44, 45, 46`.
`GPIO33–37` ebenfalls freilassen.

| Funktion | GPIO | Hinweis |
|---|---|---|
| Abzug (Trigger) | GPIO4 | Eingang, RC-Entprellung 10 kΩ + 100 nF |
| Nachladen (Reload) | GPIO5 | Eingang, RC-Entprellung |
| IR-LED MOSFET-Gate | GPIO6 | RMT-Ausgang |
| Rückstoß-Vibration | GPIO48 | PWM/LEDC, eigener MOSFET + Freilaufdiode |
| Akkuspannung | GPIO8 | ADC1_CH7 |
| I²C SDA (nur falls OLED statt LED-Zeile) | GPIO1 | |
| I²C SCL (nur falls OLED statt LED-Zeile) | GPIO2 | |
| Treffer-Vibration | GPIO47 | PWM/LEDC |
| TSOP 1 – Stirnband vorn | GPIO10 | RMT-Eingang, über Sensorkabel |
| TSOP 2 – Stirnband hinten | GPIO11 | RMT-Eingang |
| TSOP 3 – Brust | GPIO12 | RMT-Eingang |
| TSOP 4 – Rücken | GPIO13 | RMT-Eingang |
| TSOP 5 – Schultern (optional) | GPIO14 | RMT-Eingang |
| TSOP 6 – Waffe vorne | GPIO21 | RMT-Eingang, direkt an der Waffe (nicht über Sensorkabel) |
| WS2812 Data | GPIO17 | über Pegelwandler (3,3→5 V, 74AHCT125) + 330 Ω; VDD über kleinen 5-V-Boost-Converter vom 1S-LiPo |
| USB-C Lade-Status | GPIO18 | Eingang vom CHRG/STAT-Pin des Lade-ICs (TP4056/MCP73831), interner Pullup |
| I²S DOUT | GPIO38 | zu MAX98357A |
| I²S BCLK | GPIO39 | zu MAX98357A |
| I²S LRCLK/WS | GPIO40 | zu MAX98357A |
| Munitionszähler-LED-Zeile (falls kein OLED) | GPIO1/GPIO2 | |
| USB D− / D+ | GPIO19 / GPIO20 | nativer USB (USB-Serial-JTAG), über ESD-Schutz an die USB-C-Buchse |
| BOOT-Taster | GPIO0 | Download-Modus, nur als Rückfallebene nötig |
| RESET | EN | 10 kΩ Pull-up + 1 µF, RESET-Taster |
| — frei für Erweiterungen — | GPIO7, 9, 15, 16, 41, 42 | |

---

## Weste – nur Sensoren

Keine Elektronik, kein Chip. Nur die TSOPs mit ihrer lokalen Beschaltung
(100 Ω + 4,7 µF je Sensor) und das Sensorkabel zur Waffe.

---

## Offene Fragen für den Praxistest

- RMT-Kanäle: 4 TX + 4 RX – bei 6 TSOPs ggf. einen Sensor per Software-Timer
  statt RMT auswerten, oder bei 4 Sensoren bleiben
- I²S-SD-Pin des MAX98357A fest auf 5V_PERIPH, GAIN_SLOT fest auf GND
- TSOP 6 (Waffe vorne, GPIO21) ist noch nicht im Schaltplan
