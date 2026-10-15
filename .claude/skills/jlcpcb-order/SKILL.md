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
- `*_externe_antenne.csv` – BOM/CPL mit ESP32-S3-WROOM-1U statt WROOM-1 (gleicher Footprint)
- `*_komplett.csv`, `*_komplett_externe_antenne.csv` – zusätzlich alle Teile mit Feld `LCSC Hand` (Stecker, SW3/SW4)
- `*_flash.csv` (jede Variante) – zusätzlich die Teile mit Feld `LCSC Option` (`OPTION` in build_clean.py: SPI-NAND
  U14 mit C25/R27), Standard ist ohne
- `--check`: Lager je Teil gegen Bedarf, basic/ext, Anzahl Extended-Teile, Teilekosten (für die Komplett-Variante
  mit Flash, also alle Teile); Anzahl Platinen mit `--boards=N`

Rotationskorrekturen (`ROTATIONS` in `jlc_fab.py`) stammen aus der Datenbank von matthewlai/JLCKicadTools
(auch in Bouni/kicad-jlcpcb-tools). Neue Gehäuse dort ergänzen.

## 3. Bestellung auf jlcpcb.com

1. „Order now“ → `*_gerber.zip` hochladen.
2. Leiterplatte: **4 Lagen**, 1,6 mm, Maße werden aus Edge.Cuts gelesen (59,6 × 55 mm, Lasche oben links, Aussparung rechts),
   **Impedanzkontrolle mit Stackup JLC04161H-7628** (USB-Paar), Oberfläche ENIG (TQFN/0,5-mm-Raster), **Lötstopplack White** (Druck dann automatisch schwarz),
   Via Covering: tented.
3. „PCB Assembly“ an → Economic/Standard, **Top Side**, Menge wählen.
4. BOM und CPL hochladen; nicht platzierte Teile prüfen (es sollen 0 sein). Stecker und SW3/SW4 haben das Feld
   `LCSC Hand` statt `LCSC` (`HAND` in build_clean.py) und fehlen in der Standard-BOM/CPL: selbst löten, spart
   8 Extended-Gebühren. Von JLC mitbestücken: `*_bom_komplett.csv` + `*_cpl_komplett.csv`.
   Externe Antenne: `*_bom_externe_antenne.csv` + `*_cpl_externe_antenne.csv` hochladen (WROOM-1U, Mitte 3,15 mm
   versetzt; `ALT`/`ALT_SHIFT` in jlc_fab.py).
5. **Platzierungsvorschau Bauteil für Bauteil prüfen**, vor allem Pin 1 / Polarität bei:
   U4 (ESP32-Modul, keine Korrektur in der DB), U6, U14 (WSON-8, Pin 1 oben links), J7 (microSD, Öffnung zur Unterkante), U15/Q3/U16 (SOT-23-6), D4, U1 (IP5306, HSOP-8, Korrektur 270° wie SOIC, ungeprüft), U12 (SOT-23-6), D1,
   C3 (Tantal), Q1/Q2/Q4 (SOT-23), D6 (SOT-323, Korrektur −90° wie SOT-23, ungeprüft), J1–J3, BT1/SP1, M1 (JST), J2/J4/J5/J6/J8 (JST-SH, Korrektur 180° ungeprüft), SW3/SW4. Falsche Drehung in der Vorschau korrigieren und
   die Korrektur in `ROTATIONS` nachtragen.
6. Bestellung erst nach Freigabe durch den User abschicken (kostenpflichtig, externe Aktion).

## Stolpersteine

- Teile ohne `LCSC`-Feld werden nicht bestückt und vom Skript gemeldet.
- `fertigung/jlcpcb/` wird bei jedem Lauf überschrieben; nach jeder Platinenänderung neu erzeugen.
- Lagerbestände ändern sich täglich: vor jeder Bestellung `--check` erneut laufen lassen.
- Gerber-Vorschau bei JLC (Gerber Viewer) kurz prüfen: 4 Kupferlagen, Umriss, Bohrungen, Beschriftung oben
  (unten nur die Projekt-URL).
