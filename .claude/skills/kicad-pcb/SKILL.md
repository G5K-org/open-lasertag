---
name: kicad-pcb
description: Rules, workflow and check tools for placing and hand-routing the lasertag KiCad board (kicad/waffe_elektronik) with build_board.py. Use for any PCB placement, routing, DRC, teardrop, render or footprint work in this repo.
---

# KiCad-PCB: Platzierung und Routing (lasertag)

Projekt: `kicad/waffe_elektronik/` (KiCad 10). Platine wird **vollständig per Skript** erzeugt:
`scripts/build_board.py` (System-`python3` mit `pcbnew`). Schaltplan: `scripts/build_clean.py`
(kiutils-venv). Prüfwerkzeuge liegen in `tools/` neben dieser Datei.

## Feste Vorgaben des Users (nie abweichen)

- **Kein Autorouter.** Jede Leiterbahn wird mit eigenen Wegpunkten festgelegt.
- **Nur SMD**, THT nur wenn es kein SMD gibt. Bestückung nur oben.
- **Leiterbahnen nur 0°/45°/90°**, jeder Knick **max. 45°**, keine Zwischenwinkel.
  Abzweige laufen **unter 45°** in die Hauptleitung oder enden in einem Pad/Via, nie im 90°-T-Stoß.
- **Jede Leiterbahn auf allen Lagen so kurz wie möglich, so lang wie nötig** (gilt allgemein, nicht nur B.Cu).
  Keine L-Form, wo ein 45°-Abschnitt passt: langer Weg =
  kurzes Gerades + **ein** langer 45°-Lauf + kurzes Gerades. Parallele Bündel als Ganzes schräg führen
  (gleiche Reihenfolge, Diagonalen parallel, Abstand der Diagonalen über `x+y` bzw. `x−y` planen).
  Umwege nur um echte Hindernisse (Pads, Vias anderer Netze, Bauteile auf der eigenen Lage) und für
  Längenausgleich (USB-Paar). Prüfen mit `tools/detour.py --layers=F,2,B --min=0.2 --ratio=1.02`; jeder
  verbleibende Fund braucht ein konkretes Hindernis als Grund.
- **Differenzpaare gleich lang** (USB D+/D−, gesamte Länge Pad→Pad über alle Lagen inkl. Via-Höhe):
  beide Leitungen erst einzeln so kurz wie möglich, dann die kürzere mit einem **Mäander** (0/45/90°,
  Abstand ≥ 3 × Bahnbreite) auf die längere ausgleichen. Rest-Differenz ≤ 0,1 mm. Mäander mit
  `meander_v(x, y0, extra, n, c, t, gap, side)` in build_board.py (senkrechter Lauf, n Ausbuchtungen,
  Zusatzlänge pro Ausbuchtung 2h − 4c(2 − √2)); Zielwerte `USB_TUNE` (Modul–U12) und `USB_TUNE2` (U12–J3). Prüfen mit
  `tools/pairlen.py w.kicad_pcb U4.14-U12.4 U4.13-U12.6 U12.3-J3.B6 U12.1-J3.B7 U12.3-J3.A6 U12.1-J3.A7 --via=0`
  (je Paar-Abschnitt zwischen denselben Bauteilen; Stand: Modul–U12 0,000, U12–J3 ≤ 0,005 mm). J3 ist die
  senkrechte hanxia HX-TYPE-C 16P 180 LT H10.5 (10,5 mm hoch, bündig mit der Gehäusewand; Projektbibliothek
  `footprints/lasertag.pretty`, Padbild aus dem Datenblatt um 180° gedreht): A-Reihe oben, B-Reihe unten,
  1,0 mm Raster, Reihen 2,73 mm auseinander, Schirmlaschen überlappen A1/B12/A12/B1 (Abstand zu den
  NPTH-Stiften ≥ 0,19). D+ = F.Cu-Diagonale A6–B6 durch ein Via in der Buchsenmitte (`vc`), von rechts oben
  über B.Cu gespeist (Mäander `USB_TUNE2` auf F.Cu zwischen U12.3 und `v3`); D− = B.Cu-Brücke links um `vc`
  von Via über A7 zu Via unter B7, Abgriff `tap` in der Längenmitte, Zuleitung von `v5` unter 45° → A- und
  B-Steckrichtung gleich lang. VBUS A4–B9 und A9–B4 gerade durch den Reihenspalt, je ein Via im Spalt; links
  über B.Cu zu C4 und zum Via in der U12-Mitte (U12.5), rechts über In2 zum selben Via. GND A1–B12 und A12–B1
  ebenfalls durch den Spalt mit Via. CC1 gerade hoch zu R23, CC2 gerade runter zu R22.
