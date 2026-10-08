# Pinbelegung

Konkretisiert [readme.md](readme.md) Abschnitt 2 und 8 sowie Phase 0 aus [roadmap.md](roadmap.md).

Nur noch **ein Chip** (ESP32-S3, in der Waffe) – die Weste hat keine eigene
Elektronik mehr, nur TSOP-Sensoren am Sensorkabel.

---

## Waffe – ESP32-S3 (zentrale Elektronik)

**Empfehlung: ESP32-S3-DevKitC-1.** Rund 18 Signale (4–5× TSOP, IR-LED, Abzug,
Nachladen, Rückstoß-Vibration, Treffer-Vibration, Munitionszähler, WS2812,
I²S ×3, Akku-ADC, Lade-Status) – das XIAO-Board mit nur 11 GPIOs reicht nicht,
der ESP32-C3 SuperMini (für das alte Zweichip-Design vorgesehen) wird hier
nicht mehr verwendet.

**Gesperrte Pins** (nicht verwenden): `GPIO0, 3, 19, 20, 43, 44, 45, 46`
(Boot-Taster/Strapping, native USB D± fürs Flashen/Debuggen, Konsolen-UART0,
Strapping/Input-only). Vorsichtshalber auch `GPIO33–37` freilassen (bei
Modulen mit Octal-PSRAM intern belegt).

| Funktion | GPIO | Hinweis |
|---|---|---|
| IR-LED MOSFET-Gate | GPIO4 | RMT-Ausgang |
| Abzug (Trigger) | GPIO5 | Eingang, RC-Entprellung 10 kΩ + 100 nF |
| Nachladen (Reload) | GPIO6 | Eingang, RC-Entprellung |
| Rückstoß-Vibration | GPIO7 | PWM/LEDC, eigener MOSFET + Freilaufdiode |
| Akkuspannung | GPIO8 | **ADC1**_CH7 – einziger für Analogmessung reservierter Pin aus GPIO1–10, da ADC2 bei aktivem WLAN blockiert ist |
| I²C SDA (nur falls OLED statt LED-Zeile) | GPIO1 | sonst frei für Munitions-LED-Zeile |
| I²C SCL (nur falls OLED statt LED-Zeile) | GPIO2 | |
| Treffer-Vibration | GPIO11 | PWM/LEDC (getrennt von Rückstoß, falls zwei Motoren) |
| TSOP 1 – Stirnband vorn | GPIO12 | RMT-Eingang, über Sensorkabel |
| TSOP 2 – Stirnband hinten | GPIO13 | RMT-Eingang |
| TSOP 3 – Brust | GPIO14 | RMT-Eingang |
| TSOP 4 – Rücken | GPIO15 | RMT-Eingang |
| TSOP 5 – Schultern (optional) | GPIO16 | RMT-Eingang |
| WS2812 Data | GPIO17 | über Pegelwandler (3,3→5 V, z. B. 74AHCT125) + 330 Ω in der Datenleitung; VDD über kleinen 5-V-Boost-Converter vom 1S-LiPo, siehe readme.md Abschnitt 2 |
| USB-C Lade-Status | GPIO18 | Eingang vom CHRG/STAT-Pin des Lade-ICs (z. B. TP4056-Modul oder MCP73831); Lade-IC hängt am VBUS desselben nativen USB-Ports, der auch zum Flashen dient – kein zweiter Stecker; Status-Pin meist Open-Drain/aktiv-Low, interner Pullup aktivieren |
| I²S BCLK | GPIO21 | zu MAX98357A |
| I²S LRCLK/WS | GPIO38 | zu MAX98357A |
| I²S DOUT | GPIO39 | zu MAX98357A |
| Munitionszähler-LED-Zeile (falls kein OLED) | GPIO1/GPIO2 | nutzt die sonst freien I²C-Pins |
| — frei für Erweiterungen — | GPIO9, 10, 40, 41, 42 | u. a. zwei weitere ADC1-fähige Pins (GPIO9/10) als Reserve |

---

## Weste – nur Sensoren

Keine Elektronik, kein Chip. Nur die TSOPs mit ihrer lokalen Beschaltung
(100 Ω + 4,7 µF je Sensor) und das Sensorkabel zur Waffe (siehe readme.md
Abschnitt 3).

---

## Offene Fragen für den Praxistest

- RMT-Kanäle: ESP32-S3 hat 4 TX + 4 RX RMT-Kanäle – bei IR-LED (TX) + 5 TSOPs
  (RX) reicht ein RX-Kanal nicht für alle Sensoren gleichzeitig; ggf. einen
  Sensor per Software-Timer statt RMT auswerten, oder bei 4 Sensoren bleiben
- I²S-SD-Pin des MAX98357A (Shutdown/Gain) eher per Spannungsteiler fest verdrahten
  statt eigenen GPIO zu verbrauchen
- Exakte GPIO-Zuordnung nach ADC1/ADC2-Bereich und Strapping-Pins gegen das
  tatsächlich bestellte DevKitC-Board verifizieren (Pinout variiert leicht
  zwischen Revisionen)
