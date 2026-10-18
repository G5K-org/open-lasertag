# MP5-Gehäuse mit Gießfüllung – fertige Teile mit Gießkammern

Gießvariante aus [GIESSFUELLUNG.md](../mp5_umbau/GIESSFUELLUNG.md): Hier liegen die tragenden Teile **fertig zum
Druck**, die Gießkammern sind schon ausgespart. Kein Modifier, kein Abziehen im Slicer: STL laden, slicen, drucken.

- **Prototyp ohne Füllung:** Teile aus [`mp5_umbau/`](../mp5_umbau/) wie gewohnt drucken (6 Wände, 50 % Gyroid),
  diesen Ordner ignorieren.
- **Gießvariante:** die Teile unten aus diesem Ordner drucken, alle übrigen aus `mp5_umbau/`.

Erzeugt mit `gehaeuse/scripts/giessfuellung.py` aus den STLs in `mp5_umbau/` (auch Vorschaubilder und
`volumen.json`). Nach jedem Lauf von `umbau.py` das Skript neu laufen lassen.

<img src="bilder/uebersicht.png" alt="Gießkammern aller gießbaren Teile an ihrem Platz in der Waffe, Innenseiten der linken und rechten Hälften" width="900">

## Dateien

| Teil | Füllung | Kammer cm³ | Füllung g | Druck cm³ (massiv) |
|---|---|---|---|---|
| `gehaeuse_links.stl` | Quarzharz | 63,6 | 121 | 134,2 (197,6) |
| `gehaeuse_rechts.stl` | Quarzharz | 63,0 | 120 | 142,4 (205,1) |
| `handschutz_hinten.stl` | Schaum | 38,8 | 4 | 38,6 (77,4) |
| `handschutz_vorn_links.stl` | Schaum | 46,1 | 5 | 66,4 (112,4) |
| `handschutz_vorn_rechts.stl` | Schaum | 42,8 | 4 | 67,3 (110,0) |
| `schaft_links.stl` | Quarzharz (Ballast) | 51,8 | 98 | 41,2 (92,9) |
| `schaft_rechts.stl` | Quarzharz (Ballast) | 51,9 | 99 | 41,2 (93,0) |

Zusammen ca. **230 cm³ Quarzharz (ca. 440 g)** und **128 cm³ Schaum (ca. 13 g)**. Werte in `volumen.json`
(Quarzharz 1,9 g/cm³, Schaum 0,1 g/cm³).

Nicht gefüllt (normal aus `mp5_umbau/` drucken): Zwischenring, Magazin, Magazin-Unterteil und alle Kleinteile.

## Wie die Kammern entstehen

- Kammer = alles im Teil mit **mindestens 2 mm Abstand zu jeder Oberfläche**. Dadurch bleiben gedruckt:
  Außenhaut, Auflagerand an der Teilungsfläche, Röhren um Schächte und Bohrungen, Dome um Einschmelzmuttern
  und Schraubensenkungen sowie Dämme an offenen Kabelnuten.
- **Offen nur zur Druckbett-Seite** (bei den Hälften die Teilungsfläche, beim hinteren Handschutz die
  Rückseite mit der Nut). Von dort ist jede Kammer über Flanken mit **höchstens 45° Überhang** erreichbar.
  Beim Gießen liegt die offene Seite oben, und die Luft steigt an solchen Decken von selbst heraus. Gedruckt
  sind 45° ohne Stütze möglich. Bereiche hinter steileren Überhängen bleiben gedruckt.
- **Kammerdecke höchstens 10 mm freie Brücke.** Unter breiteren Decken bleiben gedruckte Pfeiler stehen, die
  bis zum Bett reichen. Damit hängt nichts weiter als 10 mm frei.
- **Gehäuse komplett Quarzharz**: Griff und Krafteinleitung (Einschmelzmuttern, Zuganker, Stege) ohne
  Trennwände dazwischen.
- **Antenne:** 15 mm um den Antennenbereich des WROOM-1 bekommt keine Kammer (1,5 mm Abstand zum Quarzharz).
  Der Bereich wird ganz normal mit Infill gedruckt.
- Kammern unter 0,5 cm³ und dünne Grate (< ca. 1,6 mm) bleiben gedruckt. Quarzsand kommt dort ohnehin nicht hinein.
- Der **Zapfen des hinteren Handschutzes** (Einschmelzmuttern, Zuganker-Muttern) liegt beim Druck oben und
  ist von der offenen Seite aus nicht erreichbar. Er bleibt gedruckt. Im Slicer dort einen Modifier mit
  hohem Infill (≥ 60 %) setzen.
- Die Kammern sind ab der ersten Schicht offen (bis unter das Bett abgezogen).

## Bambu Studio (X1, P1, P2, A1)

**Fertige Projekte für den P2S** (alle Teile und Einstellungen schon drin):
[`gehaeuse/bambu/`](../bambu/README.md). Die Schritte unten braucht man nur für einen anderen Drucker oder
eigene Änderungen.

Gilt genauso für OrcaSlicer. Die Einstellungsnamen stehen hier wie in der englischen Oberfläche, in Klammern
der Reiter. Bauraum 256 × 256 mm: Alle Teile passen, auf dem **A1 mini** (180 mm) passen Gehäusehälften und
vorderer Handschutz nicht.