- **Beschriftung auf der Vorderseite** (`F.SilkS`, nicht gespiegelt), **lesbar mit bestückten Bauteilen**:
  kein Text auf Pads, Bauteilkörpern (F.Fab-Umriss), Footprint-Silk, anderen Texten, ≥ 0,3 mm vom Rand.
  Jedes Steckerlabel direkt an **seinem** Stecker, näher an ihm als an jedem Nachbarn.
  **Alle Labels an Steckern, Klemmen und Tastern waagerecht (0°) und einheitlich: gleiche Höhe 0,8 mm
  (Minimum), Strich 0,12, nie gedreht** – auch der Projekttitel. Lieber eine Lücke weiter am Stecker
  (oben/unten/neben) als ein senkrechtes Label. Pin 1 von Steckern mit „1“ markieren, wenn die
  Footprint-Silk es nicht schon tut.
  **Mehrere Stecker in einer Reihe/Spalte:** ihre Labels gemeinsam ausrichten – in einer Spalte (links
  früher LED1/TSOP) gleiche Mittelpunkt-x (horizontal zentriert untereinander), jedes Label direkt am eigenen
  Stecker (nie zwei Labels zwischen zwei Steckern so, dass beide zum selben zu gehören scheinen); lückenlos
  aneinander liegende PH-Stecker (J1/SP1) bekommen ihr Label daneben bzw. darunter. Reihe (früher unten SW1/SW2):
  gemeinsame y über den Steckern; bei unterschiedlichen Steckerhöhen jedes Label mittig über seinem Stecker.
  Suche: `silk.py --column "A=REF" ...` bzw. `--row`; Mindestabstand Label ↔ Pad/Via/Körper/Silk 0,12 mm.
  Die gefundenen Werte sind Mittelpunkte der Strichkontur; KiCad-Textanker liegt bis 0,1 mm daneben
  (y ≈ +0,036) → nach dem Setzen immer `silk.py --gap=0.12` laufen lassen.
  Unter Labels keine Vias: `stitch()` hält Textflächen frei, `silk.py` prüft Vias mit Leiterbahn. Was vorne keinen Platz hat (Projekt-URL), geht in `BACK_LABELS` auf `B.SilkS`.
  Herstellerzeichen vorne unter U2: Borg-Würfel (`LOGO`, `logo()`, isometrisch mit 3 × 3-Gitter, Linien 0,15) plus
  „made by“ / „lucas.giesecke.cc“ in `LABELS`; BOOT steht deshalb links unter SW4.
  Bauteilbezeichner bleiben auf `F.Fab`. Prüfen/platzieren mit `tools/silk.py`.
- **Teardrops** an allen Pads und Vias (Ausnahme: GND-Stiche auf F.Cu, die in der GND-Fläche liegen).
- Platine **so klein wie möglich**, Bauteilplatzierung mit 3D-Daten prüfen (Render).
- Docs: nur Entscheidungen, keine Begründungen. Commits nur auf Anweisung, ohne Claude-Hinweis.
  `scripts/` wird mit committet, `MP5+Build_stls.zip` und `.history/` nie.

## Lagenaufbau und Regeln

- 4 Lagen, 1,6 mm (JLCPCB-Standardstackup).
  - F.Cu: Bauteile, kurze Signale, GND-Fläche
  - In1.Cu: durchgehende GND-Fläche, **keine Leiterbahnen**
  - In2.Cu: Versorgung (`5V_PERIPH`, `3V3_MCU`, `BAT_P`) als Leiterbahnen + GND-Fläche
  - B.Cu: lange Signale + GND-Fläche, nur die Projekt-URL als Beschriftung (gespiegelt)
- Jedes GND-Pad bekommt ein eigenes Via nach In1 (`r.gnd`), Stromversorgungs-Pads ein Via nach In2 (`r.drop`).
- Netzklassen/Regeln stehen in `RULES`/`NETCLASSES` und werden von `write_project()` in die `.kicad_pro` geschrieben:
  min. 0,15 mm Bahn/Abstand, Vias 0,5/0,3 (USB-Kreuzung 0,4/0,2), Default 0,2, Power 0,5, 3V3 0,6, USB-Paar 0,2/0,2.
