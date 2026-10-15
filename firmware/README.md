# Firmware Waffe (ESP-IDF)

Firmware für die Waffen-Platine ([../kicad/waffe_elektronik/](../kicad/waffe_elektronik/)),
Pins nach [../pinbelegung.md](../pinbelegung.md). ESP-IDF v6.0, nur offizielle
Espressif-Komponenten (RMT, I²S, LEDC, ADC, esp_wifi, `espressif/led_strip`).

## Bauen und Flashen

```sh
. ~/esp/esp-idf-v6.0.3/export.sh      # fish: . ~/esp/esp-idf-v6.0.3/export.fish
cd firmware
idf.py menuconfig                      # "Lasertag Waffe": WLAN, Server, Team/Spieler, Regeln
idf.py build
idf.py -p /dev/ttyACM0 flash monitor   # nativer USB-C der Platine
```

Hängt die Firmware oder belegt sie die USB-Pins: BOOT halten, RESET drücken,
dann flashen.

## Aufteilung

| Modul | Aufgabe | Kern |
|---|---|---|
| `ir_tx.c` | Schuss = NEC-Frame (Adresse = Team, Command = Spieler-ID) 2× mit 10 ms Pause, RMT mit 38-kHz-Träger an `IR_GATE` | – |
| `ir_rx.c` | TSOP 1–4 über die 4 RMT-RX-Kanäle, TSOP 5/6 über GPIO-Flanken-Interrupts mit µs-Zeitstempel; Empfang während des eigenen Schusses wird verworfen | 1 |
| `nec.c` | NEC-Codec, Toleranzen für TSOP-Verzerrung, Wiederholcodes werden ignoriert | – |
| `game.c` | HP, Munition, Nachladen, Treffer, Tod, Respawn; lokales Feedback zuerst, dann Meldung ans Netz | 1 |
| `input.c` | Abzug/Nachladen (aktiv low), 2-ms-Abfrage mit Entprellung | 1 |
| `leds.c` | WS2812-Kette (HP → Munition → Team → Ringlicht vorne): Mündungsfeuer auf dem Ring bei jedem Schuss (~120 ms, warm flackernd, eigene Helligkeitsgrenze), HP-Balken (grün → gelb → rot, blinkt unter 20 %), Munition, Teamfarbe; Treffer-Blitz, rotes Pulsieren als tot, Lade-/Akku-/Offline-Anzeige | 1 |
| `haptics.c` | Rückstoß- und Treffer-Motor per LEDC-PWM (20 kHz), Muster per `esp_timer` | – |
| `audio.c` | MAX98357A über I²S, Effekte synthetisch (keine Sound-Dateien) | 0 |
| `battery.c` | Akkuspannung (ADC1_CH7, Teiler 1:2, Kurven-Kalibrierung); IP5306 per I²C (IO18/IO9): Ladestrom 2 A am Ladegerät, 0,45 A bei Datenverbindung zum Rechner, Aus per 2 s Tastendruck, keine Abschaltung bei kleiner Last; Ladestatus; `battery_power_off()` | 0 |
| `net.c` | WLAN-STA ohne Power-Save, optional statische IP, eigenes Roaming (RSSI-Prüfung alle 1,5 s, Wechsel unter −75 dBm bei ≥ 8 dB besserem AP), UDP | 0 |
| `proto.c` | Paketformat + HMAC-SHA256 (PSA-API), auf 16 Byte gekürzt | – |
| `espnow.c` | ESP-NOW-Transport: Trefferbestätigung Waffe → Schütze, Fallback zum Server über das [Gateway](../gateway/) | 0 |

## Trefferregeln

- Eigene Spieler-ID wird immer ignoriert, eigenes Team ohne Friendly Fire auch.
- Ein Treffer braucht beide Frames eines Schusses innerhalb von 100 ms
  (`LT_HIT_CONFIRM_FRAMES`). Dasselbe Frame auf mehreren TSOPs zählt nur einmal.
- 500 ms unverwundbar nach einem Treffer.
- Ohne Server (`LT_STANDALONE`) läuft das Spiel sofort, Respawn lokal nach 10 s.

## ESP-NOW

Zwei Aufgaben (Menü „ESP-NOW“ in `menuconfig`):

- **Trefferbestätigung:** Die getroffene Waffe schickt dem Schützen per
  ESP-NOW-Broadcast `HIT_CONFIRM` (signiert wie alle Pakete). Der Schütze hört
  einen kurzen Bestätigungston, beim Abschuss einen Doppelton, und sein
  Munitionsbalken blitzt grün. Das geht ohne Server, aber nur zwischen Waffen
  auf demselben WLAN-Kanal.
- **Fallback zum Server:** Ist das WLAN länger als `LT_ESPNOW_FALLBACK_S`
  (5 s) weg, wechselt die Waffe auf `LT_ESPNOW_CHANNEL` und schickt ihre
  Pakete per ESP-NOW an das Gateway am Server. Treffer werden weiter bis
  zum ACK wiederholt. Alle `LT_ESPNOW_WIFI_RETRY_S` (20 s) versucht sie das WLAN
  erneut; während der Suche (~2 s) ist ESP-NOW taub. Im Status steht dann
  das Gateway als „Access Point“, die Weboberfläche markiert die Waffe mit
  „ESP-NOW“.

## UDP-Protokoll

Format in [`main/proto.h`](main/proto.h): 16-Byte-Header (Magic `LT`, Typ, Team,
Spieler, Länge, Session, Laufnummer) + Nutzdaten + 16 Byte HMAC. Waffe → Server:
`HELLO`, `STATUS` (1 s, mit RSSI, BSSID und RTT für die Messung pro Hallenzone),
`HIT`/`DEATH` (sofort 2×, dann alle 250 ms bis zum `ACK`, offline gepuffert),
`PING`. Waffe → Waffe: `HIT_CONFIRM` (nur ESP-NOW). Server → Waffe: `ACK`, `PONG`, `GAME_START` (Regeln), `GAME_STOP`,
`RESPAWN`, `SET_IDENTITY` (Team/Spieler, wird im NVS gespeichert).

Testserver:

```sh
python3 tools/udp_test_server.py --key change-me
# Eingaben: start | stop | respawn [spieler] | id <spieler> <team> <neue_id>
```

## Tests

```sh
gcc -I main test/test_nec.c main/nec.c -o /tmp/test_nec && /tmp/test_nec
```

## Offen / auf Hardware zu prüfen

- Alles nur gebaut, noch nicht auf der Platine getestet.
- TSOP 6 (an der Waffe, GPIO16, Stecker J6) wird wie TSOP 5 per GPIO-Interrupt ausgewertet.
- Pixelzahlen der WS2812-Kette (`LT_LEDS_*`) an die realen Streifen und den Ring anpassen.
- Stromspitze im Schuss (Ring + Rückstoß-Motor + Sound auf `5V_PERIPH`) am IP5306 messen (Akkuschutz trennt bei ca. 3 A),
  ggf. `LT_MUZZLE_BRIGHTNESS` senken.
- OTA: Partitionstabelle hat bereits zwei OTA-Slots, der Update-Weg fehlt noch.
