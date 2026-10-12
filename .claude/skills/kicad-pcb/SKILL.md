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
  Zusatzlänge pro Ausbuchtung 2h − 4c(2 − √2)); Zielwert `USB_TUNE`. Prüfen mit
  `tools/pairlen.py w.kicad_pcb U4.14-U12.4 U4.13-U12.6 U12.3-J3.B6 U12.1-J3.B7 U12.3-J3.A6 U12.1-J3.A7 --via=0`
  (je Paar-Abschnitt zwischen denselben Bauteilen; Stand: alle 0,000 mm). Die D−-Brücke A7 über B.Cu hat
  zwei Vias mehr als A6 – mit `--via=1.6` sichtbar; Via-Paar bei USB-C-Kreuzung ist nicht vermeidbar.
- **Beschriftung auf der Vorderseite** (`F.SilkS`, nicht gespiegelt), **lesbar mit bestückten Bauteilen**:
  kein Text auf Pads, Bauteilkörpern (F.Fab-Umriss), Footprint-Silk, anderen Texten, ≥ 0,3 mm vom Rand.
  Jedes Steckerlabel direkt an **seinem** Stecker, näher an ihm als an jedem Nachbarn.
  **Alle Labels an Steckern, Klemmen und Tastern waagerecht (0°) und einheitlich: gleiche Höhe 0,8 mm
  (Minimum), Strich 0,12, nie gedreht** – auch der Projekttitel. Lieber eine Lücke weiter am Stecker
  (oben/unten/neben) als ein senkrechtes Label. Pin 1 von Steckern mit „1“ markieren, wenn die
  Footprint-Silk es nicht schon tut.
  **Mehrere Stecker in einer Reihe/Spalte:** ihre Labels gemeinsam ausrichten – in einer Spalte (links
  LED1/TSOP/ABZUG/NACHL., rechts VIB) gleiche Mittelpunkt-x (horizontal zentriert
  untereinander), jedes Label direkt am eigenen Stecker (nie zwei Labels zwischen zwei Steckern so, dass
  beide zum selben zu gehören scheinen). Reihe (unten J1/J3/J2/SP1): gemeinsame y geht wegen
  unterschiedlicher Steckerhöhen nicht → jedes Label mittig (gleiche x) über seinem Stecker.
  Suche: `silk.py --column "A=REF" ...` bzw. `--row`; Mindestabstand Label ↔ Pad/Via/Körper/Silk 0,12 mm.
  Die gefundenen Werte sind Mittelpunkte der Strichkontur; KiCad-Textanker liegt bis 0,1 mm daneben
  (y ≈ +0,036) → nach dem Setzen immer `silk.py --gap=0.12` laufen lassen.
  Unter Labels keine Vias: `stitch()` hält Textflächen frei, `silk.py` prüft Vias mit Leiterbahn. Was vorne keinen Platz hat (Projekt-URL), geht in `BACK_LABELS` auf `B.SilkS`.
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
  (keine Bahnen, Vias, Füllung). Lage diagonal: H1 (20,5/14,9) neben U2, H2 (42,2/42,5) mittig zwischen
  J2 und SP1 (dort nur 3,51 mm zwischen den Courtyards → größere Köpfe/M2,5/M3 passen nicht).
  Freie Stellen suchen: größte freie Kreise gegen Pads, Körper, Bahnen, Vias mit Bahn und Texte.
  Mehr Löcher oder größere Schrauben nur mit größerer Platine.
- ESP32-S3-WROOM-1: Antenne ragt über die Oberkante (`MX, MY`), 100 nF + 10 µF und EN-RC direkt an den Pins.
- Randstecker: Body bündig, aber Befestigungspads ≥ 0,3 mm vom Rand (`SH_IN = 3.1`, `PH_IN = 4.9`).
- **Kontur L-förmig:** `W0` = 54 (Hauptplatine; Modul `MX = W0 − 11,5`, M1 an `W0`), `W` = 59,6 nur für
  y < `Y1` = 18,5 (Streifen für J4 OLED oben, J5 Drehgeber darunter, Öffnung nach rechts). Masseflächen und
  Stitching folgen der L-Kontur. Neue Teile an der Kante: `W` bzw. `W0` je nach Höhe verwenden, nie
  Modul/Bestand an `W` koppeln.
- **TSOP 6 (J6, links unter LED1, JST-SH 3 = ZX-SH1.0-3PWT):** 1 VS (3V3 über Via + In2-Abzweig der
  3V3-Diagonale), 2 GND (Via rechts), 3 OUT von IO16: B.Cu-Kanal Diagonale x + y = 38,0 (zwischen
  H1-Sperrfläche und R2-3V3-Via, H1 dafür auf 20,4/14,8, U2-GND-Via auf (−1,2/0,3)), letztes Stück
  F.Cu von unten rechts. Filter 100 Ω + 4,7 µF sitzt am Sensor (U13/R26/C24 nicht auf der Platine).
  Linker Rand ist auf B.Cu durch das EN/Abzug/Nachladen/IR-Bündel abgetrennt → Signale zu linken
  Steckern immer zuletzt auf F.Cu.
- **Vibration:** ein Motor M1 (Rückstoß + Treffer) an IO47 über Q2/R11/R12/D1; IO48 frei. I²S läuft
  neben dem Modul nach unten und dann mit einer 45°-Diagonale (x + y = 76,55 / 79,45 / 80,45) direkt
  zu U6 durch die frei gewordene Fläche.
