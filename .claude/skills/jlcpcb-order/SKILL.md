---
name: jlcpcb-order
description: Generate a ready-to-order JLCPCB package (Gerber zip, drill, BOM, CPL) from the KiCad board, pick LCSC parts that are in stock and check them. Use when the user wants to order boards/assembly at JLCPCB, needs Gerber/BOM/CPL files or LCSC part numbers.
---

# JLCPCB-Bestellung (Leiterplatte + SMT-Bestückung)

Projekt: `kicad/waffe_elektronik/`. Werkzeuge in `tools/` neben dieser Datei
(System-`python3` mit `pcbnew`, `kicad-cli` 10).

## 1. LCSC-Teile auswählen

- Jedes Bauteil auf der Platine braucht ein Feld **`LCSC`** (z. B. `C25804`). Quelle ist der Schaltplan:
  `LCSC` / `LCSC_0603` in `scripts/build_clean.py`; `scripts/build_board.py` übernimmt das Feld aus der
  Netzliste in die Footprints (sonst meldet die Schaltplan-Parität „Fehlendes Symbolfeld LCSC“).
- Suchen: `python3 tools/jlc_search.py "<Suchbegriff oder C-Nummer>" [n]` → Code, Typ, Gehäuse,
  **basic/ext**, Lager, Stückpreis (JLCPCB-Teile-API).
- Auswahlregeln:
  1. Footprint muss exakt passen (Gehäusecode in der Liste prüfen, z. B. SOD-123F = SOD-123FL, Case B = 3528).
  2. **Basic** vor Extended (Extended kostet je Teilenummer eine Rüstgebühr), bei Passiven immer Basic.
  3. Lager ≥ Bedarf × Platinenzahl, lieber Teil mit großem Lager als billigstes.
  4. Kein Lager → pin- und footprintgleiche Alternative suchen, im Schaltplan Wert anpassen, Doku nachziehen,
     User über jeden Tausch informieren.
  5. Spannungsfestigkeit beachten (MLCC auf 5 V mindestens 10 V Nennspannung).
- Danach Schaltplan neu erzeugen, ERC, Netzliste, Platine neu bauen, DRC + Parität (siehe Skill `kicad-pcb`).

## 2. Fertigungsdaten erzeugen

```bash
cd kicad/waffe_elektronik
python3 ../../.claude/skills/jlcpcb-order/tools/jlc_fab.py waffe_elektronik.kicad_pcb fertigung/jlcpcb --boards=5 --check
```

Erzeugt in `fertigung/jlcpcb/`:
- `waffe_elektronik_gerber.zip` – Gerber (Protel-Endungen, Lötstopp vom Silk abgezogen, Zonen neu gefüllt),
  Excellon-Bohrdatei (mm, dezimal, Langlöcher „alternate“, absoluter Ursprung) + Bohrplan
- `waffe_elektronik_bom.csv` – `Comment, Designator, Footprint, LCSC Part #`, gruppiert nach LCSC-Nummer
- `waffe_elektronik_cpl.csv` – `Designator, Mid X, Mid Y, Layer, Rotation` (mm, Top/Bottom, JLC-Rotationskorrektur)
- `--check`: Lager je Teil gegen Bedarf, basic/ext, Anzahl Extended-Teile, Teilekosten

Rotationskorrekturen (`ROTATIONS` in `jlc_fab.py`) stammen aus der Datenbank von matthewlai/JLCKicadTools
(auch in Bouni/kicad-jlcpcb-tools). Neue Gehäuse dort ergänzen.

## 3. Bestellung auf jlcpcb.com

1. „Order now“ → `*_gerber.zip` hochladen.
2. Leiterplatte: **4 Lagen**, 1,6 mm, Maße werden aus Edge.Cuts gelesen (59,6 × 51 mm, Lasche oben links, Aussparung rechts),
   **Impedanzkontrolle mit Stackup JLC04161H-7628** (USB-Paar), Oberfläche ENIG (TQFN/0,5-mm-Raster),
   Via Covering: tented.
3. „PCB Assembly“ an → Economic/Standard, **Top Side**, Menge wählen.
4. BOM und CPL hochladen; nicht platzierte Teile prüfen (es sollen 0 sein). Stecker und SW3/SW4 sind absichtlich
   ohne `LCSC`-Feld (`HAND` in build_clean.py) und fehlen in BOM/CPL: selbst löten, spart Extended-Gebühren.
   Externe Antenne: `*_bom_externe_antenne.csv` + `*_cpl_externe_antenne.csv` hochladen (WROOM-1U, Mitte 3,15 mm
   versetzt; `ALT`/`ALT_SHIFT` in jlc_fab.py).
5. **Platzierungsvorschau Bauteil für Bauteil prüfen**, vor allem Pin 1 / Polarität bei:
   U4 (ESP32-Modul, keine Korrektur in der DB), U5, U6, U14 (WSON-8, Pin 1 oben links), J7 (microSD, Öffnung zur Unterkante), U15/Q3 (SOT-23-6), D4/D5, U1/U3/U12 (SOT-23-5/6), D1–D3, C3 (Tantal),
   J1–J3, BT1/SP1, M1/M2/LED1/LED2/SW1/SW2 (JST), SW3/SW4. Falsche Drehung in der Vorschau korrigieren und
   die Korrektur in `ROTATIONS` nachtragen.
6. Bestellung erst nach Freigabe durch den User abschicken (kostenpflichtig, externe Aktion).

## Stolpersteine

- Teile ohne `LCSC`-Feld werden nicht bestückt und vom Skript gemeldet.
- `fertigung/jlcpcb/` wird bei jedem Lauf überschrieben; nach jeder Platinenänderung neu erzeugen.
- Lagerbestände ändern sich täglich: vor jeder Bestellung `--check` erneut laufen lassen.
- Gerber-Vorschau bei JLC (Gerber Viewer) kurz prüfen: 4 Kupferlagen, Umriss, Bohrungen, Beschriftung oben
  (unten nur die Projekt-URL).
