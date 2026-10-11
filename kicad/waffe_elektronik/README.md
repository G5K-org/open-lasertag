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

## Platzhalter-Bauteile ("Module")

Für Baugruppen ohne echtes KiCad-Symbol wurden einfache rechteckige
Platzhalter-Symbole mit beschrifteten Pins erzeugt (Bibliothek `Module`):

- `U1` – 5V-Boost-Converter (z. B. MT3608-Fertigmodul)
- `U4` – ESP32-S3-DevKitC-1 (als Modul mit allen genutzten Pins, siehe
  [pinbelegung.md](../../pinbelegung.md) für die genaue GPIO-Zuordnung)

Alle anderen Bauteile sind echte Symbole aus den KiCad-Standardbibliotheken
(u. a. `MCP73831-2-OT`, `AMS1117-3.3`, `TSOP348xx`, `MAX98357A`, `AO3400A`,
`74AHCT125`, `SS14`).

## Design-Entscheidungen im Schaltplan

- **Power-Tree:** Akku → 5V-Boost (`U1`) → `5V_PERIPH` (speist WS2812,
  MAX98357A, 74AHCT125) → AMS1117-3.3 (`U2`) → `3V3_MCU` (speist nur das
  3V3-Pin des DevKitC).
- **Lader (`U3`, MCP73831):** hängt ausschließlich am `VBUS_NATIVE`-Pin des
  DevKitC-Moduls (= dessen eigener Flash-/Debug-USB-C-Port), nicht am
  Boost-Ausgang.
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