- **Befestigung:** 2 × M2 nach ISO 7380 (Linsenkopf 3,5 mm), `HOLES` in build_board.py, Footprint
  `MountingHole_2.2mm_M2_ISO7380`, nicht durchkontaktiert, board-only (nicht in Schaltplan/BOM/CPL).
  Courtyard = Kopfradius `HOLE_HEAD` 1,75 mm, Kupfer-Sperrfläche `HOLE_KEEPOUT` 1,85 mm auf allen Lagen
  (keine Bahnen, Vias, Füllung). Lage diagonal: H1 (20,4/14,8) neben U2, H2 (37,0/42,5) unten zwischen J3 und J7
  (Lautsprecherleitungen laufen rechts daran vorbei, x 39,4/40,0).
  Freie Stellen suchen: größte freie Kreise gegen Pads, Körper, Bahnen, Vias mit Bahn und Texte.
  Mehr Löcher oder größere Schrauben nur mit größerer Platine.
- ESP32-S3-WROOM-1: Antenne ragt über die Oberkante (`MX, MY`), 100 nF + 10 µF und EN-RC direkt an den Pins.
- Randstecker: Body bündig, aber Befestigungspads ≥ 0,3 mm vom Rand (`SH_IN = 3.1`, `PH_IN = 4.9`).
- **Kontur (`OUTLINE` in build_board.py, alle Ecken R 1 mm):** Grundfläche `W` = 59,6 × `H` = 46, rechts eine
  Aussparung x > `W0` = 54 für `Y1` = 18,5 < y < `Y2` = 26,5 (M1 an `W0`, Motorkabel), oben links eine Lasche
  x < `XT` = 18,6, −`YT` = −9 < y < 0 (Akkuschutz, darüber Ein/Aus). Die Lasche endet links vom
  Antennen-Sperrbereich des Moduls (x ≥ 18,5 für y < 0: dort keine Leiterbahnen/Vias); höher als 9 mm wird die
  rechte Gehäusewand zu dünn. Modul `MX = W0 − 11,5`; J4/J5/J2 an `W`. Masseflächen und
  Stitching (`on_board()`) folgen der Kontur. Neue Teile an der Kante: `W` bzw. `W0` je nach Höhe.
- **IR-LED + TSOP 6 (J6, links bei y 18,1, JST-SH 5 = ZX-SH1.0-5PWT):** 1 LED-Anode (R7/R8 22 Ω parallel,
  senkrecht nebeneinander bei x 8,6/10,95, Akku oben, Anode unten), 2 LED-Kathode (y 17,1 nach rechts, x 7,66
  hinunter in Q1.3), 3 GND (Via 6,3/18,1), 4 VS (`3V3_J6`: Via 6,3/19,5 → In2 → Via 10,3/22,0 → R36 (10 Ω,
  12,0/22,0) → Via 13,7/22,0 → In2 an die 3V3-Diagonale), 5 OUT von IO16: B.Cu-Kanal Diagonale x + y = 38,0
  (zwischen H1-Sperrfläche und R2-3V3-Via, H1 dafür auf 20,4/14,8, U2-GND-Via auf (−1,2/0,3)), letztes Stück
  F.Cu von unten rechts. C7 (22 µ) in der Ecke über J6 (4,0/11,44). Filter 100 Ω + 4,7 µF sitzt am Sensor (U13/R26/C24 nicht auf der Platine).
  Linker Rand ist auf B.Cu durch das Abzug/Nachladen/IR-Bündel abgetrennt → Signale zu linken
  Steckern immer zuletzt auf F.Cu.
- **Steckerplätze nach Kabelweg im Gehäuse** (Zonen in `gehaeuse/scripts/platine_einbau.py`): links (vorn,
  Hauptschacht) BT1, J6 (IR-LED + TSOP 6), J1 (WS2812), SP1 (Lautsprecher); unten (Kanal zum Abzugsschalter)
  J8 (Abzug + Nachladen, 15,45) mit R9/C8, R10/C9 waagerecht darüber; rechts (hinten, Motorschacht) M1, darunter J2 (Weste); rechts oben
  J4/J5. SW3 (RESET) sitzt in der Lasche rechts neben dem Akkuschutz (13,8/−7,2); EN läuft auf In2 an der
  Oberkante (y 0,7) und bei x 16,9 die Lasche hinauf. Abzug/Nachladen laufen im B.Cu-Bündel die linke
  Spalte (x 7,8/8,6) hinunter und unter 45° zu Vias über den Tastern; Lautsprecher OUTP/OUTN von Vias rechts
  von H2 auf B.Cu entlang der Unterkante (y 44,95/45,5) zu Vias neben SP1; TSOP 1–5 von Vias unter den
  Modul-Pads unter 45° auf B.Cu in Spalten x 45,0–47,4; TSOP 1–3 über Vias links der J2-Pads, TSOP 4/5 auf
  B.Cu unter den Pads durch zu Vias rechts davon (x 50,4, unter dem J2-Körper; links wären sie zu nah an den
  I²S-Diagonalen); J2 bei y 32,7; 3V3 für J2 über In2 rechts neben dem Modul (x 51,6) zum Via (50,4/35,7).
