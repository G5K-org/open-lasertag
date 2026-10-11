# Lasertag-System (Eigenbau) – Planung

Infrarot-Lasertag mit ESP32 für eine große Lagerhalle mit Metallregalen und Ubiquiti-Mesh-WLAN.
Stand: 08.10.2026

---

## 1. Grundentscheidungen

| Thema | Entscheidung | Grund |
|---|---|---|
| Strahl | **IR-LED 940 nm + Linse**, kein echter Laser | Augensicherheit, ausreichende Reichweite |
| Empfänger | **TSOP34838** (Tageslichtfilter) | robuste Dekodierung, 38 kHz |
| Aufteilung | **Ein ESP32-S3 in der Waffe**, Weste trägt nur noch passive TSOP-Sensoren | ein Chip, ein Akku, ein Funkgerät pro Spieler – kein zweiter Mikrocontroller mehr nötig |
| Verbindung Weste–Waffe | **reines Sensorkabel** (3,3 V + GND + je 1 Ader pro TSOP) | Weste hat keine eigene Logik mehr, nur Rohsignale – kein USB/CDC/Protokoll nötig |
| Netz | **WLAN + UDP** zu einem Server | Halle hat überall guten Empfang |
| Spiellogik | **lokal in der Waffe** (HP, Vibration, LEDs, Sound), Netz meldet nur nach | Spielgefühl unabhängig von WLAN-Latenz |
| ESP-NOW | vorerst **nicht** nutzen, nur Rettungsanker | Kanalbindung kollidiert mit UniFi-Mesh |
| Firmware-Framework | **ESP-IDF, kein Arduino** – nur offizielle Espressif-Komponenten (RMT, I²S, led_strip, esp_wifi) | reine Arduino-Bibliotheken (IRremote, Adafruit_NeoPixel, FastLED) sind Drittanbieter |

---

## 2. Architektur

```
[Weste: nur Sensoren]  --Sensorkabel (TSOP + 3,3V/GND)-->  [Waffe: ESP32-S3]  --WLAN/UDP-->  [Server]
 4–5× TSOP34838                                             IR-LED, Abzug, Nachladen,          Punkte, Teams,
 (Stirnband, Brust,                                         Munition, Rückstoß-Vibration,       Runden, Anzeige
  Rücken, Schultern)                                        TSOP-Auswertung, WS2812,
                                                             Treffer-Vibration, I²S+Lautsprecher,
                                                             Akku, WLAN, Spiellogik
```

### Waffe (ESP32-S3, zentrale Elektronik – einziger Chip)
- IR-LED (TSAL6100 o. ä.) über N-MOSFET (AO3400 / IRLZ44N), Gate 100 Ω, Pulldown 100 kΩ
- 100–220 µF Elko direkt am MOSFET
- Abzug und Nachladen (Mikrotaster, RC-Entprellung 10 kΩ + 100 nF)
- Munitionszähler, optional LED-Zeile oder kleines OLED (für OLED gibt es keine
  offizielle Espressif-Bibliothek – eigener minimaler SSD1306-I²C-Treiber nötig,
  sonst LED-Zeile bevorzugen)
