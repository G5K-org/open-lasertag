# OrcaSlicer-Projekte Gießvariante (PETG)

Gegenstücke zu [`bambu/mp5_guss_p2s.3mf`](../bambu/README.md) für OrcaSlicer 2.4, Düse 0,4. Gleiche Teile aus
[`mp5_giessfuellung/`](../mp5_giessfuellung/README.md), gleiche Einstellungen, an den Drucker angepasst.
In OrcaSlicer öffnen, Platte wählen, slicen, G-Code auf die SD-Karte.

| Datei | Drucker | Filament | Druckzeit | Filament |
|---|---|---|---|---|
| `mp5_guss_i3megas.3mf` | Anycubic i3 Mega S (Bett 210 × 210) | Anycubic Generic PETG | **79,3 h** | 655 g |
| `mp5_guss_x2.3mf` | Artillery Sidewinder X2 (Bett 300 × 300) | Artillery Generic PETG | **63,6 h** | 614 g |

Zeiten aus Orca 2.4.2 (`druckzeiten.json`). Länger als beim P2S (24,8 h), weil die Systemprofile beider Drucker
mit 30–60 mm/s drucken (beim X2 schneller eingestellt, siehe unten).

## Anycubic i3 Mega S

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

- **Bett 210 × 210 mm:** Die Gehäusehälften (194 × 198 mm) passen knapp. Der vordere Handschutz (206 mm lang)
  liegt um 45° gedreht, die Schafthälften liegen auf je einer eigenen Platte.
- **Gehäusehälften 4,5 mm nach hinten verschoben:** Der Tree-Support an der Vorderkante läge sonst auf der
  Reinigungslinie des Startcodes (Y 1–2). Das Teil reicht jetzt bis Y 208,3.
- **Kein Brim, kein Skirt:** Beide ragten bei den Gehäusehälften über das Bett. Die Reinigungslinie im Startcode
  bleibt.
- Grundlage ist das Systemprofil **0.20mm Standard @Anycubic i3MegaS**.
- Filament **Anycubic Generic PETG**: 255 °C Düse, 80 °C Bett.

Auf Platte 5 meldet Orca „Potentially lost branch“ (Tree-Support), der G-Code entsteht trotzdem. Dort in der
Vorschau den Support unter dem Schaft ansehen.

## Artillery Sidewinder X2

| Platte | Teile | Zeit · Filament |
|---|---|---|
| 1 | Gehäuse links, Handschutz vorn links | 19,2 h · 182 g |
| 2 | Gehäuse rechts, Handschutz vorn rechts | 18,9 h · 181 g |
| 3 | Schaft links + rechts, Handschutz hinten, Zwischenring, Magazin, Magazin-Unterteil, Kleinteile | 25,6 h · 250 g |

- **Bett 300 × 300 mm, alles auf 3 Platten:** Gehäusehälfte und vorderer Handschutz liegen nebeneinander, der Rest
  auf Platte 3. Jedes Teil kommt in die erste Reihe, in der noch Platz ist. Nichts ist gedreht oder verschoben, und
  die Teile halten mindestens 10 mm Abstand zum Rand.
- **Kein Brim:** Der Auto-Brim des Profils wird um die Gehäusehälften 17 mm breit und lief neben dem Handschutz
  über das Bett. Der Skirt (3 Runden) bleibt. Die Reinigungslinie des Startcodes (Y 0,2–0,5, X 10–100) bleibt frei.
- Platte 3 läuft über einen Tag. Geht ein Teil schief, ist die ganze Platte verloren. Wer das vermeiden will,
  löscht in Orca Teile von der Platte und druckt sie getrennt.
- Grundlage ist das Systemprofil **0.20mm Standard @Artillery X2**. Startcode mit G29 (Bettvermessung vor jedem
  Druck) aus dem Druckerprofil.
- Filament **Artillery Generic PETG**, gegen Stringing angepasst (mit dem Profil zog es starke Fäden):
  240 °C Düse (erste Schicht 245 °C, Profil 255 °C), Retract 1,6 mm mit 40 mm/s (Profil 1 mm, 35 mm/s),
  Wiedereinschub 30 mm/s, Wipe 2 mm mit 70 % Retract davor, Z-Hop 0,2 mm (Profil 0,4 mm). 80 °C Bett,
  Flussrate 0,95.
- **Avoid crossing walls** an: Leerfahrten bleiben innerhalb der Wände, Fäden landen im Infill statt quer über
  Kammern und Außenflächen. Kostet 4 h über alle Platten.
- **Schneller als das Profil** (das druckt mit 500 mm/s² und 30–60 mm/s): Beschleunigung 1000 mm/s² (Limit im
  Druckerprofil), Innenwand 80, Infill 100, inneres Solid-Infill 80, Oberseite 45, Support 70, Gap-Fill 40,
  Leerfahrt 200 mm/s. Orca begrenzt auf die 10 mm³/s des Filaments (bei 0,5 × 0,2 mm etwa 100 mm/s). Außenwand
  bleibt 60 mm/s mit 700 mm/s².
- Fädelt es weiter: zuerst Temperatur in 5-°C-Schritten senken (bis 230 °C), dann Retract in 0,2-mm-Schritten
  erhöhen (Direktantrieb, nicht über 2,5 mm). Feuchtes PETG fädelt unabhängig davon, dann trocknen (65 °C, 4–6 h).

## Für beide

- Geschwindigkeit, Beschleunigung und Retract kommen beim Mega S unverändert aus dem Systemprofil, *Adaptive layer height*
  ist aus (Kammerdecken brauchen feste 0,2 mm).
- *Ensure vertical shell thickness* „Partial“ heißt in Orca **Critical only**.
- Filament vor dem Druck an die eigene Rolle anpassen.

Wände, Infill, Schalen, Support-Blocker über den Kammern, Modifier am Zapfen (60 %) und die massiven Kleinteile
sind wie im [Bambu-README](../bambu/README.md#einstellungen).

Geprüft im G-Code: Alle Bahnen liegen im Bett. In den Kammern der Gehäusehälfte steht kein Support.

## Neu erzeugen

```
python gehaeuse/scripts/orca_projekte.py          # beide Drucker
python gehaeuse/scripts/orca_projekte.py x2       # nur Sidewinder X2 (i3megas für den Mega S)
```

Braucht numpy, trimesh mit scipy und shapely (`trimesh[easy]`), manifold3d; orca-slicer im PATH. Andere
Programmdatei mit `ORCA_SLICER=…`, anderer Profilordner mit `ORCA_PROFILES=…` (sonst `~/.config/OrcaSlicer/system`,
und wenn der Hersteller dort fehlt, die mitgelieferten Profile neben orca-slicer). Das Skript slict zur Kontrolle
alle Platten. Orca braucht dabei mehrere GB Speicher.