- **Vibration:** ein Motor M1 (Rückstoß + Treffer) an IO47 über Q2/R11/R12/D1. I²S läuft
  neben dem Modul nach unten (Spalte beim Modul c = 70,9 / 71,6 / 72,3, an M1 vorbei) und dann mit einer
  45°-Diagonale (x + y = 75,55 / 76,3 / 77,05) über J2 hinweg zu U6, BCLK/LRCLK zuletzt senkrecht (x 43,9 /
  44,5) von rechts in U6.
- **Flash U14 (SPI-NAND, WSON-8 8×6, 38,6/28,7):** unter dem Modul zwischen C1 und R12/D1, C25 (100 n)
  und R27 (/CS-Pull-up) darüber auf y 24,6. SPI über IO7 (/CS, Pad 7), IO15 (MISO, Pad 8), IO3 (MOSI,
  Pad 15), IO46 (CLK, Pad 16): Vias neben den Pads (x 35,0 bzw. y 18,0), B.Cu-Bündel x 34,0 / 34,6 /
  35,2 / 35,8 links am IO0-Via (36,7/20,75) vorbei; /CS und MISO über Vias bei x 34,0 von links in
  Pin 1/2, MOSI/CLK unter U14 als 45°-Diagonalen zu Vias bei x 43,65 rechts von Pin 5/6 (x 43,65 hält
  die In2-5V-Diagonale x + y = 71,9 frei). 3V3: In2-Abzweig von x 51,6 auf y 23,7 zu den Vias über
  C25.1 und R27.1, von dort In2-Diagonale zum /WP-Via (34,0/29,3); /HOLD direkt an VCC (Pin 7–8);
  GND über Pin 4 → EP → Via im EP (37,4/30,0).
- **microSD J7 (TF-018, Push-Pull, Projektbibliothek, 47,45/42,1, 0°):** Die Karte wird auf der Kontaktseite
  eingesteckt (Datenblatt Hanbo TF-018: Karte ragt über den Lötbeinchen heraus). Kontaktreihe und Öffnung
  daher an der Unterkante (Pads 0,3 mm vom Rand), geschlossene Rückwand oben bei y 38,4 unter U6/J2
  (Courtyards berühren sich gerade). Alle Leitungen auf F.Cu senkrecht unter dem Slot zu den Kontakten:
  MOSI/MISO (B.Cu-Fächer aus den U14-Vias) und SD_CS (B.Cu x 51,0) über Vias bei y 39,2; CLK kreuzt MOSI und
  wechselt deshalb über dem Slot (Via auf x + y = 79,5) auf F.Cu; VDD gerade nach C26 (0402, 48,0/37,0, 90°),
  3V3 über ein Via auf dieser Leitung von In2; GND-Via direkt über Pin 6; DAT1/DAT2 über Vias bei y 43,9 und
  In2 (y 42,6) verbunden, DAT2 senkrecht zu R37. Schirm-Pads mit GND-Vias außen (oben links nach unten).
- **Akkuschutz (Lasche):** Q3 FS8205A (4,2/−2,4) und U15 DW01A (10,8/−2,4) mit zueinander zeigenden Gates
  (OD–G1 oben, OC–G2 unten, gerade), R29 (CS, 1 k) dazwischen mit GND-Via, Q3.2–Q3.5 unter dem Körper,
  S2 = GND mit zwei Vias. B− (`BAT_N`): BT1.2 → zwei Vias → B.Cu x 5,4 (0,8 mm) → zwei Vias über Q3.1;
  F.Cu-Leitung y −4,3 verbindet C27 (VSS), U15.6 (45°-Abzweig) und Q3.1. VCC über C27/R28 (y −2,4), R28.1 über ein
  Via (14,2/−1,0) an die In2-Leitung `BAT_P`.
