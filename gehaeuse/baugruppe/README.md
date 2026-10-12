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

| Vorn rechts (Frontkappe, Linsenhülse) | Hinten (OLED am Schaft) |
|---|---|
| <img src="baugruppe_vorn.png" width="280"> | <img src="baugruppe_hinten.png" width="200"> |

Schnitt durch den Schalldämpfer (Linse, IR-LED, Ringlicht als Platzhalter):

<img src="schnitt_schalldaempfer.png" width="640">

## Teile

| Teil | Datei | Lage |
|---|---|---|
| Gehäuse links / rechts | `mp5_umbau/obj_1_3_links.stl`, `obj_3_6_rechts.stl` | Bezug (Teilungsebene Z = 0) |
| Zwischenring | `mp5_umbau/obj_5_5_zwischenring.stl` | vor dem Gehäuse, Profil und Stegkanal fluchtend |
| Handschutz + Schalldämpfer | `mp5_umbau/obj_10_2_handschutz.stl` | vor dem Zwischenring |
| Linsenhülse, Frontkappe | `mp5_umbau/linsenhuelse.stl`, `frontkappe.stl` | vorn im bzw. auf dem Schalldämpfer |
| Steg vorn | `obj_8_8.stl` (Rundstab Ø 10 × 100) | Gehäuse 34 mm, Zwischenring 21 mm, Handschutz 45 mm (bis in die Kegelspitze des Kanals) |
| Korn | `obj_7_1.stl` | Ring auf dem Rohr vorn am Handschutz, Steg im Schlitz |
| Spannhebel | `obj_11_12.stl` (Stift Ø 2), `obj_9_10.stl` (Knauf) | Stift im schrägen Loch der linken Mulde, Knauf außen darauf |
| Schaft links / rechts | `mp5_umbau/obj_4_7_schaft_links.stl`, `obj_2_4_schaft_rechts.stl` | an der Gehäuserückseite, Stegkanal fluchtend |
| OLED-Rahmen | `mp5_umbau/oled_rahmen.stl` | in der Stufe des OLED-Sockels am Schaft |
| Steg hinten | `mp5_umbau/steg_schaft_77mm.stl` | ab Anschlag Y = 164 bis in den Schaft |
| Magazin, Unterteil | `mp5_umbau/obj_6_9_magazin.stl`, `magazinboden.stl` | voll im Magazinschacht, 12° geneigt |
| Abzug | `mp5_umbau/abzug.stl` | auf der Achse X = 136 / Y = 129, Ruhelage |
| Platine | KiCad-Export (`kicad-cli pcb export glb`) | Tasche in der rechten Hälfte |

`obj_12_11.stl` (Sechskantstift 6 × 17,6 mm) ist nicht enthalten: keine passende Aufnahme gefunden.

Überschneidungen in der Baugruppe (Prüfung mit manifold3d):
- Magazin ↔ Gehäuse 2 × 156 mm³: Mittelrippe hinten im Schacht (Z ±3,6) im Magazinrücken
- Korn ↔ Handschutz 276 mm³: Steg (9 × 12 mm) im Schlitz (6,7 × 8,1 mm), Klemmsitz
- Stege, Schaft, Platine, Spannhebel, Abzug, Linsenhülse, Frontkappe, Magazinunterteil: ≤ 4 mm³

## Erzeugen

```sh
.venv/bin/pip install numpy trimesh manifold3d lxml networkx scipy shapely
.venv/bin/python gehaeuse/scripts/umbau.py       # Druckteile nach mp5_umbau/
.venv/bin/python gehaeuse/scripts/baugruppe.py   # GLB/3MF
```
