# Lasertag-System (Eigenbau) – Planung

Infrarot-Lasertag mit ESP32 für eine große Lagerhalle mit Metallregalen und Ubiquiti-Mesh-WLAN.
Stand: 08.10.2026

---

## 1. Grundentscheidungen

| Thema | Entscheidung | Grund |
|---|---|---|
| Strahl | **IR-LED 940 nm + Linse**, kein echter Laser | Augensicherheit, ausreichende Reichweite |
| Empfänger | **TSOP34838** (Tageslichtfilter) | robuste Dekodierung, 38 kHz |
| Aufteilung | **Weste (ESP32-S3)** + **Waffe (ESP32-C3)**, per Kabel verbunden | kleine, billige Waffe; ein Funkgerät und ein Akku pro Spieler |
| Verbindung Waffe–Weste | **LAN-Patchkabel (Litze)** als Träger für UART + 5 V | 4 verdrillte Paare, verriegelnde Stecker, billig |
| Netz | **WLAN + UDP** zu einem Server | Halle hat überall guten Empfang |
| Spiellogik | **lokal in der Weste** (HP, Vibration, LEDs), Netz meldet nur nach | Spielgefühl unabhängig von WLAN-Latenz |
| ESP-NOW | vorerst **nicht** nutzen, nur Rettungsanker | Kanalbindung kollidiert mit UniFi-Mesh |

---

## 2. Architektur

```
[Waffe: ESP32-C3]  --LAN-Kabel (UART + 5V)--  [Weste: ESP32-S3]  --WLAN/UDP--  [Server]
 IR-LED, Abzug,                                TSOPs, LED-Streifen,             Punkte, Teams,
 Nachladen, Munition,                          Vibration, Sound,                Runden, Anzeige
 Rückstoß-Vibration                            Akku, Spiellogik
```

### Waffe (ESP32-C3, z. B. XIAO ESP32C3)
- IR-LED (TSAL6100 o. ä.) über N-MOSFET (AO3400 / IRLZ44N), Gate 100 Ω, Pulldown 100 kΩ
- 100–220 µF Elko direkt am MOSFET
- Abzug und Nachladen (Mikrotaster, RC-Entprellung 10 kΩ + 100 nF)
- Munitionszähler, optional LED-Zeile oder kleines OLED
- Rückstoß-Vibration (Motor über eigenen MOSFET, Freilaufdiode, PWM)

### Weste (ESP32-S3, z. B. XIAO ESP32S3 oder S3-DevKitC)
- 4–5 TSOP34838: Stirnband vorn/hinten, Brust, Rücken, Schultern
- Je Sensor 100 Ω + 4,7 µF direkt am VCC-Pin
- WS2812-Streifen (10 LEDs) für HP und Treffer, 330 Ω in der Datenleitung, 100–470 µF Elko
- Vibrationsmotor optional zusätzlich in der Weste
- I²S-Verstärker (MAX98357A) + Lautsprecher für Sounds
- 1S-LiPo oder geschützte 18650, Laderegler USB-C, Akkuspannung per ADC
- WLAN auf Core 0, IR-Auswertung auf Core 1 (Grund für den S3)

---

## 3. Kabel Waffe–Weste (LAN-Patchkabel, 8 Adern)

| Paar | Ader 1 | Ader 2 |
|---|---|---|
| A | TX (Weste → Waffe) | GND |
| B | RX (Waffe → Weste) | GND |
| C | 5 V | 5 V (parallel) |
| D | Reserve (Wake o. ä.) | GND |

Hinweise:
- **Nie in Netzwerkgeräte stecken** (5 V auf Ethernet-Pins). Auffällige Farbe, beschriften; alternativ M8/M12-Industriestecker.
- Flexibles Litzenkabel, Zugentlastung und Knickschutz an beiden Enden.
- UART 115200 Baud, 3,3-V-Pegel, bis ca. 2 m unkritisch.
- ESD-Schutz (TVS oder 100 Ω in Reihe) an den UART-Leitungen der Waffe.
- Warm-Plug: Waffe meldet beim Start `READY`, Weste wiederholt Kontakt bis zur Antwort.

### UART-Protokoll (Start-Byte, Länge, Daten, CRC8)
- Waffe → Weste: `SHOT`, `RELOAD`, `AMMO n`, `READY`
- Weste → Waffe: `ENABLE` / `DISABLE`, `AMMO_SET n`, `HIT_FX`, `TEAM/ID`

---

## 4. IR-Protokoll und Trefferlogik

- NEC über `irsend.encodeNEC(address, command)`: Adresse = Team, Command = Spieler-ID
  (Korrektur: einfaches `(TEAM << 8) | ID` wird vom Dekoder meist verworfen)
- Optional später eigenes kürzeres Protokoll (**38 kHz** beibehalten – TSOP34838 ist fest auf 38 kHz gefiltert, 56 kHz würde kaum noch erkannt; 2 Bit Team, 6 Bit ID, Parität)
- Treffer nur zählen bei: Team ungleich eigenem Team (Friendly Fire als Schalter), 2 gültige Pakete innerhalb 100 ms, Wiederholcodes ignorieren
- 500 ms Unverwundbarkeit nach Treffer (kommerzielle Systeme nutzen meist 1,5–3 s; Wert im Praxistest gegen Mehrfachtreffer prüfen)
- Während des Sendens Empfang pausieren, eigene ID ignorieren
- Kein `delay()`, alles mit `millis()` oder FreeRTOS-Tasks
- Zonenerkennung (Kopf/Arm/Bein) ist mit der Strahlbreite **nicht sinnvoll**; Kopf-Bonus eher über Regeln

