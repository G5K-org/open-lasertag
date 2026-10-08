# Roadmap

Phasenplan für das Lasertag-Projekt, aufbauend auf [readme.md](readme.md) Abschnitt 9 ("Vorgehen"). Jede Phase hat ein Exit-Kriterium, bevor zur nächsten übergegangen wird.

---

## Phase 0 – Vorbereitung

- Genaue Pinbelegung für S3 (Weste) und C3 (Waffe) festlegen
- Stückliste erstellen und bestellen: TSOP34838, IR-LEDs (TSAL6100 o. ä.), Linsen, MOSFETs (AO3400/IRLZ44N), WS2812-Streifen, MAX98357A, 1S-LiPo/18650 + Laderegler, LAN-Patchkabel + Stecker
- Organisatorisches klären: Chef, Versicherung, ggf. Betriebsrat

---

## Phase 1 – Einzelpaar-Prototyp (nur IR)

- Weste + Waffe auf dem Tisch aufbauen
- Schusserkennung, Abzug, Nachladen, Munitionszähler
- Reichweite und Fehltreffer messen

**Exit:** Reichweite 30–50 m frei gemessen.

---

## Phase 2 – IR-Stresstest

- 1000 Schüsse bei laufendem WLAN und LED-Animation
- Test unter realer Hallenbeleuchtung (PWM-Flicker-Risiko)
- Reflexionstest an Regalen/Folie, früh an Gangkreuzungen

**Exit:** Erkennungsrate ≥ 99 %.

---

## Phase 3 – UART-Protokoll Waffe ↔ Weste

- Waffe → Weste: `SHOT`, `RELOAD`, `AMMO n`, `READY`
- Weste → Waffe: `ENABLE`/`DISABLE`, `AMMO_SET n`, `HIT_FX`, `TEAM/ID`
- Warm-Plug-Verhalten und ESD-Schutz an den UART-Leitungen verifizieren

---

## Phase 4 – Netzwerk & Server-Grundgerüst

- UniFi-SSID/VLAN einrichten, feste Kanäle, Band-Steering aus
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
- Akku-/Laufzeitbudget pro Weste messen (WLAN + WS2812 + Sound + IR-Pulse)
- OTA-Update-Mechanismus für Weste (und Waffe über UART-Bridge) einbauen

---

## Phase 7 – Skalierung

- Weitere Westen/Waffen fertigen (Platinen, Gehäuse in Serie)
- Sound, Spielmodi, Extras
