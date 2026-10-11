# ESP-NOW-Gateway

Brücke zwischen ESP-NOW und dem Server-PC. Fällt das WLAN aus, wechseln die
Waffen auf einen festen Kanal und schicken ihre Pakete per ESP-NOW an dieses
Gateway. Es hängt per USB am Server und reicht die Pakete in beide Richtungen
durch. Gedacht für den vorhandenen **ESP32-C3 SuperMini**, läuft aber auf jedem
ESP32 mit USB-Serial-JTAG (C3, S3, C6).

Das Gateway prüft die Pakete nicht und kennt den HMAC-Schlüssel nicht. Die
Signatur prüfen Waffe und Server.

## Bauen und Flashen

```sh
. ~/esp/esp-idf-v6.0.3/export.sh
cd gateway
idf.py menuconfig                    # "Lasertag Gateway": Kanal = LT_ESPNOW_CHANNEL der Waffen
idf.py -p /dev/ttyACM0 flash         # ESP32-C3 (Standard)
# anderes Board, z. B. S3:
idf.py -B build-s3 -D IDF_TARGET=esp32s3 -D SDKCONFIG=build-s3/sdkconfig -p /dev/ttyACM0 flash
```

Server dazu mit `--gateway /dev/ttyACM0` starten (siehe [../server/](../server/)).

## Serielles Protokoll

Eine Zeile pro Paket, hexadezimal:

| Richtung | Zeile |
|---|---|
| Waffe → Server | `LT:<MAC der Waffe>:<Paket>` |
| Server → Waffe | `LT:<MAC der Waffe oder ffffffffffff>:<Paket>` |

Alle anderen Zeilen sind Log-Ausgaben (z. B. `LT-GW: ready, channel 1, mac …`
beim Start). Weitergeleitet werden nur Waffe→Server-Pakete (Typ 0x01–0x0F).
Die Trefferbestätigungen zwischen den Waffen bleiben draußen. An bekannte
Waffen sendet das Gateway per Unicast (mit Quittung und Wiederholung auf
Funkebene), ab 20 Waffen per Broadcast.

## Hinweise

- Der Server setzt das Gateway beim Öffnen des Ports gezielt zurück (DTR aus,
  RTS-Puls), weil Linux beim Öffnen DTR/RTS setzt und der native USB des
  ESP32 das sonst als „in den Bootloader“ deuten kann. Der Neustart dauert
  ~0,3 s, Pakete in dieser Zeit wiederholen die Waffen.
- Hängt das Gateway trotzdem im Bootloader (`waiting for download` im
  Server-Log): `esptool --port <PORT> --after watchdog-reset chip-id`.
- Auf einem ESP32-S3 getestet: Waffe im Fallback ↔ Gateway ↔ Server in beide
  Richtungen, RTT ~22 ms.
- Kanal so wählen, dass er zu einem Access Point in der Nähe passt oder frei
  ist. Waffen im WLAN hören das Gateway nur, wenn ihr AP auf demselben Kanal
  funkt; im Fallback sitzen sie fest auf diesem Kanal.
