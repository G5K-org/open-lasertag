# waffe_elektronik – KiCad-Projekt

Schaltplan und Platine für die zentrale Elektronik der Waffe (einziger
ESP32-S3-Chip), passend zu [../../pinbelegung.md](../../pinbelegung.md) und
[../../readme.md](../../readme.md). KiCad 10, ERC 0 Fehler und 0 Warnungen, DRC 0 Fehler.

![Schaltplan, alle Seiten](renders/schaltplan.png)

## Öffnen

`waffe_elektronik.kicad_pro` in KiCad öffnen, dann Schaltplan- bzw.
Platinen-Editor starten. Die Bibliotheken sind über die mitgelieferte projekteigene
`sym-lib-table` eingebunden (nur Standard-KiCad-Bibliotheken, z. B. `Device`,
`Diode`, `Transistor_FET`, `74xx`, `power`).

## Aufbau

Hierarchischer Schaltplan: ein Übersichtsblatt (`waffe_elektronik.kicad_sch`, A4) mit fünf A3-Unterblättern,
jedes in gestrichelt umrahmte Funktionsblöcke gegliedert:

| Seite | Datei | Blöcke |
|---|---|---|
| 2 [Stromversorgung](renders/schaltplan_1_stromversorgung.png) | `stromversorgung.kicad_sch` | Boost + LDO, Laden, Akku-Messung, Akkuschutz + USB-Versorgung |
| 3 [ESP32-S3 und USB](renders/schaltplan_2_mcu_usb.png) | `mcu_usb.kicad_sch` | ESP32-S3-WROOM-1, USB-C |
| 4 [Bedienung und Aktoren](renders/schaltplan_3_bedienung_aktoren.png) | `bedienung_aktoren.kicad_sch` | IR-Sender, Abzug/Nachladen, WS2812, Vibration, OLED + Drehgeber |
| 5 [Audio und Speicher](renders/schaltplan_4_audio_speicher.png) | `audio_speicher.kicad_sch` | Sound (I²S), Flash, microSD |
| 6 [Sensoren](renders/schaltplan_5_sensoren.png) | `sensoren.kicad_sch` | Weste, TSOP 6, Serienwiderstände im Sensorkabel |

- Innerhalb eines Blocks ist alles mit echten Leitungen verdrahtet; Bauteile
  liegen auf dem Raster, Versorgung zeigt nach oben, Masse nach unten.
- Zwischen den Blöcken und Seiten laufen Signale über globale Labels an kurzen
  Stichleitungen (z. B. `IR_GATE`, `TSOP1_OUT`) statt über lange Leitungen.
- Versorgungsnetze (`GND`, `3V3_MCU`, `5V_PERIPH`, `BAT_P`, `VBUS_NATIVE`)
  hängen an KiCad-Power-Symbolen.
- Unbenutzte Pins sind markiert: freie GPIOs mit No-Connect-Kreuz, die drei
  freien Gatter des 74HCT125 mit Eingang und `/OE` auf GND.

Schaltplan ([kiutils][1]) und Platine (pcbnew) werden per Python erzeugt und
mit `kicad-cli` geprüft; die Generator-Skripte liegen in [`scripts/`](scripts/).
Die Footprints der senkrechten USB-C-Buchse (J3) und des microSD-Slots (J7, Pads nach LCSC/EasyEDA) liegen in der Projektbibliothek
[`footprints/lasertag.pretty`](footprints/lasertag.pretty) (`fp-lib-table`), ihr 3D-Modell
erzeugt `freecadcmd scripts/gen_3d_usb_c_vertical.py`.
3D-Modelle der JST-PH-SMD-Stecker (BT1, SP1, J1) und des WSON-8 8×6 (U14) liegen in [`3dmodels/`](3dmodels/)
(STEP + WRL, erzeugt mit `freecadcmd scripts/gen_3d_jst_ph_sm4.py` bzw. `scripts/gen_3d_wson8_8x6.py`),
das Modell des microSD-Slots (J7) stammt aus der LCSC/EasyEDA-Bibliothek (C961679).

[1]: https://github.com/mvnmgrx/kiutils

## Bauteile

