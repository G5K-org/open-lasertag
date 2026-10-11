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
  [pinbelegung.md](../../pinbelegung.md) für die genaue GPIO-Zuordnung)

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
  Weste), nicht erst an der Waffe – entspricht [readme.md Abschnitt 2](../../readme.md#2-architektur).
- **WS2812:** läuft über einen 74AHCT125-Pegelwandler (3,3→5 V) plus
  330 Ω-Vorwiderstand; die Munitionsanzeige hängt als weitere WS2812-Pixel am
  physischen DOUT-Pin des HP-Streifens (Daisy-Chain, hier nicht separat als
  Bauteil dargestellt).
- **PWR_FLAG-Symbole** (`#FLG*`) markieren Netze, die ERC sonst als "nicht
  getrieben" anmahnen würde (z. B. Boost-Ausgang, Lader-VBUS) – Standardpraxis
  für Netze, die von einem Steckverbinder/Modul statt einem echten
  Power-Output-Pin kommen.

## Platine (waffe_elektronik.kicad_pcb)

Footprints, Platzierung **und Routing** sind bereits vorhanden – 2 Lagen,
vollständig verdrahtet, mit `kicad-cli pcb drc` gegengeprüft. Renderings:
[renders/top.png](renders/top.png), [renders/bottom.png](renders/bottom.png).

- **Footprints, bevorzugt SMD:** Widerstände 0603, Kondensatoren 0603 (Keramik)
  bzw. `CP_Elec` (Elko, SMD), Taster als SMD-Tastschalter (SKQG-Serie),
  Batterie-Steckverbinder als SMD-JST-PH. IC-seitig ohnehin schon SMD
  (SOT-23(-5), SOT-223, TQFN-16, SOIC-14). **Bewusste THT-Ausnahmen:**
  IR-LED (5mm-Bauform durch die Linsenoptik aus
  [readme.md Abschnitt 4](../../readme.md#4-ir-protokoll-und-trefferlogik)
  vorgegeben) sowie alle Steckverbinder mit echtem Kabel dran (Sensorkabel
  zur Weste, WS2812-Zuleitung) – dort muss ein Stecker Zug am Kabel abkönnen,
  das halten SMD-Pads schlechter als durchgesteckte Pins. Die beiden
  Platzhalter-Module bekamen passende Pinheader-Footprints
  (`Boost_5V_MT3608` → 1×4, `ESP32S3_DevKitC` → 1×22, Pads umbenannt auf die
  GPIO-Pinnamen aus der Schematic).
- **Platzierung – verbindungsbewusst, nicht nur schematisch sortiert:**
  Jedes Bauteil wird (direkt oder über 1–2 Netz-Hops) auf den Pin-Index
  von `U4` (dem ESP32-S3-Modul) zurückgeführt und in dieser Reihenfolge
  gepackt. `U4` sitzt fest als Spalte links, alles andere gruppiert sich
  rechts davon in der Reihenfolge seiner Pins – vorher (reine
  Schematic-Reihenfolge) gab es lange Diagonal-Leitungen quer übers Board,
  das ist jetzt behoben. Eng gepackt (1 mm Abstand, 4 mm Rand), Board-Umriss
  mit abgerundeten Ecken exakt auf den Platzbedarf zugeschnitten: **ca.
  99 × 102 mm** bei dieser Bauteilauswahl (vorher 159 × 141 mm mit
  THT-Bauteilen und unsortierter Platzierung).
- **Netzklassen/Leiterbahnbreiten:** `Default` 0,25 mm, `Power`
  (BAT_P/GND/5V_PERIPH/3V3_MCU/VBUS_NATIVE) 0,6 mm, `IR_Pulse`
  (IR_K/IR_LED_ANODE1/2, der ~300-mA-Puls-Pfad) 1,0 mm. Feinpitch-SMD-Fanout
  (QFN/SOIC) nutzt stellenweise 0,10–0,15 mm (4–6 mil) – bei den meisten
  Prototyp-Fabs Standard bzw. "Advanced"-Tier, daher bewusst belassen statt
  künstlich auf 0,2 mm aufgeweitet; vor der Bestellung mit dem gewählten Fab
  abgleichen.
- **Routing:** mit [Freerouting][2] v2.5.0 geroutet (DSN-Export/SES-Import
  über `pcbnew`-Python, nicht über `kicad-cli` – das hat in dieser
  KiCad-10-Version keine Specctra-Subcommands mehr). Ergebnis laut Freerouting:
  Score 1000, 0 unverbunden, 0 Verstöße. Unabhängig mit `kicad-cli pcb drc`
  gegengeprüft: **0 unverbundene Pads**, 23 Hinweise (ausschließlich die oben
  genannten 0,10–0,15-mm-Fanout-Leiterbahnen).
- **Bekannter Workaround nötig:** Der offizielle `freerouting-cli`-Native-Build
  hat einen Reflection/Serialisierungs-Bug (GraalVM) und hängt sich auf.
  Stattdessen die normale `freerouting-*.jar` mit Java 25+ verwenden. Falls nur
  Java 27 verfügbar ist: dessen C2-JIT stürzt beim Routen ab
  (`ShapeSearchTree45Degree::completeShapeUnlocked`) – mit
  `-XX:TieredStopAtLevel=1` umgehen.
- **Generator-Skripte:** [scripts/build_sch.py](scripts/build_sch.py) +
  [scripts/build_full.py](scripts/build_full.py) bauen den Schaltplan,
  [scripts/build_pcb.py](scripts/build_pcb.py) baut daraus Footprints +
  Platzierung + Netze/Netzklassen und exportiert die DSN-Datei fürs Routing.
  Bei Schaltplan-Änderungen: Skripte anpassen und neu laufen lassen statt von
  Hand nachzuziehen, sonst laufen Schematic und Board auseinander.
- **3D-Ansicht neu rendern:** `kicad-cli pcb render --quality high --floor --rotate "-30,0,30" waffe_elektronik.kicad_pcb` (bzw. mit `--side bottom` für die Rückseite).

[2]: https://github.com/freerouting/freerouting

## Bekannte offene Punkte

- Platzierung ist automatisch nach Netz-Nähe zu U4 sortiert, aber nicht von
  Hand feinjustiert; Autorouter-Pfade sind funktional, nicht für den Druck
  optimiert
- `ESP32S3_DevKitC`- und `Boost_5V_MT3608`-Footprints sind Platzhalter
  (generische Pinheader) – vor der Fertigung durch die echten Footprints der
  tatsächlich gekauften Module/Boards ersetzen
- RMT-Kanal-Engpass bei 5 TSOPs (siehe
  [pinbelegung.md, Offene Fragen für den Praxistest](../../pinbelegung.md#offene-fragen-für-den-praxistest))
  ist hier nicht abgebildet, da rein softwareseitig
- Kein mechanischer Abgleich mit dem Waffengehäuse (Board-Umriss ist reine
  Platzbedarfs-Schätzung, keine Gehäusemaße eingeflossen) – Gehäusebasis siehe
  [../../gehaeuse/mp5_toygun_stls/](../../gehaeuse/mp5_toygun_stls/)
