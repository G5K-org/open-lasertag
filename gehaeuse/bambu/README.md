# Bambu-Studio-Projekte (P2S, PETG HF)

Fertige Projekte für **Bambu Lab P2S, Düse 0,4, Bambu PETG HF, Textured PEI Plate**. Einfach in Bambu Studio
öffnen, Platte wählen, slicen und drucken.

| Datei | Inhalt | Druckzeit | Filament |
|---|---|---|---|
| `mp5_massiv_p2s.3mf` | Prototyp **ohne Füllung**: 6 Wände, 50 % Gyroid, Zwischenring 100 % | **41,2 h** | 933 g |
| `mp5_guss_p2s.3mf` | **Gießvariante**: Teile mit ausgesparten Kammern aus [`mp5_giessfuellung/`](../mp5_giessfuellung/README.md) | **24,8 h** | 560 g |

Zeiten und Gewichte stammen aus dem Slicen mit Bambu Studio 02.08.03 (`druckzeiten.json`).

## Platten

| Platte | Teile | massiv | Guss |
|---|---|---|---|
| 1 | Gehäuse links | 7,8 h · 189 g | 4,9 h · 111 g |
| 2 | Gehäuse rechts | 7,8 h · 191 g | 4,7 h · 110 g |
| 3 | Handschutz vorn links | 4,9 h · 107 g | 2,6 h · 55 g |
| 4 | Handschutz vorn rechts | 5,0 h · 107 g | 2,8 h · 57 g |
| 5 | Schaft links + rechts | 6,6 h · 165 g | 3,9 h · 83 g |
| 6 | Handschutz hinten, Zwischenring, Magazin, Magazin-Unterteil | 8,3 h · 161 g | 5,4 h · 130 g |
| 7 | Kleinteile (Abzug, Nachladehebel, Frontkappe, Linsenhülse, TSOP-Einsatz, OLED-Rahmen, Korn, Spannhebel) | 0,8 h · 14 g | 0,6 h · 14 g |

Die Stege werden nicht gedruckt (Stahl-Rundstab Ø 10).

## Einstellungen

Grundlage ist das Systemprofil **0.20mm Standard @BBL P2S**, geändert:

| | massiv | Guss |
|---|---|---|
| Wall loops | 6 | 2 |
| Sparse infill | 50 % Gyroid | 15 % Grid |
| Bottom shell layers / thickness | Profil | 3 / 0 |
| Top shell layers | Profil | 5 |
| Line width außen / innen / Infill | Profil | 0,42 / 0,5 / 0,5 |
| Ensure vertical shell thickness | Profil | Partial |
| Support | tree(auto) | tree(auto), in den Kammern blockiert |

Dazu in beiden Projekten Seam *aligned*, kein Ironing. In der Gießvariante zusätzlich:
- **Support-Blocker über den Kammern** (Originalteil minus Gussteil, beim Bauen erzeugt). Bambu Studio würde
  die Kammerdecken sonst stützen.
- **Hinterer Handschutz:** ein Quader-Modifier über dem Zapfen mit 60 % Infill (Einschmelzmuttern, Muttern der Zuganker).
- **Kleinteile, Zwischenring, Magazin:** wie im massiven Satz (6 Wände, 50 %, Zwischenring 100 %).

Geprüft im G-Code der Schaft-Platte: In den Kammern liegt kein Material, sie sind ab der ersten Schicht offen.

## Anderer Drucker

Im Projekt oben links den Drucker wechseln (X1C, P1S usw.). Bambu Studio übernimmt die Einstellungen der Objekte
und Blocker. Danach Filament und Prozess prüfen. Oder die Projekte neu erzeugen: In
`gehaeuse/scripts/bambu_projekte.py` die Namen `MACHINE`, `PROCESS` und `FILAMENT` anpassen.

## Neu erzeugen

Nach Änderungen an `umbau.py` bzw. `giessfuellung.py`:

```
./BambuStudio_*.AppImage --appimage-extract      # einmalig, ergibt squashfs-root/
BAMBU_STUDIO=$PWD/squashfs-root/AppRun python gehaeuse/scripts/bambu_projekte.py
```

Das Skript baut beide Projekte über die Kommandozeile von Bambu Studio, slict sie zur Kontrolle und schreibt
`druckzeiten.json`.
