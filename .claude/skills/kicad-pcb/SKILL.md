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
- **So kurz wie möglich, so lang wie nötig.** Keine L-Form, wo ein 45°-Abschnitt passt: langer Weg =
  kurzes Gerades + **ein** langer 45°-Lauf + kurzes Gerades. Parallele Bündel als Ganzes schräg führen
  (gleiche Reihenfolge, Diagonalen parallel, Abstand der Diagonalen über `x+y` bzw. `x−y` planen).
  Umwege nur um echte Hindernisse (Pads, Vias anderer Netze, Bauteile auf der eigenen Lage) und für
  Längenausgleich (USB-Paar). Prüfen mit `tools/detour.py`.
- **Beschriftung auf der Vorderseite** (`F.SilkS`, nicht gespiegelt), **lesbar mit bestückten Bauteilen**:
  kein Text auf Pads, Bauteilkörpern (F.Fab-Umriss), Footprint-Silk, anderen Texten, ≥ 0,3 mm vom Rand.
  Jedes Steckerlabel direkt an **seinem** Stecker, näher an ihm als an jedem Nachbarn. Höhe 0,8 mm
  (Minimum), Strich 0,12. Was vorne keinen Platz hat (Projekt-URL), geht in `BACK_LABELS` auf `B.SilkS`.
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
  - B.Cu: lange Signale + GND-Fläche + Beschriftung (gespiegelt)
- Jedes GND-Pad bekommt ein eigenes Via nach In1 (`r.gnd`), Stromversorgungs-Pads ein Via nach In2 (`r.drop`).
- Netzklassen/Regeln stehen in `RULES`/`NETCLASSES` und werden von `write_project()` in die `.kicad_pro` geschrieben:
  min. 0,15 mm Bahn/Abstand, Vias 0,5/0,3 (USB-Kreuzung 0,4/0,2), Default 0,2, Power 0,5, 3V3 0,6, USB-Paar 0,2/0,2.
- ESP32-S3-WROOM-1: Antenne ragt über die Oberkante (`MX, MY`), 100 nF + 10 µF und EN-RC direkt an den Pins.
- Randstecker: Body bündig, aber Befestigungspads ≥ 0,3 mm vom Rand (`SH_IN = 3.1`, `PH_IN = 4.9`).

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
     Grund (Hindernis, Bündelreihenfolge, Paar-Längenausgleich). Stand: B.Cu nur noch EN/RELOAD (Bündel)
     und VBUS-Ring (um die USB-Pads), F.Cu I²S (um Modul-Padreihe und Motortreiber)
   - `python3 tools/silk.py w.kicad_pcb --gap=0.15 [--suggest]` → 0 silk problems (Hinweis für
     `BACK_LABELS` ist ok); `--place "TEXT=REF" ...` sucht für Labels die freie Stelle (0°/90°) am
     nächsten an ihrem Stecker, eindeutig näher an ihm als an den anderen genannten REFs;
     Ergebnis danach im 3D-Render (`kicad-cli pcb render --side top`) auf Zuordnung prüfen
5. Ansehen: `python3 tools/view.py w.kicad_pcb out.png x0 y0 x1 y1 --layers=F,B --scale=0.9`
   (Gitter in mm, Netznamen auf Pads, Teardrops deckend) und Bild mit Read anschauen.
   `python3 tools/padmap.py w.kicad_pcb GND 3V3_MCU ...` listet Pad-Koordinaten je Netz.
6. Erst wenn alles sauber ist ins Projekt schreiben (`OUT_PCB=../waffe_elektronik.kicad_pcb`) und dort
   `kicad-cli pcb drc --schematic-parity` laufen lassen (Parität 0). Erwartet ist nur die Warnung
   `lib_footprint_mismatch` für U4 (Modul-Silk jenseits der Kante entfernt).
7. Renders: `kicad-cli pcb render --side top|bottom ...` nach `renders/platine_oben.png`, `platine_unten.png`,
   `platine_3d.png` (`--perspective --rotate "-35,0,20"`).

## Bekannte Stolpersteine

- Teardrop-Generator von KiCad ist in Python nicht erreichbar → `teardrops()` erzeugt Zonen
  `$teardrop_padvia$`, das Attribut `(attr (teardrop (type padvia)))` wird nach dem Speichern in die Datei
  geschrieben. Prüfen: `z.IsTeardropArea()` nach `LoadBoard`.
- Schaltplan-Parität braucht `SetFPID(LIB_ID(lib, name))`, `SetPath(KIID_PATH("/" + uuid))` und volle Netznamen
  (`/TRIGGER`); der Routing-Code nutzt die Kurznamen ohne `/`.
- `PCB_VIA.GetWidth()` braucht einen Layer (`GetWidth(pcbnew.F_Cu)`).
- Keine STEP-Modelle für JST-PH-SM4 (BT1, J1, SP1); TQFN-16 EP1.23 wird beim Speichern auf das EP1.6-Modell umgebogen.
- Läuft KiCad/Eeschema mit dem Projekt, nach dem Schreiben auf Neuladen hinweisen; KiCad kann die `.kicad_pro`
  beim Schließen überschreiben.
- Labels: Courtyards sind für die Platzsuche zu groß (Sicherheitsrand) → `silk.py` nutzt den F.Fab-Umriss.
  JST-PH-Stecker (BT1, J1, SP1) haben kein 3D-Modell, im Render fehlt ihr Körper; F.Fab gilt trotzdem.
- `pkill -f <muster>` trifft die eigene Shell, wenn das Muster im Befehl steht → `pgrep -f "name[s]"`.
- Offener Schaltplanpunkt: C7 hängt zwischen BAT und LED-Kathode statt an GND (User informiert, unverändert).