### Reichweite (IR)
- Linse Ø 25 mm, f ≈ 40–50 mm, LED knapp hinter dem Brennpunkt
- Spitzenstrom 150–300 mA gepulst (Datenblatt beachten), Tastgrad 25–33 %
- Zwei LEDs **parallel** mit eigenen Vorwiderständen (nicht in Reihe an 1S-LiPo)
- Schuss 2× kurz hintereinander senden
- Ziel: 30–50 m frei, in Gängen durch Sichtlinie begrenzt

---

## 5. Netzwerk (UniFi-Mesh, WLAN/UDP)

- Eigene SSID nur 2,4 GHz, eigenes VLAN, Band-Steering aus
- Feste Kanäle (1/6/11) und Auto-Optimize während des Spiels aus
- Minimum RSSI ca. -75 dBm, DTIM 1, 802.11r für diese SSID eher aus
- Server und möglichst viele APs per Kabel anbinden
- Weste: `WiFi.setSleep(false)` bzw. `WIFI_PS_NONE`, statische IP, keine Scans im Spiel
- UDP-Pakete mit Laufnummer, Treffer 2× senden, bei Aussetzern puffern und nachsenden
- Pakete mit Shared-Secret/HMAC absichern (gemeinsames WLAN, sonst leicht fälschbare Trefferpakete)
- Eigene Roaming-Logik: RSSI alle 1–2 s prüfen, unter ca. -75 dBm gezielt wechseln
- Latenzmessung: Zeitstempel + Echo vom Server, RTT pro Hallenzone loggen
- Erwartung: 3–15 ms, Ausreißer bis 200 ms bei Roaming

### Server
- UDP-Listener als eigener asyncio-`DatagramProtocol` (FastAPI selbst hört nicht nativ auf UDP, nur für WebSocket/Live-Anzeige daneben nutzen), Deduplizierung über (Spieler-ID, Laufnummer)
- Teams, Punkte, Runden, Respawn-Freigabe
- Live-Anzeige als Webseite (WebSocket)

---

## 6. Anzeige und Feedback

- **Lebensanzeige:** WS2812-Streifen, 1 LED = 10 % HP, grün → gelb → rot, unter 20 % blinken
- **Treffer:** Vibration 200–300 ms, weißer Blitz 150 ms, Treffer-Ton, Richtung über Sensor-Segment
- **Tod:** rot pulsierend bis Respawn, langes Vibrationsmuster
- **Team:** Rückenleuchte in Teamfarbe
- Lokale Anzeige zuerst, Netzmeldung danach
- Helligkeit begrenzen (`setBrightness(60)`), Diffusor über den LEDs

---

## 7. Risiken und Gegenmaßnahmen

| Risiko | Maßnahme |
|---|---|
| WLAN stört IR-Empfang | S3 mit Core-Trennung, RC-Filter am TSOP, ggf. RMT-Empfang |
| Reflexionen an Regalen/Folie | 2 gültige Pakete, früh an Gangkreuzungen testen |
| PWM-gedimmte Hallenbeleuchtung stört/blendet TSOP | früh unter realer Beleuchtung testen, ggf. Dimmfrequenz der Lampen prüfen |
| Spannungseinbruch beim IR-Puls | Elko am MOSFET, ausreichend dicke Adern |
| Kabelbruch | Litzenkabel, Zugentlastung, Knickschutz, Steckverbinder mit Rastung |
| Augen | IR-LED-Datenblatt und IEC 62471 prüfen, nicht aus der Nähe in die Optik schauen |
| LiPo in der Halle | Schutzschaltung, geschütztes Laden (LiPo-Beutel), nie unbeaufsichtigt |
| Unfallgefahr | nur gehen, Schutzschuhe, Staplerbereiche sperren |
| Organisation | Chef, Versicherung, ggf. Betriebsrat vorher klären |

---

## 8. ESP32-Wahl (Kurzfassung)

| Chip | Eignung |
|---|---|
| ESP32-S3 | **Weste:** 2 Kerne, viele GPIOs, IR sauber getrennt vom WLAN |
| ESP32-C3 | **Waffe:** reicht, nur 1 Kern, ca. 13–15 nutzbare Pins |
| ESP32-C6 | mehr Pins/RAM als C3, aber ebenfalls 1 Kern |
| ESP32 (WROOM) | Plan B, älter und stromhungriger |

Befestigung: Platine mit Buchsenleisten und M3-Abstandshaltern oder gedruckte PETG-Halterung mit Schnappnasen, Antenne frei halten (≥ 10–15 mm Abstand zu Akku und Metall), USB-Zugang einplanen.

---

## 9. Vorgehen (Reihenfolge)

1. Ein Paar Weste + Waffe auf dem Tisch, nur IR: Reichweite und Fehltreffer messen
2. IR-Stresstest (1000 Schüsse bei laufendem WLAN und LED-Animation, Ziel ≥ 99 %)
3. UART-Protokoll Waffe ↔ Weste
4. WLAN/UDP zum Server, RTT pro Hallenzone loggen
5. Spiellogik (Teams, HP, Respawn, Runden) auf dem Server
6. Optik- und Schaltungsoptimierung nach Messwerten
7. Danach weitere Westen, Sound, Extras

## 10. Offene Punkte

- Genaue Pinbelegung für S3 (Weste) und C3 (Waffe)
- Weste-Code (IR-Task Core 1, UDP, Puffer, Reconnect) und Server-Code
- Gehäuse/3D-Druck-Maße
- Akku-/Laufzeitbudget pro Weste (WLAN + WS2812 + Sound + IR-Pulse) für Eventplanung
- OTA-Update-Mechanismus für Weste (und Waffe über UART-Bridge) bei mehreren Sets
