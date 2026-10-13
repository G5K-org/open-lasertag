# MP5-Baugruppe

Alle Teile der Waffe an ihrem Platz in einer Datei, erzeugt mit
[`../scripts/baugruppe.py`](../scripts/baugruppe.py) aus den Teilen von
[`../mp5_umbau/`](../mp5_umbau/) (vorher `umbau.py` laufen lassen):

- `mp5_baugruppe.glb` – farbig, jedes Teil ein eigener Knoten; Meter, y oben, Mündung in +x
  (Blender, Windows 3D-Viewer, gltf-viewer.donmccurdy.com)
- `mp5_baugruppe.3mf` – dieselben Teile in mm, Gun-Rahmen (für CAD/Slicer)

| Links | Linke Hälfte, linker Schaft und Magazin ausgeblendet | Schräg vorn links |
|---|---|---|
| <img src="baugruppe_links.png" width="280"> | <img src="baugruppe_offen.png" width="280"> | <img src="baugruppe_schraeg.png" width="280"> |

| Rechts (Schraubensenkungen an Gehäuse und Handschutz, Schalllöcher) | Vorn rechts (Frontkappe, Linsenhülse) | Hinten (OLED am Schaft) |
|---|---|---|
| <img src="baugruppe_rechts.png" width="280"> | <img src="baugruppe_vorn.png" width="280"> | <img src="baugruppe_hinten.png" width="200"> |

Explosionszeichnung (alle Druckteile und die Platine, Namen wie in [`../mp5_umbau/`](../mp5_umbau/README.md#dateien);
Kaufteile wie Schrauben, Akku und Lautsprecher sind nicht dargestellt):

<img src="explosion_links.png" width="900">

<img src="explosion_rechts.png" width="900">

Schnitt durch den Schalldämpfer (Linse, IR-LED, Ringlicht als Platzhalter):

<img src="schnitt_schalldaempfer.png" width="640">

Schnitt durch den Handschutz (rechte Hälfte): Lautsprecher (rot, Platzhalter) strahlt nach hinten in die
Schallkammer mit Löchern, davor die geschlossene Basskammer, oben die Kabelnut und das Korn, rechts (blau)
der Zapfen des hinteren Handschutzes:

<img src="schnitt_lautsprecher.png" width="640">

Schnitt durch Gehäuse und Schaft (rechte Hälfte): GX16-Buchse für die Weste (gold, Platzhalter) mit Mutter in der
Sechskanttasche und Stecker, Westenschacht schräg nach vorn zur Platine; darüber OLED-Schacht und Steg hinten:

<img src="schnitt_weste.png" width="520">

## Teile

Die Knoten in GLB/3MF tragen die Namen aus [`../mp5_umbau/`](../mp5_umbau/README.md#dateien)
(dort auch Datei und Herkunft im Originalsatz).

| Teil | Lage |
|---|---|
| Gehäuse links / rechts | Bezug (Teilungsebene Z = 0), 6 × M3 verschraubt |
| Zwischenring | vor dem Gehäuse, Profil und Stegkanal fluchtend |
| Handschutz hinten, Handschutz vorn mit Schalldämpfer links / rechts | vor dem Zwischenring, geteilt bei Y = −32; vorderer Teil links/rechts geteilt (Z = 0), 5 × M3 verschraubt, umschließt den Zapfen des hinteren Teils (4 × M3) |
| Linsenhülse, Frontkappe | vorn im bzw. auf dem Schalldämpfer |
| TSOP-Einsatz | vorn an der Rundung unter dem Korn, über dem Schalldämpfer |
| Steg vorn (Rundstab 96 mm) | Gehäuse 34 mm, Zwischenring 21 mm, Handschutz hinten 41 mm (bis vor den Zapfen) |
| Korn | Ring auf dem Rohr vorn am Handschutz, Steg im Schlitz |
| Spannhebel Stift, Spannhebel Knauf | Stift im schrägen Loch der linken Mulde, Knauf außen darauf |
| Schaft links / rechts, OLED-Rahmen | an der Gehäuserückseite; Rahmen in der Stufe des OLED-Sockels; GX16-Buchse unten vorn (X = 114,4, Y = 232) |
| Steg hinten (Rundstab 77 mm) | ab Anschlag Y = 164 bis in den Schaft |
| Magazin, Magazin Unterteil | voll im Magazinschacht, 12° geneigt |
| Abzug | auf der Achse X = 136 / Y = 129, Ruhelage |
| Platine | KiCad-Export (`kicad-cli pcb export glb`), Tasche in der rechten Hälfte |

`obj_12_11` (Sechskantstift 6 × 17,6 mm) ist nicht enthalten: keine passende Aufnahme gefunden.

Überschneidungen in der Baugruppe (Prüfung mit manifold3d):
- Magazin ↔ Gehäuse 2 × 156 mm³: Mittelrippe hinten im Schacht (Z ±3,6) im Magazinrücken
- Korn ↔ Handschutz vorn links / rechts je ca. 138 mm³: Steg (9 × 12 mm) im Schlitz (6,7 × 8,1 mm), Klemmsitz
- Stege, Schaft, Platine, Spannhebel, Abzug, Linsenhülse, Frontkappe, Magazinunterteil, TSOP-Einsatz,
  OLED-Rahmen: ≤ 4 mm³

## Erzeugen

```sh
.venv/bin/pip install numpy trimesh manifold3d lxml networkx scipy shapely matplotlib
.venv/bin/python gehaeuse/scripts/umbau.py       # Druckteile nach mp5_umbau/
.venv/bin/python gehaeuse/scripts/baugruppe.py   # GLB/3MF
.venv/bin/python gehaeuse/scripts/kabelwege.py   # alle Kabelwege prüfen
.venv/bin/python gehaeuse/scripts/explosion.py gehaeuse/baugruppe/explosion_links.png -30 -22
.venv/bin/python gehaeuse/scripts/explosion.py gehaeuse/baugruppe/explosion_rechts.png 150 -22
```
