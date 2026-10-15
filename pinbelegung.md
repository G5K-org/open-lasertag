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

**Gesperrte Pins** (nicht verwenden): `GPIO0, 19, 20, 43, 44, 45`.
`GPIO33–37` ebenfalls freilassen.

| Funktion | GPIO | Hinweis |
|---|---|---|
| Abzug (Trigger) | GPIO4 | Eingang, RC-Entprellung 10 kΩ + 100 nF |
| Nachladen (Reload) | GPIO5 | Eingang, RC-Entprellung |
| IR-LED MOSFET-Gate | GPIO6 | RMT-Ausgang |
| Akkuspannung | GPIO8 | ADC1_CH7 |
| I²C SCL – OLED | GPIO1 | J4 Pin 4 (Qwiic: GND, 3V3, SDA, SCL), Pull-ups auf dem OLED-Modul |
| I²C SDA – OLED | GPIO2 | J4 Pin 3 |
| Drehgeber A | GPIO42 | J5 Pin 4 (GND, Taster, B, A), interner Pull-up |
| Drehgeber B | GPIO41 | J5 Pin 3, interner Pull-up |
| Drehgeber Taster | GPIO21 | J5 Pin 2 über D6 (BAT54CW, Anode 2), interner Pull-up; der Taster ist zugleich der Ein/Aus-Taster (IP5306 KEY) |
| Vibrationsmotor (Rückstoß + Treffer) | GPIO47 | PWM/LEDC, MOSFET + Freilaufdiode, Stecker M1 |
| TSOP 1 – Stirnband vorn | GPIO10 | RMT-Eingang, über Sensorkabel; TSOP 1–5 je über 100 Ω (R30–R34) an J2 |
| TSOP 2 – Stirnband hinten | GPIO11 | RMT-Eingang |
| TSOP 3 – Brust | GPIO12 | RMT-Eingang |
| TSOP 4 – Rücken | GPIO13 | RMT-Eingang |
| TSOP 5 – Schultern (optional) | GPIO14 | RMT-Eingang |
| TSOP 6 – an der Waffe | GPIO16 | J6 (1 VS, 2 GND, 3 OUT), Filter 100 Ω + 4,7 µF am Sensor; GPIO-Interrupt |
| WS2812 Data | GPIO17 | über Pegelwandler (3,3→5 V, 74HCT125) + 330 Ω; VDD 5 V vom IP5306 |
| I²C SCL – IP5306 | GPIO18 | eigener Bus zum Lade-/Boost-IC U1 (Adresse 0x75), 4,7 kΩ Pull-up R40 |
| I²C SDA – IP5306 | GPIO9 | 4,7 kΩ Pull-up R38 |
| I²S DOUT | GPIO38 | zu MAX98357A |
| I²S BCLK | GPIO39 | zu MAX98357A |
| I²S LRCLK/WS | GPIO40 | zu MAX98357A |
| Flash /CS | GPIO7 | SPI-NAND U14 (ZD35Q1GC-IB, 128 MB), SPI2 über GPIO-Matrix, 10 kΩ Pull-up |
| microSD /CS | GPIO48 | Slot J7 (TF-018) am selben Bus, interner Pull-up |
| SPI MISO | GPIO15 | U14 DO, J7 DAT0 (interner Pull-up) |
| SPI MOSI | GPIO3 | U14 DI, J7 CMD (Strapping-Pin, JTAG-eFuse bleibt ungebrannt) |
| SPI CLK | GPIO46 | U14 CLK, J7 CLK (Strapping-Pin, beim Booten low über internen Pull-down) |
| USB D− / D+ | GPIO19 / GPIO20 | nativer USB (USB-Serial-JTAG), über ESD-Schutz an die USB-C-Buchse |
| BOOT-Taster | GPIO0 | Download-Modus, nur als Rückfallebene nötig |
| RESET | EN | 10 kΩ Pull-up + 1 µF, RESET-Taster |

Firmware Ein/Aus und Laden (IP5306-I2C, Register lesen → Bit ändern → zurückschreiben, bei jedem Start):
- `0x00` Bit 1 = 1 (keine Abschaltung bei kleiner Last), Bit 0 = 1 (Ausschalten per Taster)
- `0x01` Bit 7 = 1 (Aus = 2 s drücken statt Doppelklick), Bit 2 = 1 (5 V bleiben nach dem Abziehen von USB)
- `0x24` Ladestrom auf der USB-Seite: `0x10` ≈ 1,65 A (≈ 2 A in den Akku)
- `0x70` Bit 3 = lädt, `0x71` Bit 3 = voll
- Ausschalten aus der Firmware: `0x00` Bit 1 = 0, dann Deep Sleep; der IP5306 schaltet nach 8 s kleiner Last ab
  (`0x02` Bit 3:2 = 00)

GPIO8 misst die Akkuspannung direkt an der Zelle (Teiler 1 MΩ / 1 MΩ).

Firmware am SPI-Bus: die microSD-Karte zuerst initialisieren (CMD0 mit /CS low → SPI-Modus), erst danach
den Flash ansprechen; interne Pull-ups an GPIO48 (SD /CS) und GPIO15 (MISO) einschalten.

---

## Weste – nur Sensoren

Keine Elektronik, kein Chip. Nur die TSOPs mit ihrer lokalen Beschaltung
(100 Ω + 4,7 µF je Sensor) und das Sensorkabel zur Waffe.

---

## Offene Fragen für den Praxistest

- RMT-Kanäle: 4 TX + 4 RX – bei 6 TSOPs ggf. einen Sensor per Software-Timer
  statt RMT auswerten, oder bei 4 Sensoren bleiben
- I²S-SD-Pin des MAX98357A fest auf 5V_PERIPH, GAIN_SLOT fest auf GND