- **IP5306 (U1, Laden + 5 V) oben links, HSOP-8 mit Thermal-Vias, 180° bei (19,6/3,5):** linke Padreihe
  KEY/BAT/SW/VOUT, rechte NC/SDA/SCL/VIN. L1 (1 µH, 270°) links daneben zwischen BT1 und U1: SW U1.7 → L1.1
  gerade (1,0 mm), Akku BT1.1 → L1.2 1,2 mm unter 45°, weiter C19 (22 µ) → R8/R7 → C7 (IR, y 11,44), Abzweig rechts von R8 (x 12,95) → R3 (Teiler 1 M/1 M, R4/C6 bei
  y 18,5 unter H1). BAT-Messeingang: Via (8,6/2,9) → R2 (1 Ω, oben in der Lasche) → C5 (22 µ) → U1.6 auf y 2,45.
  VOUT → C20 (22 µ, unter U1) → Lastschalter U16 (SOT-23-6, 20,3/8,1, GND-Via unter dem Gehäuse) → zwei Vias
  (20,5/6,2), (21,6/6,2) in den In2-5V-Stamm (1,2 mm, y 7,15 → Diagonale x − y = 17,9); C30 (10 µ, 0603) über eine
  0,3-mm-Gasse x 18,175 links unter U16. U16-EN = IRQ: U1.4 → Via (20,6/1,85) unter U1 → In2 x 19,6 zwischen den
  Thermal-Vias hinunter → Via (19,6/9,9) → EN-Pad und R42 (100 k nach GND); CT → C33 (10 n). R42/C33 teilen sich das
  GND-Via (20,35/12,58) oberhalb des B.Cu-Bündels; Abzweig zu WS2812/C10 1,0 mm. Akku-Minus B.Cu 1,2 mm, je drei Vias an BT1.2
  und Q3.1. Weste-3V3 über R35 (10 Ω, 0402, 52,4/37,1) zwischen dem 3V3-Via (52,8/35,7) und J2.1.
  VIN: Pad 1 senkrecht x 22,7 (C4 0603 unter 45° rechts unter U16; Dämpfung R1/C29 an der B.Cu-VBUS-Leitung
  bei der USB-Buchse über ein Via (25,2/31,0)) zu zwei Vias (22,7/11,4), (24,0/11,4) unter
  dem B.Cu-Bündel (x + y > 33); In2 1,6 mm um das 3V3-Via (26,3/15,0) herum zu den Vias (28,6/17,2), (27,9/17,9);
  B.Cu 1,0 mm senkrecht x 25,2 hinunter zur USB-C-Buchse (vl). GND-Vias unter U1/C4 nur außerhalb des Bündels
  (x + y 28,75…32,65 frei halten). I²C: SDA-Via (23,6/2,865), SCL-Via (24,0/4,135) rechts von U1; Pull-up R40 (SCL)
  rechts von C3 an R21.1 (3V3), Via (27,0/2,6) auf der SCL-Bahn; Pull-up R38 (SDA) direkt unter IO9 (38,05/21,6),
  3V3 vom R27-Via.
- **Ein/Aus (Lasche):** D6 (BAT54CW, kleiner Sperrstrom, 6,0/−6,7) und R24 (10 k, 9,5/−6,05); KEY F.Cu von U1.5 die Lasche hinauf
  (x 16,6) und waagerecht zu R24. B.Cu-Bahnen an der Oberkante (oben → unten = Riser rechts → links): PWR_KEY
  y 0,45 (J5, Riser x 50,0), ENC_SW y 0,9 (IO21, x 45,68) – beide in die Lasche (x 18,05/17,6) zu D6 –, IP_SDA
  y 1,35 (IO9, x 38,05) und IP_SCL y 1,8 (IO18, Via (35,6/14,19) unter dem Modul, Riser x 35,6) zu den U1-Vias.
  GPIO-Zuordnung folgt dieser Reihenfolge (sonst Kreuzungen). IO0 läuft auf B.Cu unter dem IO21-Via (y 18,7) zu
  BOOT. D4 (VBUS → 5 V) waagerecht bei (24,4/27,0): Anode an Via auf der VBUS-B.Cu-Leitung, Kathode zu C31.1
  (22 µ, 5-V-Via 21,8/28,48).