- Rückstoß-Vibration (Motor über eigenen MOSFET, Freilaufdiode, PWM)
- 4–5× TSOP34838-Signale von der Weste, lokale RMT-Auswertung
- WS2812(B)-Streifen, **echte 5-V-Variante** (HP/Treffer/Team-Farbe), jetzt
  **an der Waffe montiert**, nicht mehr am Körper sichtbar – bewusste
  Entscheidung, siehe [Abschnitt 6](#6-anzeige-und-feedback).
  **Spannungsumsetzung nötig:** kleiner **Boost-Converter** vom 1S-LiPo
  (3,7–4,2 V) auf 5 V für die VDD-Versorgung des Strips, plus **Pegelwandler**
  (z. B. 74AHCT125) zwischen 3,3-V-GPIO und Datenleitung, da WS2812(B) ~5-V-
  Logikpegel am DIN erwartet. Deutlich einfacher als eine 12-V-Lösung – ein
  kleiner 5-V-Boost reicht, kein 12-V-Wandler nötig.
- Zusätzlicher Vibrationsmotor für Treffer-Feedback (getrennt von der Rückstoß-Vibration oder gemeinsam genutzt, noch zu entscheiden)
- I²S-Verstärker (MAX98357A) + Lautsprecher für Sounds, kann denselben 5-V-Boost wie der WS2812-Strip mitnutzen (bessere Audioqualität als bei 3,3 V)
- 1S-LiPo oder geschützte 18650, Akkuspannung per ADC – jetzt im Waffengehäuse, Gewicht/Balance beachten (siehe Risiken)
- **Ladeelektronik USB-C:** nutzt **denselben USB-C-Port wie Flash/Debug** am
  DevKitC – VBUS/5V-Pin des Boards abgreifen und auf einen Lade-IC führen,
  z. B. **TP4056-Modul mit Schutzschaltung** (DW01A + FS8205, günstig und
  verfügbar) oder **MCP73831** für eine minimalere Eigenbau-Lösung. Kein
  zweiter Stecker nötig – der native USB-Port ist bereits als Device
  beschaltet und hat die nötigen CC1/CC2-Pulldowns, damit USB-C-Netzteile
  Spannung liefern (beim gewählten Board kurz verifizieren). Bei unprotected
  LiPo-Pouch-Zelle zusätzliche Schutzschaltung einplanen (bei geschützter
  18650 entfällt das). CHRG/STAT-Ausgang des Lade-ICs auf den
  Lade-Status-GPIO (siehe [pinbelegung.md](pinbelegung.md)) und/oder eine eigene LED.
  Laden während des Spielens (Last + Ladestrom gleichzeitig über denselben
  Port) ist mit einfachen Linearladern grundsätzlich möglich, aber nicht der
  Regelfall – für den Spielbetrieb eher Akku vorher laden.
- WLAN auf Core 0, IR-Auswertung auf Core 1 (Grund für den S3)

### Weste (nur Sensoren, keine eigene Elektronik)
- 4–5 TSOP34838: Stirnband vorn/hinten, Brust, Rücken, Schultern
- Je Sensor 100 Ω + 4,7 µF direkt am VCC-Pin, am Sensor selbst (nicht erst an der Waffe)
- Kein Chip, keine Platine – nur Sensoren und das Sensorkabel zur Waffe

---

## 3. Kabel Weste–Waffe (reines Sensorkabel, kein Protokoll)

Die Weste hat keinen eigenen Chip mehr – nur die TSOP-Sensoren. Das Kabel trägt
daher nur rohe Signale, keine Kommunikation zwischen zwei Mikrocontrollern.
Die gesamte USB-Host/CDC-Geschichte der Vorversion entfällt komplett: kein
Enumerations-Handshake, kein `SHOT`/`RELOAD`/`READY`-Nachrichtenprotokoll mehr
nötig – das sind jetzt einfache Funktionsaufrufe innerhalb einer einzigen
Firmware statt serialisierter Nachrichten zwischen zwei Geräten.

| Ader | Signal | Hinweis |
|---|---|---|
| 1 | 3,3 V | gemeinsame Versorgung aller TSOPs |
| 2 | GND | gemeinsame Masse (Rückleiter für alle Signale) |
| 3 | TSOP 1 – Stirnband vorn | |
| 4 | TSOP 2 – Stirnband hinten | |
| 5 | TSOP 3 – Brust | |
| 6 | TSOP 4 – Rücken | |
| 7 | TSOP 5 – Schultern (optional) | |

Hinweise:
- Mind. 7 Adern (bei 5 Sensoren) – ein Standard-USB-C-Kabel reicht dafür nicht
  mehr (nur 4 nutzbare Adern). Stattdessen z. B. ein **GX12/GX16-Aviation-
  Steckverbinder** (Schraubverriegelung, 7–9-polig) oder ein mehradriges
  Sensorkabel mit passendem Stecker.
- **Locking-Steckverbinder wichtig**: anders als USB-C rastet so ein
  Aviation-Stecker durch die Schraubverriegelung – reduziert das Risiko von
  Kontaktabriss bei Bewegung im Spiel.
- Je TSOP weiterhin 100 Ω + 4,7 µF direkt am Sensor, nicht erst an der Waffe.
- Kabel kurz halten, möglichst geschirmt – läuft jetzt näher am WLAN-Funk der
  Waffe vorbei als vorher.
- Kein Zeitkritischer Software-Anteil auf dieser Verbindung – reine
  GPIO/RMT-Eingänge, von derselben Firmware ausgewertet, die auch sendet.

---

## 4. IR-Protokoll und Trefferlogik

- NEC-Timing selbst über den offiziellen ESP-IDF **RMT-Treiber**
  (`driver/rmt_tx.h` / `rmt_rx.h`) encodieren/decodieren – keine Drittanbieter-
  Bibliothek wie IRremote; Adresse = Team, Command = Spieler-ID
  (Korrektur: einfaches `(TEAM << 8) | ID` wird vom Dekoder meist verworfen)
- Optional später eigenes kürzeres Protokoll (**38 kHz** beibehalten – TSOP34838 ist fest auf 38 kHz gefiltert, 56 kHz würde kaum noch erkannt; 2 Bit Team, 6 Bit ID, Parität)
- Treffer nur zählen bei: Team ungleich eigenem Team (Friendly Fire als Schalter), 2 gültige Pakete innerhalb 100 ms, Wiederholcodes ignorieren
- 500 ms Unverwundbarkeit nach Treffer (kommerzielle Systeme nutzen meist 1,5–3 s; Wert im Praxistest gegen Mehrfachtreffer prüfen)
- Während des Sendens Empfang pausieren, eigene ID ignorieren
- Kein blockierendes Warten – FreeRTOS-Tasks mit `vTaskDelay()`/`esp_timer_get_time()` statt Busy-Loops
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
- Waffe: `esp_wifi_set_ps(WIFI_PS_NONE)` (offizielle ESP-IDF-API), statische IP, keine Scans im Spiel
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

Komplett an der Waffe montiert (WS2812-Streifen, Vibration, Lautsprecher) –
dadurch für andere Spieler schlechter sichtbar als eine Anzeige am Körper. Das
ist eine bewusste Folge davon, dass die Weste keinen Chip mehr trägt; falls
sich das im Praxistest als Problem zeigt, wäre eine spätere Erweiterung des
Sensorkabels um eine WS2812-Datenader für eine zusätzliche Rückenleuchte
möglich (siehe [Offene Punkte](#10-offene-punkte)).

- **Lebensanzeige:** WS2812-Streifen an der Waffe über das offizielle
  ESP-IDF-`led_strip`-Component (RMT-basiert, kein FastLED/Adafruit_NeoPixel),
  1 LED = 10 % HP, grün → gelb → rot, unter 20 % blinken
- **Treffer:** Vibration 200–300 ms (im Griff spürbar), weißer Blitz 150 ms, Treffer-Ton, Richtung über Sensor-Segment
- **Tod:** rot pulsierend bis Respawn, langes Vibrationsmuster
- **Team:** Lichtband an der Waffe in Teamfarbe (statt Rückenleuchte)
- Lokale Anzeige zuerst, Netzmeldung danach
- Helligkeit per Skalierungsfaktor in der `led_strip`-Pixel-Berechnung begrenzen (kein `setBrightness()` aus Arduino-Bibliotheken), Diffusor über den LEDs

---

## 7. Risiken und Gegenmaßnahmen

| Risiko | Maßnahme |
|---|---|
| WLAN stört IR-Empfang | S3 mit Core-Trennung, RC-Filter am TSOP, ggf. RMT-Empfang |
| Reflexionen an Regalen/Folie | 2 gültige Pakete, früh an Gangkreuzungen testen |
| PWM-gedimmte Hallenbeleuchtung stört/blendet TSOP | früh unter realer Beleuchtung testen, ggf. Dimmfrequenz der Lampen prüfen |
| Spannungseinbruch beim IR-Puls | Elko am MOSFET, ausreichend dicke Adern |
| Kabelbruch / Sensorkabel löst sich | Zugentlastung, GX12/GX16-Steckverbinder mit Schraubverriegelung statt loser Stecker |
| TSOP-Signale über längeres Kabel anfälliger für Störungen | kurz halten, geschirmt/verdrillt, RC-Filter direkt am Sensor (ohnehin vorgesehen) |
| Team-/HP-Anzeige an der Waffe schlechter sichtbar als am Körper | im Praxistest prüfen, ggf. Sensorkabel später um WS2812-Datenader erweitern |
| Gewicht/Balance der Waffe (Akku, Lautsprecher, LED jetzt alle dort) | früh mit Gesamtgewicht prototypisch testen, ggf. Akku in den Griff/Schaft verlegen |
| WS2812-Datensignal bei 3,3 V unzuverlässig | Pegelwandler (74AHCT125) einplanen; kleiner 5-V-Boost-Converter als zusätzliche Störquelle nahe WLAN/TSOP beachten |
| Augen | IR-LED-Datenblatt und IEC 62471 prüfen, nicht aus der Nähe in die Optik schauen |
| LiPo in der Halle | Schutzschaltung, geschütztes Laden (LiPo-Beutel), nie unbeaufsichtigt |
| Unfallgefahr | nur gehen, Schutzschuhe, Staplerbereiche sperren |
| Organisation | Chef, Versicherung, ggf. Betriebsrat vorher klären |

---

## 8. ESP32-Wahl (Kurzfassung)

| Chip | Eignung |
|---|---|
| ESP32-S3 | **Einziger Chip, jetzt in der Waffe:** 2 Kerne, genug GPIOs für TSOPs + WS2812 + I²S + Steuerung, IR sauber getrennt vom WLAN |
| ESP32-C3 SuperMini (vorhanden) | **nicht mehr im Einsatz** – im Zweichip-Design für die Waffe geplant, jetzt als Ersatzteil/zweiter Prototyp aufheben |
| ESP32-C6 | entfällt (war Alternative zum C3) |
| ESP32 (WROOM) | entfällt (war Plan B zum S3) |

Befestigung: Platine mit Buchsenleisten und M3-Abstandshaltern oder gedruckte PETG-Halterung mit Schnappnasen, Antenne frei halten (≥ 10–15 mm Abstand zu Akku und Metall), USB-Zugang einplanen.

---

## 9. Vorgehen (Reihenfolge)

1. Waffe mit angeschlossenen TSOP-Sensoren auf dem Tisch, nur IR: Reichweite und Fehltreffer messen
2. IR-Stresstest (1000 Schüsse bei laufendem WLAN und LED-Animation, Ziel ≥ 99 %)
3. Sensorkabel Weste → Waffe verlegen und auswerten (reine GPIO/RMT-Einbindung, kein Protokoll)
4. WLAN/UDP zum Server, RTT pro Hallenzone loggen
5. Spiellogik (Teams, HP, Respawn, Runden) auf dem Server
6. Optik- und Schaltungsoptimierung nach Messwerten
7. Danach weitere Westen, Sound, Extras

## 10. Offene Punkte

- Genaue Pinbelegung für den einen ESP32-S3 (jetzt in der Waffe)
- Waffe-Code (IR-Task Core 1, TSOP-Auswertung, UDP, Puffer, Reconnect) und Server-Code
- Gehäuse/3D-Druck-Maße, inkl. Platz für Akku/Lautsprecher/LED in der Waffe –
  als Basis ausgewählt: [MP5 Toygun Cosplay](https://makerworld.com/de/models/427808-mp5-toygun-cosplay)
  (STLs + Quellenangabe in [gehaeuse/mp5_toygun_stls/](gehaeuse/mp5_toygun_stls/)).
  Reine Deko-Requisite ohne Funktionsteile – muss für Elektronik-Einbau
  ausgehöhlt/angepasst werden.
- Akku-/Laufzeitbudget (WLAN + WS2812 + Sound + IR-Pulse) für Eventplanung
- OTA-Update-Mechanismus für die Waffe bei mehreren Sets
- ESP-IDF-Projektstruktur (Komponenten-Repo, CI-Build) statt Arduino-Sketches
- Server bleibt bewusst außerhalb der "nur Espressif"-Vorgabe – betrifft nur die ESP32-Firmware, nicht den Python/Node-RED-Server
- Steckverbinder für das Sensorkabel festlegen (z. B. GX12/GX16, Polzahl nach TSOP-Anzahl)
- Gewichtsverteilung der Waffe mit Gesamt-BOM früh real nachbauen/wiegen

---

## 11. Android-App und Server (Basis: open-laser-tag)

Als normale Verzeichnisse ins Projekt übernommen (nicht als Submodule) –
Ausgangspunkt für die Weiterentwicklung der eigenen App und des eigenen
Servers, ursprünglich GPL-3.0 von [open-laser-tag](https://github.com/open-laser-tag):

- [android-app/](android-app/) – BLE- und WebSocket-Client (Basis:
  [open-laser-tag/android-app](https://github.com/open-laser-tag/android-app)),
  wird zur geplanten Live-Anzeige/Steuerung weiterentwickelt
- [server/](server/) – node.js-Server mit WebSocket (Basis:
  [open-laser-tag/server](https://github.com/open-laser-tag/server)), wird zum
  eigenen UDP/WebSocket-Server (Abschnitt 5) weiterentwickelt

Da GPL-3.0-Code übernommen wurde, bleibt eine eigene Veröffentlichung dieser
beiden Teile ebenfalls GPL-3.0-pflichtig.
