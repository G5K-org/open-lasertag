# MP5-Gehäuse mit Gießfüllung – Modifier für den Slicer

Variante B aus [GIESSFUELLUNG.md](../mp5_umbau/GIESSFUELLUNG.md): Die Teile selbst bleiben die aus
[`mp5_umbau/`](../mp5_umbau/). Hier liegen nur **Modifier-Volumen**, die im Slicer die Gießkammern erzeugen.

- **Prototyp ohne Füllung:** Teile aus `mp5_umbau/` wie gewohnt drucken (6 Wände, 50 % Gyroid), diesen Ordner
  ignorieren.
- **Gießvariante:** Teil + passende Modifier aus diesem Ordner zusammen laden (siehe unten).

Erzeugt mit `gehaeuse/scripts/giessfuellung.py` aus den STLs in `mp5_umbau/`. Nach jedem Lauf von `umbau.py`
das Skript neu laufen lassen (`python giessfuellung.py bilder` erzeugt nur die Bilder neu).

<img src="bilder/uebersicht.png" alt="Gießkammern aller gießbaren Teile an ihrem Platz in der Waffe, Innenseiten der linken und rechten Hälften" width="900">

## Dateien

| Teil | Modifier | Kammer cm³ | Füllung g |
|---|---|---|---|
| `gehaeuse_links` | `__quarzharz` / `__hohl` (Antenne) | 66,9 / 3,7 | 127 / – |
| `gehaeuse_rechts` | `__quarzharz` / `__hohl` (Antenne) | 66,0 / 6,8 | 125 / – |
| `handschutz_hinten` | `__schaum` | 43,4 | 4 |
| `handschutz_vorn_links` | `__schaum` | 46,1 | 5 |
| `handschutz_vorn_rechts` | `__schaum` | 42,8 | 4 |
| `schaft_links` | `__quarzharz` (Ballast) | 52,0 | 99 |
| `schaft_rechts` | `__quarzharz` (Ballast) | 52,0 | 99 |

Zusammen ca. **237 cm³ Quarzharz (ca. 450 g)** und **132 cm³ Schaum (ca. 15 g)**. Werte in `volumen.json`
(Quarzharz 1,9 g/cm³, Schaum 0,1 g/cm³).

Nicht gefüllt (normal drucken): Zwischenring, Magazin, Magazin-Unterteil und alle Kleinteile.

## Wie die Kammern entstehen

- Kammer = alles im Teil mit **mindestens 2 mm Abstand zu jeder Oberfläche**. Dadurch bleiben gedruckt:
  Außenhaut, Auflagerand an der Teilungsfläche, Röhren um Schächte und Bohrungen, Dome um Einschmelzmuttern
  und Schraubensenkungen sowie Dämme an offenen Kabelnuten.
- **Offen nur zur Druckbett-Seite** (bei den Hälften die Teilungsfläche, beim hinteren Handschutz die
  Rückseite mit der Nut). Von dort ist jede Kammer über Flanken mit **höchstens 45° Überhang** erreichbar.
  Beim Gießen liegt die offene Seite oben, und die Luft steigt an solchen Decken von selbst heraus. Gedruckt
  sind 45° ohne Stütze möglich. Bereiche hinter steileren Überhängen bleiben gedruckt.
- **Gehäuse komplett Quarzharz**: Griff und Krafteinleitung (Einschmelzmuttern, Zuganker, Stege) ohne
  Trennwände dazwischen.
- **Hohl (Antenne):** 15 mm um den Antennenbereich des WROOM-1, mit 1,5 mm Trennwand zum Quarzharz. Wird
  geschlossen gedruckt und nicht gefüllt.
- Kammern unter 0,5 cm³ und dünne Grate (< ca. 1,6 mm) bleiben gedruckt. Quarzsand kommt dort ohnehin nicht hinein.
- Der **Zapfen des hinteren Handschutzes** (Einschmelzmuttern, Zuganker-Muttern) liegt beim Druck oben und
  ist von der offenen Seite aus nicht erreichbar. Er bleibt gedruckt. Im Slicer dort einen Modifier mit
  hohem Infill (≥ 60 %) setzen.
- Die Modifier reichen 0,8 mm unter das Bett, damit die Kammer ab der ersten Schicht sicher offen ist.

## Im Slicer (PrusaSlicer / OrcaSlicer)

1. Teil aus `mp5_umbau/` **und** seine Modifier aus diesem Ordner **gemeinsam** importieren (alle Dateien
   auf einmal auswählen). Die Frage „als ein Objekt mit mehreren Teilen laden?“ mit **Ja** beantworten,
   so bleiben die Lagen zueinander erhalten.
2. Die Modifier-Teile per Rechtsklick → *Typ ändern* auf **Modifier** stellen.
3. Einstellungen:

| | Teil (außerhalb der Kammern) | `__quarzharz`, `__schaum` | `__hohl` |
|---|---|---|---|
| Wände | 2 | – (wie Teil) | – |
| Infill | 25–40 % Gyroid | **Lightning** | Lightning |
| Bodenschichten | 4 | **0** (Kammer offen) | 4 (geschlossen) |
| Deckschichten | 5 | 5 | 5 |

Düse 0,4, Schichthöhe 0,16–0,20 mm, sonst Profil aus GIESSFUELLUNG.md, Abschnitt 4.

4. In der Vorschau prüfen: Die Kammern sind von der ersten Schicht an offen (nur Lightning-Stränge), und die
   Decke über den Kammern hängt nicht durch. Tut sie das doch, im Modifier Gyroid 10 % statt Lightning
   nehmen (wird ebenfalls eingegossen).

## Gießen

Ablauf in GIESSFUELLUNG.md, Abschnitt 6. Teil mit der offenen Seite nach oben legen (wie links in den
Bildern). Zuerst die Quarzharz-Zonen füllen, nach dem Aushärten den Schaum. Jeweils nur bis 0,5–1 mm unter
die Teilungsfläche bzw. Auflagefläche füllen.

## Vorschau je Teil

Links die Gießseite (Teil umgedreht, Kammern offen nach oben), rechts die Durchsicht mit den Kammern im Teil.

### Gehäuse links
<img src="bilder/gehaeuse_links.png" alt="Gehäuse links: Quarzharz-Kammern und Antennenbereich" width="900">

### Gehäuse rechts
<img src="bilder/gehaeuse_rechts.png" alt="Gehäuse rechts: Quarzharz-Kammern und Antennenbereich" width="900">

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