- **WS2812-Pegelwandler:** Q4 (2N7002, 180°, 13,6/26,82) in Gateschaltung: Source vom B.Cu-Via (15,6/24,2) der
  WS2812-Diagonale, Drain → R15.1 → R25 (1 k nach 5 V an J1.2), Gate über Via (16,2/28,075) und In2-Abzweig der
  3V3-Diagonale. C10/C32 (22 µ) übereinander rechts der J1-5V-Diagonale. In2 `BAT_P` nur noch BT1-Via → R28-Via (DW01A VCC).
- **TSOP-Serienwiderstände:** R30–R34 (0402, 100 Ω) bei x 52,0 auf y 33,7 … 29,7 zwischen den Vias und den
  J2-Pads (J2 bei x 56,5); J2.1-3V3-Via (52,8/35,7), J2.2-GND-Via (52,8/34,7).
- **Bedienteil-Routing:** SCL/SDA (IO1/IO2) auf F.Cu direkt in J4; 3V3 für J4 über In2 von einem Via an
  Modul-Pin 2 (35,0/2,76) waagerecht nach rechts; ENC_A (IO42) auf F.Cu von oben in J5.4; ENC_B (IO41)
  über B.Cu zu einem Via hinter den J5-Pads (unter dem Steckerkörper); J5.2 ist PWR_KEY (siehe Ein/Aus). Die
  I²S-Leitungen laufen links neben den J5-Pads (0,175 mm Abstand) – J5 nicht weiter nach links.

## Routing-API in build_board.py

```python
r.t(layer, width, *points, net=None)   # layer "F"/"2"/"B"; points: "U4.12" | (x, y) | ("R3.1", dx, dy)
r.v(point, net=None, d=0.5, h=0.3)     # Via; ohne net -> Netz des vorigen Tracks
r.gnd("C8.2", dx, dy)                  # GND-Pad -> Stich -> eigenes Via
r.drop("C31.1", dx, dy)                # Power-Pad -> Stich -> Via (zu In2)
```

- `r.t` wird erst in `flush()` gezeichnet: `octilinear()` zerlegt schräge Abschnitte in gerade + 45°
  und fast 90°-Ecken ab; `split_at()` setzt Abzweigpunkte als Stützpunkte (sonst meldet KiCad „track_dangling“).
  Endpunkte eines Aufrufs sind „gepinnt“ und werden **nicht** abgefast → Ecken an Übergängen zwischen zwei
  Aufrufen selbst mit 45°-Stück planen oder den Pfad in **einem** Aufruf führen.
- Abzweig richtig: Startpunkt auf der Hauptleitung, erstes Stück 45° weg (z. B. `(30.2, 27.4), (29.6, 28.0), ...`).
- Pads mit doppelter Nummer (z. B. `U2.2` = Pin + Tab) per Koordinate ansprechen, nicht per Referenz.
- Mehrere Signale aus einer Pad-Reihe: Reihenfolge der Pads = Reihenfolge der Ziele, sonst Kreuzungen.
  Lieber GPIO-Zuordnung im Schaltplan (`MCU_SIGNALS` in build_clean.py) anpassen als Vias stapeln.

## Ablauf (immer so)

1. **Backup** von `build_board.py` in den Scratchpad, bevor größere Edits laufen. Edits nur mit eindeutigen
   `str.replace`/`assert s.count(a) == 1` – nie mit breiten `s.index(...)`-Slices (hat einmal den ganzen
   Routing-Teil gelöscht).
