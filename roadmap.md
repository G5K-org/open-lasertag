# Roadmap

Phasenplan für das Lasertag-Projekt, aufbauend auf [readme.md](readme.md) Abschnitt 9 ("Vorgehen"). Jede Phase hat ein Exit-Kriterium, bevor zur nächsten übergegangen wird.

---

## Phase 0 – Vorbereitung

- [x] Pinbelegung für den einen ESP32-S3 (jetzt in der Waffe) festlegen → [pinbelegung.md](pinbelegung.md)
- [x] Schaltplan Waffen-Elektronik (ERC-geprüft) → [kicad/waffe_elektronik/](kicad/waffe_elektronik/waffe_elektronik.kicad_sch)
- Stückliste erstellen und bestellen: ESP32-S3-WROOM-1-N16R8, USB-C-Buchse (USB 2.0,
  16 Pin), USBLC6-2SC6, TSOP34838, IR-LEDs (TSAL6100 o. ä.), Linsen,
  MOSFETs (AO3400/IRLZ44N), WS2812(B)-Streifen (echte 5-V-Variante), MAX98357A,
  1S-LiPo/18650, Pegelwandler (74HCT125), kleiner 5-V-Boost-Converter,
  Lade-IC (TP4056-Modul mit Schutzschaltung oder MCP73831),
  GX12/GX16-Steckverbinder + Sensorkabel
- Organisatorisches klären: Chef, Versicherung, ggf. Betriebsrat

---

## Phase 1 – Prototyp (nur IR)

- Waffe (ESP32-S3) mit angeschlossenen TSOP-Sensoren der Weste auf dem Tisch aufbauen
- Power-Tree verifizieren: Laden über den nativen USB-C-Port (VBUS → Lade-IC),
  5-V-Boost-Converter, Pegelwandler für WS2812-Datenleitung
- Schusserkennung, Abzug, Nachladen, Munitionszähler
- Reichweite und Fehltreffer messen

**Exit:** Reichweite 30–50 m frei gemessen, Laden + 5-V-Rail funktionieren.

---

## Phase 2 – IR-Stresstest

- 1000 Schüsse bei laufendem WLAN und LED-Animation
- Test unter realer Hallenbeleuchtung (PWM-Flicker-Risiko)
- Reflexionstest an Regalen/Folie, früh an Gangkreuzungen

**Exit:** Erkennungsrate ≥ 99 %.

---

## Phase 3 – Sensorkabel Weste → Waffe

- GX12/GX16-Steckverbinder anschließen, TSOP-Signale auf RMT-Eingänge legen
- Kein Protokoll, nur GPIO/RMT-Einbindung in dieselbe Firmware, die auch sendet
- RMT-Kanalaufteilung bei mehr TSOPs als freien RX-Kanälen klären (siehe
  [pinbelegung.md, Offene Fragen für den Praxistest](pinbelegung.md#offene-fragen-für-den-praxistest))
- ESD-Schutz an den Sensorleitungen verifizieren

---

## Phase 4 – Netzwerk & Server-Grundgerüst

- WLAN-SSID/VLAN einrichten, feste Kanäle, Band-Steering aus
- Eigene Roaming-Logik auf dem ESP32 (RSSI-Check alle 1–2 s)
- UDP-Server (eigener asyncio-`DatagramProtocol`) mit Deduplizierung über (Spieler-ID, Laufnummer) und Shared-Secret/HMAC gegen gefälschte Pakete
- Latenzmessung: RTT pro Hallenzone loggen

**Exit:** RTT-Erwartung 3–15 ms bestätigt.

---

## Phase 5 – Spiellogik Server

- Teams, Punkte, Runden, Respawn-Freigabe
- Live-Anzeige als Webseite (WebSocket)

---

## Phase 6 – Feinschliff

- Optik- und Schaltungsoptimierung nach Messwerten
- Akku-/Laufzeitbudget messen (WLAN + WS2812 + Sound + IR-Pulse)
- Gewichtsverteilung der Waffe prüfen (Akku, Lautsprecher, LED jetzt alle dort)
- OTA-Update-Mechanismus für die Waffe einbauen

---

## Phase 7 – Skalierung

- Weitere Waffen (mit Weste/Sensoren) fertigen (Platinen, Gehäuse in Serie)
- Sound, Spielmodi, Extras
