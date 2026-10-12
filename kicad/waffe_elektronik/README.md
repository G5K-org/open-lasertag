# waffe_elektronik – KiCad-Projekt

Schaltplan und Platine für die zentrale Elektronik der Waffe (einziger
ESP32-S3-Chip), passend zu [../../pinbelegung.md](../../pinbelegung.md) und
[../../readme.md](../../readme.md). KiCad 10, ERC 0 Fehler, DRC 0 Fehler.

![Schaltplan](renders/schaltplan.png)

## Öffnen

`waffe_elektronik.kicad_pro` in KiCad öffnen, dann Schaltplan- bzw.
Platinen-Editor starten. Die Bibliotheken sind über die mitgelieferte projekteigene
`sym-lib-table` eingebunden (nur Standard-KiCad-Bibliotheken, z. B. `Device`,
`Diode`, `Transistor_FET`, `74xx`, `power`).

## Aufbau

Ein A2-Blatt, in gestrichelt umrahmte Funktionsblöcke gegliedert:
Stromversorgung, Laden, Akku-Messung, Sound, ESP32-S3, IR-Sender,
Abzug/Nachladen, WS2812, Weste (Sensoren) und Vibration.

- Innerhalb eines Blocks ist alles mit echten Leitungen verdrahtet; Bauteile
  liegen auf dem Raster, Versorgung zeigt nach oben, Masse nach unten.
- Zwischen den Blöcken laufen Signale über Netz-Labels an kurzen
  Stichleitungen (z. B. `IR_GATE`, `TSOP1_OUT`) statt über lange Leitungen
  quer über das Blatt.
- Versorgungsnetze (`GND`, `3V3_MCU`, `5V_PERIPH`, `BAT_P`, `VBUS_NATIVE`)
  hängen an KiCad-Power-Symbolen.
- Unbenutzte Pins sind markiert: freie GPIOs mit No-Connect-Kreuz, die drei
  freien Gatter des 74HCT125 mit Eingang und `/OE` auf GND.

Schaltplan ([kiutils][1]) und Platine (pcbnew) werden per Python erzeugt und
mit `kicad-cli` geprüft; die Generator-Skripte liegen in [`scripts/`](scripts/).
3D-Modelle der JST-PH-SMD-Stecker (BT1, SP1, J1) liegen in [`3dmodels/`](3dmodels/)
(STEP + WRL, erzeugt mit `freecadcmd scripts/gen_3d_jst_ph_sm4.py`).

[1]: https://github.com/mvnmgrx/kiutils

## Bauteile

Alle Bauteile sind Symbole aus den KiCad-Standardbibliotheken, u. a.
`ESP32-S3-WROOM-1` (`U4`), `USB_C_Receptacle_USB2.0_16P` (`J3`),
`USBLC6-2SC6`, `MT3608`, `MCP73831-2-OT`, `AMS1117-3.3`, `TSOP348xx`,
`MAX98357A`, `AO3400A`, `74AHCT125`, `SS14`, `SS34`. Alle Footprints sind
SMD; Bauteile außerhalb der Platine (Akku, IR-LED, TSOP 6, Taster, Motoren,
Lautsprecher, WS2812, Weste) sind über JST-SH/-PH-Stecker angeschlossen.

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
  MAX98357A, 74HCT125) → AMS1117-3.3 (`U2`) → `3V3_MCU` (ESP32-S3 und
  Pull-ups).
- **Lader (`U3`, MCP73831):** hängt ausschließlich an `VBUS_NATIVE` der
  USB-C-Buchse, nicht am Boost-Ausgang.
- **TSOPs:** je eigener 100 Ω/4,7 µF-Tiefpass direkt am Sensor (auf der
  Weste).
- **WS2812:** läuft über einen 74HCT125-Pegelwandler (3,3→5 V) plus
  330 Ω-Vorwiderstand; die Munitionsanzeige hängt als weitere WS2812-Pixel am
  physischen DOUT-Pin des HP-Streifens (Daisy-Chain), am Ende der Kette sitzt
  das Ringlicht für das Mündungsfeuer vorne an der Waffe.
- **PWR_FLAG-Symbole** (`#FLG*`) markieren Netze, die ERC sonst als "nicht
  getrieben" anmahnen würde (Boost-Ausgang, Lader-VBUS).

## Platine

![Platine oben](renders/platine_3d.png)

| Oben | Unten |
|---|---|
| ![oben](renders/platine_oben.png) | ![unten](renders/platine_unten.png) |

- **59,6 × 46 mm, L-förmig** (54 mm breit, oben rechts bis y = 18,5 mm ein 5,6 mm breiter Streifen
  für OLED- und Drehgeber-Stecker), 1,6 mm, 4 Lagen, nur SMD, Bestückung nur oben
