# waffe_elektronik – KiCad-Schaltplan

Schaltplan für die zentrale Elektronik der Waffe (einziger ESP32-S3-Chip),
passend zu [../../pinbelegung.md](../../pinbelegung.md) und
[../../readme.md](../../readme.md). KiCad 10, ERC-geprüft (0 Fehler).

![Schaltplan](renders/schaltplan.png)

## Öffnen

`waffe_elektronik.kicad_pro` in KiCad öffnen, dann den Schaltplan-Editor
starten. Die Bibliotheken sind über die mitgelieferte projekteigene
`sym-lib-table` eingebunden (nur Standard-KiCad-Bibliotheken, z. B. `Device`,
`Diode`, `Transistor_FET`, `74xx`, `power`).

## Aufbau

Ein A3-Blatt, in gestrichelt umrahmte Funktionsblöcke gegliedert:
Stromversorgung, Laden, Akku-Messung, Sound, ESP32-S3, IR-Sender,
Abzug/Nachladen, WS2812, Weste (Sensoren) und Vibration.

- Innerhalb eines Blocks ist alles mit echten Leitungen verdrahtet; Bauteile
  liegen auf dem Raster, Versorgung zeigt nach oben, Masse nach unten.
- Zwischen den Blöcken laufen Signale über Netz-Labels an kurzen
  Stichleitungen (z. B. `IR_GATE`, `TSOP1_OUT`) statt über lange Leitungen
  quer über das Blatt.
- Versorgungsnetze (`GND`, `3V3_MCU`, `5V_PERIPH`, `BAT_P`, `VBUS_NATIVE`)
  hängen an KiCad-Power-Symbolen.
- Unbenutzte Pins sind markiert: GPIO1/GPIO2 mit No-Connect-Kreuz, die drei
  freien Gatter des 74AHCT125 mit Eingang und `/OE` auf GND.

Der Schaltplan wird per Python ([kiutils][1]) erzeugt und mit
`kicad-cli sch erc` geprüft: 0 Fehler. Die Generator-Skripte gehören nicht
zum Repo.

[1]: https://github.com/mvnmgrx/kiutils

## Bauteile

Einziges Platzhalter-Symbol ist `U1`, der 5-V-Boost-Converter (MT3608-
Fertigmodul, Bibliothek `Module`). Alle anderen Bauteile sind echte Symbole
aus den KiCad-Standardbibliotheken, u. a. `ESP32-S3-WROOM-1` (`U4`),
`USB_C_Receptacle_USB2.0_16P` (`J3`), `USBLC6-2SC6`, `MCP73831-2-OT`,
`AMS1117-3.3`, `TSOP348xx`, `MAX98357A`, `AO3400A`, `74AHCT125`, `SS14`.

## Design-Entscheidungen im Schaltplan

- **ESP32-S3-WROOM-1 direkt auf der Platine** (kein DevKit):
  - 3V3 mit 100 nF + 10 µF direkt am Modul
  - EN mit 10 kΩ Pull-up und 1 µF (Power-on-Reset), dazu RESET-Taster
  - BOOT-Taster an IO0
- **USB-C (`J3`) am nativen USB des S3** (IO19/IO20 = USB_D−/USB_D+):
  - Flashen und serielle Konsole über den eingebauten USB-Serial-JTAG –
    esptool setzt das Modul automatisch in den Download-Modus, ohne
    USB-UART-Chip
  - Hängt die Firmware oder belegt sie die USB-Pins: BOOT halten und RESET
    drücken, dann lässt sich trotzdem flashen
  - CC1/CC2 je 5,1 kΩ nach GND, damit USB-C-Netzteile VBUS einschalten
  - ESD-Schutz USBLC6-2SC6 in D−/D+ und VBUS
- **Power-Tree:** Akku → 5V-Boost (`U1`) → `5V_PERIPH` (speist WS2812,
  MAX98357A, 74AHCT125) → AMS1117-3.3 (`U2`) → `3V3_MCU` (ESP32-S3 und
  Pull-ups).
- **Lader (`U3`, MCP73831):** hängt ausschließlich an `VBUS_NATIVE` der
  USB-C-Buchse, nicht am Boost-Ausgang.
- **TSOPs:** je eigener 100 Ω/4,7 µF-Tiefpass direkt am Sensor (auf der
  Weste).
- **WS2812:** läuft über einen 74AHCT125-Pegelwandler (3,3→5 V) plus
  330 Ω-Vorwiderstand; die Munitionsanzeige hängt als weitere WS2812-Pixel am
  physischen DOUT-Pin des HP-Streifens (Daisy-Chain).
- **PWR_FLAG-Symbole** (`#FLG*`) markieren Netze, die ERC sonst als "nicht
  getrieben" anmahnen würde (Boost-Ausgang, Lader-VBUS).

## Platine

Noch keine `.kicad_pcb`-Datei im Repo – Footprints, Platzierung und Routing
werden manuell in KiCad erstellt.

## Bekannte offene Punkte

- RMT-Kanal-Engpass bei 5 TSOPs (siehe
  [pinbelegung.md, Offene Fragen für den Praxistest](../../pinbelegung.md#offene-fragen-für-den-praxistest))
  ist hier nicht abgebildet, da rein softwareseitig
- Kein mechanischer Abgleich mit dem Waffengehäuse – Gehäusebasis siehe
  [../../gehaeuse/mp5_toygun_stls/](../../gehaeuse/mp5_toygun_stls/)
