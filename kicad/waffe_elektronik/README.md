# waffe_elektronik – KiCad-Schaltplan

Schaltplan für die zentrale Elektronik der Waffe (einziger ESP32-S3-Chip),
passend zu [../../pinbelegung.md](../../pinbelegung.md) und
[../../readme.md](../../readme.md). KiCad 10, ERC-geprüft (0 Fehler).

## Öffnen

`waffe_elektronik.kicad_pro` in KiCad öffnen, dann den Schaltplan-Editor
starten. Die Bibliotheken sind über die mitgelieferte projekteigene
`sym-lib-table` eingebunden (nur Standard-KiCad-Bibliotheken, z. B. `Device`,
`Diode`, `Transistor_FET`, `74xx`, `power` – kein Internet/Zusatz-Download
nötig).

## Was hier generiert statt gezeichnet wurde

Der Schaltplan wurde programmatisch erzeugt (Python + [kiutils][1]), nicht von
Hand in der GUI gezeichnet, und per `kicad-cli sch erc` auf 0 Fehler geprüft.
Verbindungen laufen über Netz-Label statt handgeroutete Leitungen – elektrisch
korrekt und ERC-sauber, aber optisch schlicht. Platzierung/Optik beim ersten
Öffnen in KiCad bei Bedarf nachbessern (Label-basierte Netze lassen sich
jederzeit zu echten Drahtverbindungen umbauen, ohne die Konnektivität zu
ändern).

[1]: https://github.com/mvnmgrx/kiutils

## Platzhalter-Bauteile ("Module")

Für Baugruppen ohne echtes KiCad-Symbol wurden einfache rechteckige
Platzhalter-Symbole mit beschrifteten Pins erzeugt (Bibliothek `Module`):

- `U1` – 5V-Boost-Converter (z. B. MT3608-Fertigmodul)
- `U4` – ESP32-S3-DevKitC-1 (als Modul mit allen genutzten Pins, siehe
  pinbelegung.md für die genaue GPIO-Zuordnung)

Alle anderen Bauteile sind echte Symbole aus den KiCad-Standardbibliotheken
(u. a. `MCP73831-2-OT`, `AMS1117-3.3`, `TSOP348xx`, `MAX98357A`, `AO3400A`,
`74AHCT125`, `SS14`).

## Wichtige Design-Entscheidungen im Schaltplan

- **Power-Tree:** Akku → 5V-Boost (`U1`) → `5V_PERIPH` (speist WS2812,
  MAX98357A, 74AHCT125) → AMS1117-3.3 (`U2`) → `3V3_MCU` (speist **nur** das
  3V3-Pin des DevKitC – die eigene 5V→3V3-LDO des DevKitC wird bewusst nicht
  genutzt, um Rückspeisungs-/Parasitärladeprobleme zu vermeiden).
- **Lader (`U3`, MCP73831):** hängt ausschließlich am `VBUS_NATIVE`-Pin des
  DevKitC-Moduls (= dessen eigener Flash-/Debug-USB-C-Port), **nicht** am
  Boost-Ausgang – sonst würde der Lader dauerhaft versuchen, die Batterie aus
  sich selbst zu laden, wenn kein USB-Kabel steckt.
- **TSOPs:** je eigener 100 Ω/4,7 µF-Tiefpass direkt am Sensor (auf der
  Weste), nicht erst an der Waffe – entspricht readme.md Abschnitt 2.
- **WS2812:** läuft über einen 74AHCT125-Pegelwandler (3,3→5 V) plus
  330 Ω-Vorwiderstand; die Munitionsanzeige hängt als weitere WS2812-Pixel am
  physischen DOUT-Pin des HP-Streifens (Daisy-Chain, hier nicht separat als
  Bauteil dargestellt).
- **PWR_FLAG-Symbole** (`#FLG*`) markieren Netze, die ERC sonst als "nicht
  getrieben" anmahnen würde (z. B. Boost-Ausgang, Lader-VBUS) – Standardpraxis
  für Netze, die von einem Steckverbinder/Modul statt einem echten
  Power-Output-Pin kommen.

## Bekannte offene Punkte

- Platzierung/Linienführung ist rein funktional, nicht für den Druck optimiert
- `ESP32S3_DevKitC`- und `Boost_5V_MT3608`-Symbole sind Platzhalter ohne
  Footprint – vor dem Layout durch echte Footprints/Symbole ersetzen oder
  Footprint-Felder ausfüllen
- RMT-Kanal-Engpass bei 5 TSOPs (siehe pinbelegung.md, offene Fragen) ist hier
  nicht abgebildet, da rein softwareseitig