- **Lagen:**
  - F.Cu: Bauteile, kurze Signale, GND-Fläche
  - In1.Cu: durchgehende GND-Fläche ohne Leiterbahnen
  - In2.Cu: Versorgung (`5V_PERIPH`, `3V3_MCU`, `BAT_P`) als Leiterbahnen + GND-Fläche
  - B.Cu: lange Signale (EN, Abzug, Nachladen, IR, WS2812, IO0, TSOP, Bedienteil) + GND-Fläche, Projekt-URL
- **ESP32-S3-Modul:** Antenne ragt über die Oberkante hinaus; jedes GND-Pad
  mit eigenem Via nach In1, GND-Stitching-Vias im Raster
- **Befestigung:** 2 × M2-Loch (2,2 mm, nicht durchkontaktiert) für Linsenkopfschrauben
  ISO 7380 (Kopf ≤ 3,5 mm), diagonal: neben dem Spannungsregler und zwischen Sensor- und
  Lautsprecherstecker; Ø 3,7 mm kupferfrei auf allen Lagen
- **Bedienung:** J4 OLED (JST-SH 4, Qwiic: GND/3V3/SDA/SCL) und J5 Drehgeber (JST-SH 4:
  GND/Taster/B/A) übereinander im rechten Streifen; I²C-Pull-ups auf dem OLED-Modul
- **Stecker:** links IR-LED (LED1)/TSOP 6 (J6)/Abzug/Nachladen, unten WS2812/USB-C/Sensor/
  Lautsprecher, rechts Vibrationsmotor, rechts oben OLED/Drehgeber, oben links Akku
- **Regeln (`.kicad_pro`):** min. 0,15 mm Leiterbahn/Abstand, Vias 0,5/0,3 mm
  (USB-Kreuzung 0,4/0,2 mm), Netzklassen Default 0,2 mm, Power 0,5 mm,
  3V3 0,6 mm, USB 0,2/0,2 mm (Paar)
- **Leiterbahnen so kurz wie möglich** auf allen Lagen: lange Wege als ein 45°-Abschnitt
  statt L-Form; parallele Bündel bleiben parallel und kreuzungsfrei
- **USB-Paar gleich lang:** D+ mit Mäander zwischen Modul und USBLC6, jeder Abschnitt
  D+/D− auf 0,000 mm gleich (Leiterbahnlänge)
- **Beschriftung oben** (F.SilkS), alle Labels waagerecht und einheitlich 0,8 mm hoch,
  direkt am jeweiligen Stecker/Taster, frei von Pads, Vias und Bauteilkörpern; Labels einer
  Steckerspalte auf gemeinsamer Mittelachse, untere Stecker mittig beschriftet; Pin 1 von J2
  mit „1“ markiert; Bauteilbezeichner nur auf F.Fab
- **Leiterbahnen nur in 0°/45°/90°**, jeder Knick max. 45°, Abzweige laufen
  unter 45° ein; Teardrops an allen Pads und Vias (außer GND-Stichen in der
  GND-Fläche)
- **Routing von Hand**, kein Autorouter: MT3608-Schaltknoten kurz und breit,
  3V3 von der LDO-Kühlfläche über 10 µF + 100 nF direkt an Modul-Pin 2,
  USB-Paar 45° geführt, D+/D− an der Buchse über eine Via-Kreuzung
- Fertigungsdaten: JLCPCB-4-Lagen-Standardstackup (USB-Impedanz beim
  Fertiger prüfen)

## Fertigung (JLCPCB)

[`fertigung/jlcpcb/`](fertigung/jlcpcb/): `waffe_elektronik_gerber.zip` (Gerber + Bohrdaten),
`waffe_elektronik_bom.csv`, `waffe_elektronik_cpl.csv`. Alle Bauteile mit LCSC-Nummer (Feld `LCSC`),
geprüft auf Lagerbestand bei JLCPCB.

- Leiterplatte: 4 Lagen, 1,6 mm, Impedanz-Stackup JLC04161H-7628, ENIG
- Bestückung: Top Side, BOM + CPL hochladen, Platzierungsvorschau prüfen
- Ersatzteile: `U5` 74HCT125PW, `D1`/`D2` SS14 (SOD-123FL), `L1` 10 µH MWSA0503S,
  `BT1`/`SP1` CJT A2001WR-S-2P (JST-PH-kompatibel)

## Bekannte offene Punkte

- RMT-Kanal-Engpass bei 5 TSOPs (siehe
  [pinbelegung.md, Offene Fragen für den Praxistest](../../pinbelegung.md#offene-fragen-für-den-praxistest))
  ist hier nicht abgebildet, da rein softwareseitig
- Kein mechanischer Abgleich mit dem Waffengehäuse – Gehäusebasis siehe
  [../../gehaeuse/mp5_toygun_stls/](../../gehaeuse/mp5_toygun_stls/)