Die Symbole stammen aus den KiCad-Standardbibliotheken; FS8205A sowie Kopien von `W25Q32JVZP`
(/WP, /HOLD passiv), `MAX98357A` (Pad = Masse) und `74AHCT125` liegen in der Projektbibliothek
[`symbols/lasertag.kicad_sym`](symbols/lasertag.kicad_sym), die `build_clean.py` aus dem erzeugten Schaltplan
schreibt. Verwendet u. a.
`ESP32-S3-WROOM-1` (`U4`), `USB_C_Receptacle_USB2.0_16P` (`J3`),
`USBLC6-2SC6`, `MT3608`, `MCP73831-2-OT`, `AMS1117-3.3`, `TSOP348xx`,
`MAX98357A`, `AO3400A`, `74AHCT125`, `SS14`, `SS34`, `W25Q32JVZP` (Pinbild für U14), `Micro_SD_Card_Det1`,
`DW01A`, `D_Schottky`. Alle Footprints sind
SMD, J3 aus der Projektbibliothek; Bauteile außerhalb der Platine (Akku, IR-LED, TSOP 6, Taster, Motoren,
Lautsprecher, WS2812, Weste) sind über JST-SH/-PH-Stecker angeschlossen.

## Design-Entscheidungen im Schaltplan

- **ESP32-S3-WROOM-1 direkt auf der Platine** (kein DevKit):
  - 3V3 mit 100 nF + 10 µF direkt am Modul
  - EN mit 10 kΩ Pull-up und 1 µF (Power-on-Reset), dazu RESET-Taster
  - BOOT-Taster an IO0
- **USB-C (`J3`) am nativen USB des S3** (IO19/IO20 = USB_D−/USB_D+):
  - senkrechte Buchse hanxia HX-TYPE-C 16P 180 LT H10.5 (LCSC C49261570), 10,5 mm hoch;
    Stecker kommt von der Bestückungsseite, die Buchse reicht in der Waffe durch die linke Seitenwand
    und schließt bündig mit einer flachen Mulde außen ab
  - Flashen und serielle Konsole über den eingebauten USB-Serial-JTAG –
    esptool setzt das Modul automatisch in den Download-Modus, ohne
    USB-UART-Chip
  - Hängt die Firmware oder belegt sie die USB-Pins: BOOT halten und RESET
    drücken, dann lässt sich trotzdem flashen
  - CC1/CC2 je 5,1 kΩ nach GND, damit USB-C-Netzteile VBUS einschalten
  - ESD-Schutz USBLC6-2SC6 in D−/D+ und VBUS
- **Power-Tree:** Akku → Akkuschutz → 5V-Boost (`U1`) → `5V_PERIPH` (speist WS2812,
  MAX98357A, 74HCT125) → AMS1117-3.3 (`U2`) → `3V3_MCU` (ESP32-S3 und
  Pull-ups).
- **Akkuschutz:** DW01A (`U15`, LCSC C351410) + FS8205A (`Q3`, C2830320) im Minuspfad des Akkus
  (`BAT_N` → `GND`): trennt bei ca. 4,3 V, 2,4 V und Überstrom; VCC über 100 Ω (`R28`) + 100 nF (`C27`),
  CS über 1 kΩ (`R29`)
- **USB ohne Akku:** Schottky SS14 (`D4`) von `VBUS_NATIVE` auf `5V_PERIPH`; D3 im Boost sperrt den Rückweg
  in den Akku, mit Akku liefert der Boost (5,1 V)
- **Lade-Status:** STAT des MCP73831 über BAT54WS (`D5`) an IO18, Pull-up `R2` auf der GPIO-Seite
- **IR-Puffer:** `C7` (100 µF) von `BAT_P` nach GND
- **Lader (`U3`, MCP73831):** hängt ausschließlich an `VBUS_NATIVE` der
  USB-C-Buchse, nicht am Boost-Ausgang.
- **Sensorkabel:** TSOP 1–5 je über 100 Ω (`R30`–`R34`) an J2
- **TSOPs:** je eigener 100 Ω/4,7 µF-Tiefpass direkt am Sensor (auf der
  Weste).