- **Bedienteil-Routing:** SCL/SDA (IO1/IO2) auf F.Cu direkt in J4; 3V3 für J4 über In2 von einem Via an
  Modul-Pin 2 (35,0/2,76) waagerecht nach rechts; ENC_A (IO42) auf F.Cu von oben in J5.4; ENC_B (IO41)
  und ENC_SW (IO9, unten am Modul) über B.Cu zu Vias hinter den J5-Pads (unter dem Steckerkörper). Die
  I²S-Leitungen laufen links neben den J5-Pads (0,175 mm Abstand) – J5 nicht weiter nach links.

## Routing-API in build_board.py

```python
r.t(layer, width, *points, net=None)   # layer "F"/"2"/"B"; points: "U4.12" | (x, y) | ("R3.1", dx, dy)
r.v(point, net=None, d=0.5, h=0.3)     # Via; ohne net -> Netz des vorigen Tracks
r.gnd("C8.2", dx, dy)                  # GND-Pad -> Stich -> eigenes Via
r.drop("C21.1", dx, dy)                # Power-Pad -> Stich -> Via (zu In2)
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
     Grund (Hindernis, Bündelreihenfolge, Paar-Längenausgleich). Stand (begründet): F.Cu CHRG_STAT (U2-Pins
     + BAT_P-Via an R3), I²S (Modul-Padreihe, Motortreiber; Rückseite bräuchte 6 Vias), USB D+ (Mäander),
     USB D− (außen um U12.4/VBUS-Via), 5V an U6 (um unbelegte IC-Pins), OUTP/OUTN (verschachtelt),
     J1→C10 (GND-Via J1.3), R15 (U5-Padreihe), GND-Stiche an U5, BAT_P-Ende (Abzweig); In2 5V am
     U6-Abzweig (+0,2); B.Cu EN/TRIGGER/RELOAD (Bündel), VBUS-Ring (um die USB-Pads)
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
- Schaltplan-Parität braucht `SetFPID(LIB_ID(lib, name))`, `SetPath(KIID_PATH("/" + uuid))` und volle Netznamen
  (`/TRIGGER`); der Routing-Code nutzt die Kurznamen ohne `/`.
- `PCB_VIA.GetWidth()` braucht einen Layer (`GetWidth(pcbnew.F_Cu)`).
- **3D-Modelle:** jedes Bauteil braucht eins (Render, Gehäuse-STEP). KiCad liefert für JST-PH-SM4 (BT1, SP1, J1)
  keine → eigene Modelle in `3dmodels/`, erzeugt mit `freecadcmd scripts/gen_3d_jst_ph_sm4.py` (STEP + farbige
  WRL, Maße aus Footprint-F.Fab, Höhe 4,85 wie S*B-PH-K). `OWN_MODELS` in build_board.py setzt den Pfad
  `${KIPRJMOD}/3dmodels/<name>.wrl`; KiCad nimmt beim STEP-Export die `.step` daneben. Prüfen: Skript-Check
  „missing models: []“ (alle Modellpfade auflösen) und `kicad-cli pcb export step --subst-models` ohne Warnung.
  Fehlt künftig ein Modell: erst KiCad-Bibliothek/`kicad-packages3D`, sonst eigenes Modell nach diesem Muster.
- pcbnew-Python: `for m in fp.Models()` liefert Kopien → Änderungen nur per Index (`models[i].m_Filename = ...`).
- `kicad-cli` schreibt beim Export KiCads Standard-ERC-Abschnitt in die `.kicad_pro` → vor dem Commit
  `git checkout` der `.kicad_pro`, wenn sonst nichts geändert wurde.
- TQFN-16 EP1.23 wird beim Speichern auf das EP1.6-Modell umgebogen.
- Läuft KiCad/Eeschema mit dem Projekt, nach dem Schreiben auf Neuladen hinweisen; KiCad kann die `.kicad_pro`
  beim Schließen überschreiben.
- Labels: Courtyards sind für die Platzsuche zu groß (Sicherheitsrand) → `silk.py` nutzt den F.Fab-Umriss.
  Für Texte zählt die Strichkontur (`GetEffectiveTextShape().BBox()`, bei 0,8 mm ≈ 0,92 mm hoch), nicht
  `GetBoundingBox()` (≈ 1,36 mm mit Zeilenabstand) – sonst findet die Suche viele echte Lücken nicht.
- Label-Stand: linke Spalte x = 4,2 (LED1 unter LED1, TSOP/ABZUG/NACHL. über ihrem Stecker), rechte
  „VIB“ über M1 (x = 49,85), USB/SENSOR/LAUTSPR. mittig über J3/J2/SP1,
  AKKU rechts neben BT1, RESET über SW3, WS2812 links neben J1 (über J1 kein Platz), „1“ an J2-Pin 1,
  BOOT links neben SW4 auf Mittelhöhe, Titel „open-lasertag v1“ frei in der Mitte (19,5/17,9),
  „OLED“/„GEBER“ unter J4/J5 auf gemeinsamer Achse x = 56,95 („DREHGEBER“ zu lang für den Streifen).
- Wegpunkte, die auf einem Via enden sollen, exakt auf die Via-Koordinate legen (z. B. 31,39 statt 31,4);
  sonst hängt die Verbindung nur über Kupfer-Überlappung und `detour.py` erkennt das Via nicht als Halt.
- Verzweigungen: der Abzweig darf nicht am Knickpunkt des Stamms beginnen (sonst 90° zum weiterlaufenden
  Stamm) → Abzweigpunkt auf das gerade Stück davor legen.
- `pkill -f <muster>` trifft die eigene Shell, wenn das Muster im Befehl steht → `pgrep -f "name[s]"`.
- Offener Schaltplanpunkt: C7 hängt zwischen BAT und LED-Kathode statt an GND (User informiert, unverändert).
