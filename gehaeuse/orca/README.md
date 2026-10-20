# OrcaSlicer-Projekt Gießvariante (Anycubic i3 Mega S, PETG)

`mp5_guss_i3megas.3mf` ist das Gegenstück zu [`bambu/mp5_guss_p2s.3mf`](../bambu/README.md) für den
**Anycubic i3 Mega S, Düse 0,4, Anycubic Generic PETG** in OrcaSlicer 2.4. Gleiche Teile aus
[`mp5_giessfuellung/`](../mp5_giessfuellung/README.md), gleiche Einstellungen, an den Drucker angepasst.
In OrcaSlicer öffnen, Platte wählen, slicen, G-Code auf die SD-Karte.

**Druckzeit gesamt 79,3 h, 655 g** (Orca 2.4.2, `druckzeiten.json`). Länger als beim P2S (24,8 h), weil das
Systemprofil des Mega S mit 40–60 mm/s druckt.

| Platte | Teile | Zeit · Filament |
|---|---|---|
| 1 | Gehäuse links | 15,5 h · 130 g |
| 2 | Gehäuse rechts | 14,4 h · 125 g |
| 3 | Handschutz vorn links (45° gedreht) | 8,5 h · 65 g |
| 4 | Handschutz vorn rechts (45° gedreht) | 8,8 h · 67 g |
| 5 | Schaft links | 5,4 h · 45 g |
| 6 | Schaft rechts | 5,4 h · 45 g |
| 7 | Handschutz hinten, Zwischenring, Magazin, Magazin-Unterteil | 19,3 h · 163 g |
| 8 | Kleinteile | 2,0 h · 16 g |

## Unterschiede zum Bambu-Projekt

- **Bett 210 × 210 mm:** Die Gehäusehälften (194 × 198 mm) passen knapp. Der vordere Handschutz (206 mm lang)
  liegt um 45° gedreht, die Schafthälften liegen auf je einer eigenen Platte.
- **Gehäusehälften 4,5 mm nach hinten verschoben:** Der Tree-Support an der Vorderkante läge sonst auf der
  Reinigungslinie des Startcodes (Y 1–2). Das Teil reicht jetzt bis Y 208,3.
- **Kein Brim, kein Skirt:** Beide ragten bei den Gehäusehälften über das Bett. Die Reinigungslinie im Startcode
  bleibt.
- Grundlage ist das Systemprofil **0.20mm Standard @Anycubic i3MegaS**. Geschwindigkeit, Beschleunigung und
  Retract kommen unverändert aus dem Profil, *Adaptive layer height* ist aus.
- *Ensure vertical shell thickness* „Partial“ heißt in Orca **Critical only**.
- Filament **Anycubic Generic PETG**: 255 °C Düse, 80 °C Bett. Vor dem Druck an die eigene Rolle anpassen.

Wände, Infill, Schalen, Support-Blocker über den Kammern, Modifier am Zapfen (60 %) und die massiven Kleinteile
sind wie im [Bambu-README](../bambu/README.md#einstellungen).

Geprüft im G-Code: Alle Bahnen liegen im Bett. In den Kammern der Gehäusehälfte steht kein Support. Auf
Platte 5 meldet Orca „Potentially lost branch“ (Tree-Support), der G-Code entsteht trotzdem. Dort in der
Vorschau den Support unter dem Schaft ansehen.

## Neu erzeugen

```
python gehaeuse/scripts/orca_projekte.py        # braucht numpy, trimesh, manifold3d; orca-slicer im PATH
```

Andere Programmdatei mit `ORCA_SLICER=…`, anderer Profilordner mit `ORCA_PROFILES=…` (Standard
`~/.config/OrcaSlicer/system`). Das Skript slict zur Kontrolle alle Platten. Orca braucht dabei mehrere GB
Speicher.