- **WS2812:** läuft über einen 74HCT125-Pegelwandler (3,3→5 V) plus
  330 Ω-Vorwiderstand; die Munitionsanzeige hängt als weitere WS2812-Pixel am
  physischen DOUT-Pin des HP-Streifens (Daisy-Chain), am Ende der Kette sitzt
  das Ringlicht für das Mündungsfeuer vorne an der Waffe.
- **Flash für Audio-Dateien (`U14`):** SPI-NAND GD5F1GQ5UEYIGR, 1 Gbit (128 MB), WSON-8 8×6,
  LCSC C2829047, ESP-IDF-Komponente `espressif/spi_nand_flash`; SPI2 über die GPIO-Matrix
  (IO7 /CS, IO15 MISO, IO3 MOSI, IO46 CLK), /CS mit 10 kΩ (`R27`) auf 3V3, /WP und /HOLD fest
  auf 3V3, 100 nF (`C25`) an VCC, EP auf GND
- **microSD-Slot (`J7`):** XKB TF-018, Push-Pull, LCSC C961679, im SPI-Modus am Flash-Bus
  (`SPI_CLK`/`SPI_MOSI`/`SPI_MISO`), /CS an IO48; Pull-ups an /CS und DAT0 intern im ESP32, DAT1/DAT2
  gemeinsam über 10 kΩ (`R37`), Kartenerkennung offen, 100 nF (`C26`)
- **PWR_FLAG-Symbole** (`#FLG*`) markieren Netze, die ERC sonst als "nicht
  getrieben" anmahnen würde (Boost-Ausgang, Lader-VBUS).

## Platine

![Platine oben](renders/platine_3d.png)

| Oben | Unten |
|---|---|
| ![oben](renders/platine_oben.png) | ![unten](renders/platine_unten.png) |

- **59,6 × 51 mm** (Grundfläche 59,6 × 46 mm; oben links eine 17 × 5 mm große Lasche für den Akkuschutz,
  rechts bei y 18,5–26,5 eine Aussparung für das Motorkabel), 1,6 mm, 4 Lagen, nur SMD, Bestückung nur oben
- **Lagen:**
  - F.Cu: Bauteile, kurze Signale, GND-Fläche
  - In1.Cu: durchgehende GND-Fläche ohne Leiterbahnen
  - In2.Cu: Versorgung (`5V_PERIPH`, `3V3_MCU`, `BAT_P`) als Leiterbahnen + GND-Fläche
  - B.Cu: lange Signale (EN, Abzug, Nachladen, IR, WS2812, IO0, TSOP, Bedienteil, Flash, microSD) + GND-Fläche, Projekt-URL
- **ESP32-S3-Modul:** Antenne ragt über die Oberkante hinaus; jedes GND-Pad
  mit eigenem Via nach In1, GND-Stitching-Vias im Raster
- **Befestigung:** 2 × M2-Loch (2,2 mm, nicht durchkontaktiert) für Linsenkopfschrauben
  ISO 7380 (Kopf ≤ 3,5 mm), diagonal: neben dem Spannungsregler und unten zwischen USB-C und
  microSD-Slot; Ø 3,7 mm kupferfrei auf allen Lagen
- **Flash (U14):** unter dem Modul zwischen C1 und Vibrationstreiber; die vier SPI-Leitungen laufen auf
  B.Cu links an BOOT vorbei, /CS und MISO links in U14, MOSI und CLK unter U14 durch zu Vias rechts
  neben Pin 5/6; 3V3 für C25/R27/WP über einen In2-Abzweig der rechten 3V3-Leitung
- **microSD (J7):** unten rechts, Öffnung bündig mit der Unterkante, die Karte ragt ~8,6 mm in die
  Kabeltasche unter der Platine; MOSI/CLK/VDD/GND/MISO über Vias unter der Kontaktreihe, /CS von oben auf
  F.Cu, MISO auf B.Cu unter dem Slot durch; U6/C23 dafür 0,3 mm höher, J2 1,5 mm höher
- **Bedienung:** J4 OLED (JST-SH 4, Qwiic: GND/3V3/SDA/SCL) und J5 Drehgeber (JST-SH 4:
  GND/Taster/B/A) übereinander im rechten Streifen; I²C-Pull-ups auf dem OLED-Modul