### 1. Laden

1. *Datei → Importieren → 3D/STEP/3MF importieren* (Strg+I), das Teil aus diesem Ordner wählen.
2. Lage nicht drehen: Die Hälften liegen auf der Teilungsfläche, der hintere Handschutz auf der Seite mit der
   Nut. Die offenen Kammern zeigen zum Bett.

### 2. Prozess

Basis: Systemprofil **0.20mm Standard @BBL** für deinen Drucker, Filament **Bambu PETG HF** (oder PETG Basic)
bzw. ASA, **Textured PEI Plate**.

| Einstellung | Wert |
|---|---|
| Layer height (*Quality*) | 0,20 mm. Für Handschutz und Schaft optional *Variable layer height* (Symbol rechts, „Adaptive“) |
| Line width: Outer wall / Inner wall / Sparse infill (*Quality*) | 0,42 / 0,50 / 0,50 mm |
| Wall generator (*Quality*) | Arachne |
| Seam position (*Quality*) | Aligned (oder Back) |
| Wall loops (*Strength*) | **2** |
| Top shell layers / Top shell thickness (*Strength*) | 5 / 1,0 mm |
| Bottom shell layers / Bottom shell thickness (*Strength*) | 3 / 0 mm |
| Sparse infill density / pattern (*Strength*) | **15 %** / **Grid** |
| Infill combination (*Strength → Advanced*) | an |
| Ensure vertical shell thickness (*Strength → Advanced*) | **Partial** (sonst massive Füllung an den schrägen Kammerflanken) |
| Ironing (*Quality*) | aus |
| Support (*Support*) | an, Type *tree(auto)* |
| Speed | Systemprofil. Für eine feinere Außenseite *Outer wall* auf 120 mm/s |

- **Support in den Kammern:** Bambu Studio erkennt die Kammerdecken nicht als Brücke und stellt Tree-Support
  hinein (beim Schaft ca. 45 min mehr). Schaden tut er nicht, er wird mit eingegossen. In den fertigen
  Projekten verhindert das ein Support-Blocker über den Kammern. Von Hand: *Support painting* (Taste L), Teil
  von unten ansehen und die Kammerdecken mit *Block* bemalen.
- **Nur beim hinteren Handschutz:** Rechtsklick auf das Objekt → *Add modifier* → *Box*. Den Quader über den
  Zapfen legen (oberste ca. 20 mm des Teils) und darin *Sparse infill density* auf **60 %** setzen. Dort sitzen
  Einschmelzmuttern und Zuganker-Muttern, die Stelle bleibt gedruckt.

### 3. Vorschau prüfen (nach *Slice plate*)

- **Schicht 1–3:** Die Kammern sind offen, rundherum der Rand, um Bohrungen und Schächte geschlossene Ringe.
- **Kammern:** Kein Support in den Kammern (siehe oben).
- Die Druckzeit oben rechts mit dem massiven Druck vergleichen. Beim P2S geslict: Gehäusehälfte 4,9 h
  statt 7,8 h, beide Schafthälften 3,9 h statt 6,6 h, die ganze Waffe 24,8 h statt 41 h.

### 4. Speichern

Das fertige Objekt als Projekt speichern (*Datei → Projekt speichern unter*, `.3mf`). Dann bleiben die
Einstellungen für die nächste Waffe erhalten. Mehrere gleiche Teile auf einer Platte: Objekt kopieren
(Strg+C / Strg+V).

## Gießen

Ablauf in GIESSFUELLUNG.md, Abschnitt 6. Teil mit der offenen Seite nach oben legen (wie links in den
Bildern). Zuerst die Quarzharz-Zonen füllen, nach dem Aushärten den Schaum. Jeweils nur bis 0,5–1 mm unter
die Teilungsfläche bzw. Auflagefläche füllen.

## Vorschau je Teil

Links die Gießseite (Teil umgedreht, Kammern offen nach oben), rechts die Durchsicht mit den Kammern im Teil.
Farbig ist, was gegossen wird.

### Gehäuse links
<img src="bilder/gehaeuse_links.png" alt="Gehäuse links: Quarzharz-Kammern" width="900">

### Gehäuse rechts
<img src="bilder/gehaeuse_rechts.png" alt="Gehäuse rechts: Quarzharz-Kammern" width="900">

### Handschutz hinten
<img src="bilder/handschutz_hinten.png" alt="Handschutz hinten: Schaumkammer, offen zur Rückseite" width="900">

### Handschutz vorn links
<img src="bilder/handschutz_vorn_links.png" alt="Handschutz vorn links: Schaumkammern um Kabelschacht und Lautsprecher" width="900">

### Handschutz vorn rechts
<img src="bilder/handschutz_vorn_rechts.png" alt="Handschutz vorn rechts: Schaumkammern" width="900">

### Schaft links
<img src="bilder/schaft_links.png" alt="Schaft links: Quarzharz-Kammer als Ballast" width="900">

### Schaft rechts
<img src="bilder/schaft_rechts.png" alt="Schaft rechts: Quarzharz-Kammer als Ballast" width="900">