2. Netzliste: `kicad-cli sch export netlist -o board.net waffe_elektronik.kicad_sch`
3. Bauen in den Scratchpad: `NETLIST=board.net OUT_PCB=<scratch>/w.kicad_pcb python3 build_board.py`
4. Prüfen (alle drei müssen sauber sein):
   - `python3 tools/pcbtools.py w.kicad_pcb` → Courtyard-Überlappungen
   - `python3 tools/drc.py w.kicad_pcb [x0 y0 x1 y1] [-u]` → DRC (0 Verstöße, 0 unconnected);
     braucht die gleichnamige `.kicad_pro` daneben (schreibt build_board.py mit), sonst gelten KiCad-Standardregeln
   - `python3 tools/angles.py w.kicad_pcb [-v]` → 0 non-octilinear, 0 bends>45, 0 T-joins>45
   - `python3 tools/detour.py w.kicad_pcb [--layers=F,2,B] [--min=0.5]` → Umwege: jeder Lauf zwischen
     Vias/Pads/Abzweigen gegen den kürzesten 0/45/90°-Weg. Jeder Fund ist entweder behoben oder hat einen
     Grund (Hindernis, Bündelreihenfolge, Paar-Längenausgleich). Stand (begründet): F.Cu IP_KEY (Akkuschutz-Reihe in der
     Lasche), F.Cu U1-BAT (C5.2), In2 VBUS (um das 3V3-Via), I²S (Modul-Padreihe, Motortreiber; Rückseite bräuchte 6 Vias), B.Cu SPI_CLK/SPI_MOSI (links um das
     IO0-Via und dessen B.Cu-Diagonale), B.Cu SD_CS (rechts um die TSOP-4/5-Vias), B.Cu SPI_MOSI am Slot
     (Kreuzung mit CLK), In2 SD_DAT12 (um die Kontakt-Vias), B.Cu PWR_KEY/ENC_SW/IP_SDA/IP_SCL (über die
     Oberkante), B.Cu TSOP4/5 (Vias rechts von J2), USB D+ (Mäander),
     USB D− (außen um U12.4/VBUS-Via), 5V an U6 (um unbelegte IC-Pins), OUTP/OUTN (verschachtelt),
     J1→C10 (über C32, GND-Via J1.3), Q4-Drain (über R15.1), IR_LED_K (um die J6-Vias), BAT_P-Ende (Abzweig); In2 5V am
     U6-Abzweig (+0,2); B.Cu TRIGGER/RELOAD (Bündel), In2 EN (Oberkante zur Lasche), F.Cu VOUT zu C30 (Gasse um U16), VBUS-Ring (um die USB-Pads)
   - `python3 tools/silk.py w.kicad_pcb --gap=0.15 [--suggest]` → 0 silk problems (Hinweis für
     `BACK_LABELS` ist ok); `--place --angle=0 --gap=0.15 "TEXT=REF" ...` sucht für Labels die freie
     waagerechte Stelle am nächsten an ihrem Stecker, eindeutig näher an ihm als an den anderen
     genannten REFs (immer alle Stecker-REFs mitgeben). Vorschläge > ~1 mm vom Stecker von Hand
     verbessern (Lücken über/unter/neben dem Stecker), dann mit `silk.py` prüfen und im 3D-Render
     (`kicad-cli pcb render --side top`) auf Zuordnung und Lesbarkeit ansehen
5. Ansehen: `python3 tools/view.py w.kicad_pcb out.png x0 y0 x1 y1 --layers=F,B --scale=0.9`
   (Gitter in mm, Netznamen auf Pads, Teardrops deckend) und Bild mit Read anschauen.
   `python3 tools/padmap.py w.kicad_pcb GND 3V3_MCU ...` listet Pad-Koordinaten je Netz.
6. Erst wenn alles sauber ist ins Projekt schreiben (`OUT_PCB=../waffe_elektronik.kicad_pcb`) und dort
   `kicad-cli pcb drc --schematic-parity` laufen lassen (Parität 0). Erwartet sind nur die Warnungen
   `lib_footprint_mismatch` für U4 (Modul-Silk jenseits der Kante entfernt) und H1/H2 (Courtyard auf
   Schraubenkopf verkleinert). DRC-Testschleifen deshalb auf 3 × `lib_footprint_mismatch` prüfen.
7. Renders: `kicad-cli pcb render --side top|bottom ...` nach `renders/platine_oben.png`, `platine_unten.png`,
   `platine_3d.png` (`--perspective --rotate "-35,0,20"`).

## Bekannte Stolpersteine

- Teardrop-Generator von KiCad ist in Python nicht erreichbar → `teardrops()` erzeugt Zonen
  `$teardrop_padvia$`, das Attribut `(attr (teardrop (type padvia)))` wird nach dem Speichern in die Datei
  geschrieben. Prüfen: `z.IsTeardropArea()` nach `LoadBoard`.
- Schaltplan-Parität braucht `SetFPID(LIB_ID(lib, name))`, `SetPath(KIID_PATH("/<Blatt>/<Symbol>"))` und die
  Netznamen der Netzliste (globale Labels: ohne `/`); der Routing-Code nutzt die Kurznamen.
- `PCB_VIA.GetWidth()` braucht einen Layer (`GetWidth(pcbnew.F_Cu)`).
- **Projekt-Footprints:** `footprints/<lib>.pretty` + `fp-lib-table`; build_board.py lädt eine Bibliothek von dort,
  wenn es den Ordner gibt, sonst aus `FPLIB`. Kein `Datasheet`-Feld im Footprint (sonst Paritätsfehler).
