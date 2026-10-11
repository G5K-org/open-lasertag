# Pinbelegung

Konkretisiert [readme.md](readme.md) Abschnitt 2 und 8 sowie Phase 0 aus [roadmap.md](roadmap.md).
Als Schaltplan umgesetzt in [kicad/waffe_elektronik/](kicad/waffe_elektronik/waffe_elektronik.kicad_sch)
(KiCad 10, ERC-geprüft) – siehe dort die README für Hinweise zum Öffnen.

Nur noch **ein Chip** (ESP32-S3, in der Waffe) – die Weste hat keine eigene
Elektronik mehr, nur TSOP-Sensoren am Sensorkabel.

---

## Waffe – ESP32-S3 (zentrale Elektronik)

**Board: ESP32-S3-DevKitC-1.**

**Gesperrte Pins** (nicht verwenden): `GPIO0, 3, 19, 20, 43, 44, 45, 46`.
`GPIO33–37` ebenfalls freilassen.

| Funktion | GPIO | Hinweis |
|---|---|---|
| IR-LED MOSFET-Gate | GPIO4 | RMT-Ausgang |
| Abzug (Trigger) | GPIO5 | Eingang, RC-Entprellung 10 kΩ + 100 nF |
| Nachladen (Reload) | GPIO6 | Eingang, RC-Entprellung |
| Rückstoß-Vibration | GPIO7 | PWM/LEDC, eigener MOSFET + Freilaufdiode |
| Akkuspannung | GPIO8 | ADC1_CH7 |
| I²C SDA (nur falls OLED statt LED-Zeile) | GPIO1 | |
| I²C SCL (nur falls OLED statt LED-Zeile) | GPIO2 | |
| Treffer-Vibration | GPIO11 | PWM/LEDC |
| TSOP 1 – Stirnband vorn | GPIO12 | RMT-Eingang, über Sensorkabel |
| TSOP 2 – Stirnband hinten | GPIO13 | RMT-Eingang |
| TSOP 3 – Brust | GPIO14 | RMT-Eingang |
| TSOP 4 – Rücken | GPIO15 | RMT-Eingang |
| TSOP 5 – Schultern (optional) | GPIO16 | RMT-Eingang |
| TSOP 6 – Waffe vorne | GPIO40 | RMT-Eingang, direkt an der Waffe (nicht über Sensorkabel) |
| WS2812 Data | GPIO17 | über Pegelwandler (3,3→5 V, 74AHCT125) + 330 Ω; VDD über kleinen 5-V-Boost-Converter vom 1S-LiPo |
| USB-C Lade-Status | GPIO18 | Eingang vom CHRG/STAT-Pin des Lade-ICs (TP4056/MCP73831), interner Pullup |
| I²S BCLK | GPIO21 | zu MAX98357A |
| I²S LRCLK/WS | GPIO38 | zu MAX98357A |
| I²S DOUT | GPIO39 | zu MAX98357A |
| Munitionszähler-LED-Zeile (falls kein OLED) | GPIO1/GPIO2 | |
| — frei für Erweiterungen — | GPIO9, 10, 41, 42 | |

---

## Weste – nur Sensoren

Keine Elektronik, kein Chip. Nur die TSOPs mit ihrer lokalen Beschaltung
(100 Ω + 4,7 µF je Sensor) und das Sensorkabel zur Waffe.

---

## Offene Fragen für den Praxistest

- RMT-Kanäle: 4 TX + 4 RX – bei 6 TSOPs ggf. einen Sensor per Software-Timer
  statt RMT auswerten, oder bei 4 Sensoren bleiben
- I²S-SD-Pin des MAX98357A fest auf 5V_PERIPH, GAIN_SLOT fest auf GND
- Exakte GPIO-Zuordnung gegen das tatsächlich bestellte DevKitC-Board
  verifizieren