- **Stecker nach Kabelweg in der Waffe:** jede Öffnung zeigt in die Zone am Platinenrand, aus der der
  Kabelschacht des Bauteils abgeht
  - links (vorn, Hauptschacht zum Lauf, Abzweig Magazin): Akku (BT1), IR-LED (LED1), TSOP 6 (J6),
    WS2812 (J1), Lautsprecher (SP1)
  - unten (Kanal zur Abzugsschalter-Tasche): Abzug (SW1), Nachladen (SW2), Entprellung R9/C8 und
    R10/C9 direkt darüber; microSD-Karte (J7) rechts davon, die Abzugskabel liegen über ihr
  - rechts (hinten, Motorschacht): Vibrationsmotor (M1), Sensorkabel Weste (J2)
  - rechts oben: OLED (J4), Drehgeber (J5)
  - USB-C (J3) senkrecht unten rechts der Abzugsstecker, CC1/CC2-Widerstände R23/R22 direkt
    darüber/darunter; RESET-Taster auf dem EN-Weg oben links
- **Regeln (`.kicad_pro`):** min. 0,15 mm Leiterbahn/Abstand, Vias 0,5/0,3 mm
  (USB-Kreuzung 0,4/0,2 mm), Netzklassen Default 0,2 mm, Power 0,5 mm,
  3V3 0,6 mm, USB 0,2/0,2 mm (Paar)
- **Leiterbahnen so kurz wie möglich** auf allen Lagen: lange Wege als ein 45°-Abschnitt
  statt L-Form; parallele Bündel bleiben parallel und kreuzungsfrei
- **USB-Paar gleich lang:** D+ mit Mäander zwischen Modul und USBLC6 und zwischen USBLC6
  und Buchse; an der Buchse D+ über ein Via in der Buchsenmitte (A6–B6-Diagonale), D− über eine
  B.Cu-Brücke A7–B7 mit Abgriff in der Längenmitte; beide Steckrichtungen gleich lang
  (Modul–USBLC6 0,000 mm, USBLC6–Buchse ≤ 0,01 mm, je 2 Vias); VBUS A4/B9 und A9/B4 je über ein
  Via im Reihenspalt, links über B.Cu, rechts über In2 zum USBLC6
- **Beschriftung oben** (F.SilkS), alle Labels waagerecht und einheitlich 0,8 mm hoch,
  direkt am jeweiligen Stecker/Taster, frei von Pads, Vias und Bauteilkörpern; LED1/TSOP auf
  gemeinsamer Mittelachse, WS2812 neben und LAUTSPR. unter ihrem Stecker, ABZUG/NACHL. auf gemeinsamer
  Höhe über ihren Steckern; Pin 1 von J2
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
Lose Teile in der Waffe, die an die Platine angeschlossen werden (nicht bestückt):
[`fertigung/lcsc/waffe_lose_teile.csv`](fertigung/lcsc/waffe_lose_teile.csv) – Nachladetaster
K2-1102DP-C4SW-04 (C110153) an SW2, Abzugsschalter Omron D2F-01 (C397278) an SW1.

- Leiterplatte: 4 Lagen, 1,6 mm, Impedanz-Stackup JLC04161H-7628, ENIG
- Bestückung: Top Side, BOM + CPL hochladen, Platzierungsvorschau prüfen
- Ersatzteile: `U5` 74HCT125PW, `D1`/`D2` SS14 (SOD-123FL), `L1` 10 µH MWSA0503S,
  `BT1`/`SP1` CJT A2001WR-S-2P, `J1` CJT A2001WR-S-3P (JST-PH-kompatibel)

## Bekannte offene Punkte

- RMT-Kanal-Engpass bei 5 TSOPs (siehe
  [pinbelegung.md, Offene Fragen für den Praxistest](../../pinbelegung.md#offene-fragen-für-den-praxistest))
  ist hier nicht abgebildet, da rein softwareseitig
- Kein mechanischer Abgleich mit dem Waffengehäuse – Gehäusebasis siehe
  [../../gehaeuse/mp5_toygun_stls/](../../gehaeuse/mp5_toygun_stls/)