- **3D-Modelle:** jedes Bauteil braucht eins (Render, Gehäuse-STEP). J3: `freecadcmd scripts/gen_3d_usb_c_vertical.py`
  (Pfad steht im Footprint). KiCad liefert für JST-PH-SM4 (BT1, SP1, J1)
  keine → eigene Modelle in `3dmodels/`, erzeugt mit `freecadcmd scripts/gen_3d_jst_ph_sm4.py` (STEP + farbige
  WRL, Maße aus Footprint-F.Fab, Höhe 4,85 wie S*B-PH-K). `OWN_MODELS` in build_board.py setzt den Pfad
  `${KIPRJMOD}/3dmodels/<name>.wrl`; KiCad nimmt beim STEP-Export die `.step` daneben. Prüfen: Skript-Check
  „missing models: []“ (alle Modellpfade auflösen) und `kicad-cli pcb export step --subst-models` ohne Warnung.
  Fehlt künftig ein Modell: erst KiCad-Bibliothek/`kicad-packages3D`, sonst eigenes Modell nach diesem Muster.
- pcbnew-Python: `for m in fp.Models()` liefert Kopien → Änderungen nur per Index (`models[i].m_Filename = ...`).
- Schaltplan hierarchisch: `build_clean.py` schreibt das Übersichtsblatt nach `OUT_SCH` und die fünf Unterblätter
  (`PAGES`) daneben; Labels sind global, Symbol-Instanzpfade `/<Blatt-UUID>`, `build_board.py` setzt den
  Footprint-Pfad aus `sheetpath`-tstamps + Symbol-UUID der Netzliste. Blattsymbole in einer Spalte (KiCad
  nummeriert die Seiten nach Lage). Zum Testen in den Scratchpad schreiben: alle Seiten landen im selben Ordner.
- Schaltplan: `build_clean.py` schreibt die Projekt-Symbolbibliothek `symbols/lasertag.kicad_sym` (FS8205A,
  angepasste Pin-Typen) aus dem erzeugten Schaltplan; Ziel ist `kicad-cli sch erc --severity-all` mit 0 Meldungen.
- `kicad-cli` schreibt beim Export KiCads Standard-ERC-Abschnitt in die `.kicad_pro` → vor dem Commit
  `git checkout` der `.kicad_pro`, wenn sonst nichts geändert wurde.
- TQFN-16 EP1.23 wird beim Speichern auf das EP1.6-Modell umgebogen.
- Läuft KiCad/Eeschema mit dem Projekt, nach dem Schreiben auf Neuladen hinweisen; KiCad kann die `.kicad_pro`
  beim Schließen überschreiben.
- Labels: Courtyards sind für die Platzsuche zu groß (Sicherheitsrand) → `silk.py` nutzt den F.Fab-Umriss.
  Für Texte zählt die Strichkontur (`GetEffectiveTextShape().BBox()`, bei 0,8 mm ≈ 0,92 mm hoch), nicht
  `GetBoundingBox()` (≈ 1,36 mm mit Zeilenabstand) – sonst findet die Suche viele echte Lücken nicht.
- Label-Stand: LED/TSOP unter J6 (4,2/23,4), WS2812 rechts neben J1, LAUTSPR. unter
  SP1, TASTER rechts neben J8 (19,0/40,43), „VIB“ unter M1, SENSOR unter J2 (56,5/39,3), „1“ unter J2-Pin 1 (54,1/36,95),
  „SD“ links über J7 (40,9/40,13),
  USB über J3, AKKU rechts neben BT1, RESET über SW3,
  BOOT links neben SW4 auf Mittelhöhe, U14 ohne Label, Titel „open-lasertag v1“ auf der Rückseite unter der URL,
  „OLED“/„GEBER“ unter J4/J5 auf gemeinsamer Achse x = 56,95 („DREHGEBER“ zu lang für den Streifen).
- Wegpunkte, die auf einem Via enden sollen, exakt auf die Via-Koordinate legen (z. B. 31,39 statt 31,4);
  sonst hängt die Verbindung nur über Kupfer-Überlappung und `detour.py` erkennt das Via nicht als Halt.
- Verzweigungen: der Abzweig darf nicht am Knickpunkt des Stamms beginnen (sonst 90° zum weiterlaufenden
  Stamm) → Abzweigpunkt auf das gerade Stück davor legen.
- `pkill -f <muster>` trifft die eigene Shell, wenn das Muster im Befehl steht → `pgrep -f "name[s]"`.
