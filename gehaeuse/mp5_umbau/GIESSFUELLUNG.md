# Gießfüllung für das MP5-Gehäuse – weniger Druckzeit, mehr Festigkeit

Konzept für `gehaeuse/mp5_umbau/`: Statt die tragenden Teile massiv zu drucken
(aktuell **6 Wände, 50 % Gyroid**), druckt man nur noch Außenhaut, Funktionsgeometrie
und Trennwände. Der Rest wird mit **Quarzharz** (2K-PU-Gießharz + trockener Quarzsand)
oder **2K-PU-Hartschaum** ausgegossen.

**Entscheidung:** Weg = **Schale drucken + ausgießen** (Slicer-Modifier, Variante B).
Silikonabformung (Hebel 8) wird nicht umgesetzt. Gründe: Sie spart keine Kosten,
bringt mehr Handarbeit und lohnt sich erst ab ca. 8–10 Waffen.

**Ziele**

- Druckzeit pro Waffe von ~50 h auf ~15–20 h (Schätzung, mit dem Slicer prüfen)
- Griff, Schaft und Verschraubungspunkte fester als heute
- Gewicht und Balance gezielt einstellbar
- Alles bleibt zerlegbar (Platine, Akku, Kabel, Lautsprecher erreichbar)

---

## 1. Grundprinzip: Hälften als offene Gussform

Fast alle tragenden Teile sind an der Teilungsfläche (Z = 0) geteilt. Jede Hälfte wird
im CAD als **Schale mit offenen Gießkammern zur Teilungsfläche hin** konstruiert.

- Die Hälfte liegt beim Gießen flach, die Teilungsfläche zeigt nach oben. Damit gibt es
  keine Einfüll- oder Entlüftungslöcher, und Schaum kann frei aufgehen.
- Ein **gedruckter Rand von 2 mm Breite** bleibt an der gesamten Teilungsfläche stehen.
  Er trägt die Klemmkraft der M3-Verschraubung und hält die Passung maßhaltig.
- Gefüllt wird nur bis **0,5–1 mm unter die Teilungsfläche**. Dann muss nichts
  geschliffen werden, und die Hälften liegen nur auf gedrucktem Kunststoff auf.
- Zwei Wege, die Kammern zu erzeugen:
  - **Variante A – CAD** (Abschnitt 2): Kammern explizit in `umbau.py` abziehen.
    Volle Kontrolle, aber die Kammerdecke (Außenhaut von innen) hängt über und
    braucht Support.
  - **Variante B – Slicer-Modifier (empfohlen, schneller):** siehe Abschnitt 4a.
    Keine CAD-Änderung an den Kammern nötig.

---

## 2. Änderungen in `gehaeuse/scripts/umbau.py`

### 2.1 Gießkammer erzeugen (pro Teil)

```
kammer = innen_offset(teil, -wand)               # Außenhaut bleibt stehen (wand = 2,0 mm)
kammer = kammer ∩ halbraum(z < -0,8)             # 0,8 mm unter der Teilungsfläche enden (Vorzeichen je Hälfte)
kammer = kammer − rand(teilungsflaeche, 2,0)     # 2-mm-Auflagerand an der Teilung bleibt gedruckt
kammer = kammer − Σ sperrzone_i.offset(+wand)    # alle Funktionsbereiche + eigene Wand drum herum
kammer = kammer − antennen_sperrzone             # siehe 2.3
teil_neu = teil − kammer
```

Danach `kammer` getrennt je Füllart in Zonen aufteilen (Quarzharz / Schaum) und die
Grenzen als **Trennwände** (1,2–1,6 mm) im Teil stehen lassen.

Zusätzlich exportieren:
- Volumen jeder Kammer → Gewichtsrechnung (Abschnitt 5)
- Kammern als eigene STL zur Kontrolle in der Baugruppe (`baugruppe.py`)

### 2.2 Sperrzonen (bleiben hohl oder massiv gedruckt, mit eigener Wand)

| Bereich | Teil | Behandlung |
|---|---|---|
| Platinentasche inkl. Steckerzonen, microSD-Tasche (bis 9,5 mm unter Platine) | Gehäuse L/R | hohl, umlaufende Wand |
| Hauptschacht Ø 5, Abzweig Ø 6 zum Magazin | Gehäuse, Zwischenring, Handschutz hinten | als **geschlossene Röhre**, Wand ≥ 1,2 mm |
| Motorschacht, VIB-Zone, Motorraum | Gehäuse L/R | hohl |
| Kanal zum Abzugsschalter, Schaltertasche, Abzugsachse, Federbohrung | Gehäuse L/R | hohl |
| Nachladehebel: Tasche, Lagerbund, Stiftbahnen, Kanal über der Abzugsfeder | Gehäuse links | hohl |
| Drehgeber-Aufnahme in der Griffunterseite | Gehäuse L/R | hohl |
| USB-C-Durchbruch und Mulde | Gehäuse links | massiv, Wand ≥ 2 mm |
| **Offene Kabelnuten an der Teilungsfläche** | alle | Damm (Wand) bis zur Teilungsfläche hochziehen |
| Einschmelzmuttern M3 (Loch Ø 4,0) | Gehäuse links, Handschutz vorn links, Zapfen | Dom mit ≥ 2 mm Wand, **wird umgossen** |
| Schraubensenkungen M3 | rechte Hälften | Dom mit ≥ 2 mm Wand, wird umgossen |
| Zuganker-Bohrungen M4 + Mutternischen (offen zur Teilung) | Gehäuse, Zwischenring, Handschutz hinten, Schaft | Bohrung als Röhre, Nische hohl mit Damm |
| Stahlstege Ø 10 (96 / 77 mm) | Gehäuse, Zwischenring, Handschutz hinten, Schaft | Bohrung als Röhre, wird umgossen |
| OLED-Sockel, OLED-Schacht | Schaft L/R | hohl |
| GX16-Aufnahme, Sechskanttasche der Mutter, Westenschacht | Schaft L/R | hohl, Wand ≥ 2 mm |
| Schlitz für die gefangene M4-Mutter (Zuganker hinten) | Schaft L/R | hohl, Damm bis Teilung |
| Lautsprechertasche, Schallkammer, **Basskammer (ca. 42 cm³)** | Handschutz vorn | **hohl**, nicht verändern |
| Linsengewinde M24 × 1,5, LED-Sitz, Ringlichtkanal, TSOP-Aufnahme | Handschutz vorn | unverändert |

### 2.3 Antennenzone

- **WROOM-1U mit externer Antenne:** Bereich um RP-SMA-Buchse und Pigtail-Schlaufe
  hohl lassen. Im Umkreis von 15 mm darf nur PU-Schaum hinein, kein Quarzharz.
- **WROOM-1 mit PCB-Antenne:** Im Umkreis von 15 mm um den Antennenbereich des Moduls
  wird nichts gefüllt.

### 2.4 Verkrallung

An den Innenwänden der Kammern kleine Rippen oder Noppen (1,5 × 1,5 mm, Abstand ca. 10 mm)
oder schwalbenschwanzförmige Nuten vorsehen. PU haftet auf PETG nur mäßig, die Füllung
soll mechanisch halten.

### 2.5 Griffverstärkung (optional, prüfen)

Ein Kanal Ø 6,5 für einen **Carbonstab Ø 6** oder eine **Gewindestange M5**, vom
Griffende bis über den Abzug ins Gehäuse. Dabei mit Motorschacht, Drehgeber und
Abzugsmechanik auf Kollision prüfen (`kabelwege.py` analog als Zylinder gegen die
Baugruppe laufen lassen). Ist kein durchgehender Weg frei: zwei kürzere Stäbe beidseits
des Motorschachts.

---

## 3. Zonenplan pro Teil

| Teil | Füllung | Begründung |
|---|---|---|
| `gehaeuse_links/rechts` | **Quarzharz** komplett (+ Stab aus 2.5) | Griff ist die typische Bruchstelle, dazu Krafteinleitung an Einschmelzmuttern, Zuganker-Nischen und Stegbohrungen. Keine Schaumzone: Die Trennwände um die einzelnen Quarzharz-Inseln hätten ca. 15 cm³ je Hälfte gekostet, und das Gehäuse sitzt nahe am Schwerpunkt |
| `gehaeuse_links/rechts` – Antennenzone | hohl | siehe 2.3 |
| `zwischenring` | unverändert, 100 % gedruckt | klein, kaum Zeitgewinn |
| `handschutz_hinten` – Zapfen (4 Einschmelzmuttern, 2 gefangene M4) | **Quarzharz** | trägt den vorderen Handschutz und die Zuganker |
| `handschutz_hinten` – Rest | PU-Schaum | |
| `handschutz_vorn_links/rechts` | PU-Schaum in den Restvolumen, sonst unverändert | vorne leicht bleiben, Akustik nicht anfassen |
| `schaft_links/rechts` | **Quarzharz** (Hauptballast) | Gegengewicht zu Schalldämpfer und Lautsprecher |
| `magazin`, `magazin_unterteil` | nicht füllen, normal drucken | Akku; keine Wärme, nichts Festes um die Zelle |
| Kleinteile (Abzug, Nachladehebel, Frontkappe, Linsenhülse, TSOP-Einsatz, OLED-Rahmen, Korn, Spannhebel) | unverändert | zu klein, Präzisionsteile |

---

## 4. Druckprofil (neu)

Gilt für alle Teile mit Gießkammern (Gehäuse L/R, Handschutz hinten, Schaft L/R,
Handschutz vorn L/R):

| Parameter | Alt | Neu |
|---|---|---|
| Düse | 0,4 | 0,4 (unverändert) |
| Schichthöhe | – | 0,16–0,20 mm, variable Schichthöhe an sichtbaren Rundungen |
| Linienbreite | – | Außenwand 0,42, Innenwände 0,5–0,6 |
| Wände | 6 | **2**, an tragenden Domen und Röhren mehr (siehe Hebel 1) |
| Infill | 50 % Gyroid | **Lightning** in den Gießkammern |
| Modifier | – | 100 % in Domen und Bunden, die nicht umgossen werden |
| Material | PETG/ASA | PETG/ASA (kein PLA wegen Wärme beim Aushärten) |
| Temperatur / Lüfter | – | PETG ca. 250 °C, Lüfter 30–50 % (Schichthaftung) |

- Druckrichtung beibehalten (flach auf der Teilungsfläche). Das ist für das Gießen
  ohnehin die richtige Lage, und die Schichten liegen dann längs im Griff.
- Details zu Geschwindigkeit und Linienbreiten in Abschnitt 4a, Hebel 2.

---

## 4a. Maximale Druckzeit-Reduktion

Ziel: Druckzeit pro Waffe auf **ca. 15–20 h** bei detailreicher Außenseite
(Schätzung, mit Slicer prüfen).
Die Füllung übernimmt Festigkeit und Gewicht, die Schale ist nur noch Form und Haut.

### Hebel 1 – Kammern per Slicer-Modifier statt CAD (Variante B)

**Umgesetzt:** Modifier-STLs je Teil in [`mp5_giessfuellung/`](../mp5_giessfuellung/README.md), erzeugt
von `gehaeuse/scripts/giessfuellung.py` (2 mm Wand um alles, offen nur zur Bettseite, Überhänge der Kammern bis 45°, Zonen nach Abschnitt 3).

Teile liegen flach auf der Teilungsfläche. Pro Gießzone einen Modifier (Quader oder
eigene STL aus `umbau.py`) mit:

| Einstellung im Modifier | Wert |
|---|---|
| Bodenschichten (= Teilungsfläche) | **0** → Kammer bleibt zur Teilung offen |
| Deckschichten | **normal (4–5)** – die Seitenfläche der Waffe liegt oben und ist Deckfläche, sie bildet die Außenhaut über der Kammer |
| Infill | **Lightning** – stützt nur die Deckschichten und wird mit eingegossen |
| Wände | Standardwert des Teils |

Funktionsbereiche (Bohrungen, Schächte, Taschen) sind Löcher im Volumen. Der Slicer
legt automatisch Wände um sie herum, sie werden dadurch zu geschlossenen Röhren.
Mit 2 Wänden sind das aber nur ca. 0,9 mm. Wo Abschnitt 2.2 mehr verlangt (Röhren
≥ 1,2 mm: 3 Wände; Dome, USB-C, GX16 ≥ 2 mm: 4–5 Wände), dort einen eigenen Modifier
mit mehr Wänden oder 100 % Infill setzen.
Damit entfallen Kammer-Geometrie, Trennwände und Kammerdecken-Support aus Variante A.
Trennung Quarzharz/Schaum: eine Trennwand bleibt als schmaler Modifier mit 100 % Infill
(1,5 mm breit) stehen.

### Hebel 2 – Wände und Linienbreiten (Außenseite detailreich)

Vorgabe: Die Außenseite bleibt fein, gedruckt wird mit der normalen 0,4er Düse.
Die Zeit wird innen gespart, nicht an der Haut. Der größte Gewinn kommt ohnehin aus
dem Wegfall von 6 Wänden und 50 % Gyroid.

| Parameter | Detail-Profil |
|---|---|
| Düse | 0,4 |
| Schichthöhe | 0,16–0,20 mm, **variable Schichthöhe** nur an sichtbaren Rundungen (Handschutz, Schaftkappe) |
| Außenwand | Linienbreite 0,42, normale bis langsame Geschwindigkeit |
| Innenwand | Linienbreite 0,5–0,6, schnell |
| Wände | **2**, an tragenden Domen und Röhren mehr (Hebel 1) |
| Infill in Gießkammern | Lightning, im Orca/Prusa-Slicer „Infill alle 2 Schichten kombinieren“ |
| Untere Schichten außerhalb der Kammern | 3–4 |

- Die Kombination „feine Außenwand + breite Innenwand + kombiniertes Infill“ bringt
  fast die Geschwindigkeit eines groben Drucks bei feiner Oberfläche.
- Begrenzung bei den Innenwänden ist der **Volumenstrom**, nicht die Geschwindigkeit.
  PETG ca. 15–20 mm³/s mit Standard-Hotend, 30+ mm³/s mit High-Flow. Wert im Slicer
  eintragen, dann rechnet er realistisch.
- Bei 2 Wänden zuerst den Probekörper (Abschnitt 8) auf Verzug durch Wärme und
  Schaumdruck testen.

### Hebel 3 – Zeit dort sparen, wo man nichts sieht

- Bügeln (Ironing) nur auf sichtbaren Flachstellen, sonst aus
- Naht an Kanten oder auf die Innenseite legen
- Details bleiben vollständig erhalten
- Schichtlinien nach Bedarf mit dünner Füllgrundierung überdecken (keine grobe
  Nacharbeit nötig)

### Hebel 4 – Kaufteile statt Druck

| Bauteil | Ersatz | Gedruckt wird nur noch |
|---|---|---|
| Schalldämpfer-Rohr | Alu-Rohr oder HT-/KG-Rohr passenden Durchmessers | Einsatz mit Linsengewinde, LED-Sitz, Basskammer, Frontkappe |
| Stege | bereits Stahl | – |
| Magazin-Unterteil | prüfen, ob Stück Alu-Rechteckrohr passt | Deckel |

Der Schalldämpfer ist ein großes, hohes Rundteil und kostet viel Druckzeit. Ein Rohr
mit gedrucktem Innenleben spart dort am meisten. Dafür `handschutz_vorn_links/rechts`
in Handschutz und Rohreinsatz aufteilen.

**Schalllöcher im Rohrbereich** – drei Möglichkeiten:
1. **Trennung an der Schallkammer:** Lautsprecher, Schallkammer und Lochreihen bleiben
   im gedruckten Handschutz. Das Rohr beginnt erst davor (Linse, LED, Ringlicht) und
   braucht keine Löcher.
2. **Rohr bohren:** Bohrlehre drucken (Halbschale, die aufs Rohr geklemmt wird, mit
   Führungsbohrungen Ø 1,8 an den Positionen aus dem CAD). Pro Rohr ca. 10–15 min,
   für jede Waffe wiederverwendbar. Gründlich entgraten und Späne entfernen, sonst rascheln sie am Lautsprecher.
3. **Gelochtes Rohr:** Alu-Lochrohr oder gerolltes Lochblech. Wirkt optisch wie ein
   „ported“ Schalldämpfer, ein Gaze- oder Stoffeinsatz innen schützt die Membran.

Akustik: Die Basskammer (ca. 42 cm³) und die Schallkammer müssen im gedruckten Einsatz
dicht bleiben. Ein starres Rohr außen herum stört nicht, eher klingt es klarer als
dünner Kunststoff.

### Hebel 5 – Support und Plattenbelegung

- Tree-Support, Überhänge bis 50–55° ohne Stütze testen (Probe drucken).
- Im CAD Fasen statt Überhängen, wo die Optik es erlaubt.
- Gleiche Teile mehrerer Waffen auf eine Platte (Teile einer Sorte gemeinsam drucken).
  Spart Aufheiz-, Kalibrier- und Wechselzeit und läuft am Stück über Nacht.

### Hebel 6 – Slicer- und Druckerfeintuning

| Maßnahme | Effekt |
|---|---|
| Beschleunigung für Innenwände, Infill und Fahrwege hoch, Außenwand moderat | Außenhaut bleibt sauber, Rest deutlich schneller |
| Input Shaping und Pressure Advance kalibrieren (Klipper oder Bambu/Prusa-Kalibrierung) | erst damit sind hohe Beschleunigungen ohne Ghosting möglich |
| Z-Hop nur „über gedruckten Flächen“, Retraction kurz | bei vielen Bohrungen und Domen spürbar weniger Fahrzeit |
| „Wände nicht kreuzen“ an | weniger Retracts, keine Fäden außen |
| Textur-PEI-Platte, kein Brim, erste Schicht nicht unnötig langsam | spart pro Platte Minuten und Nacharbeit |
| Mindestschichtzeit für kleine Teile über mehrere Teile pro Platte erreichen statt durch Abbremsen | kein langsames „Warten“ auf Kühlung |

### Hebel 7 – Vasenmodus für einfache Hüllen

Einfache, geschlossene Hüllen ohne innere Funktion (z. B. Schaftkappe, Magazin-Unterteil,
Deko-Abdeckungen) im **Spiralvasenmodus** mit breiter Linie (0,6–0,7 mm mit der 0,4er Düse)
drucken. Danach mit Schaum oder Quarzharz ausgießen. Das ist der schnellste
FDM-Modus überhaupt, die Außenfläche ist nahtlos.

### Hebel 8 – Silikonabformung (verworfen, nur Referenz für größere Serien)

Nicht günstiger als Druck + Gießfüllung (PU-Harz pro kg teurer als Filament,
Formen 80–150 € einmalig) und deutlich mehr Handarbeit. Erst sinnvoll, wenn der
Drucker der Engpass ist (ab ca. 8–10 Waffen oder fester Termin).

Für mehrere Waffen lohnt es sich, einfache Außenteile nicht jedes Mal zu drucken:

1. **Ein Master pro Teil** fein drucken, schleifen und grundieren.
2. **Silikonform** abnehmen (Additionsvernetzend, Shore A 20–30).
3. Teil in **PU-Gießharz** gießen. Hohl über Schwenkguss (Harz in der Form schwenken,
   bis eine 2–3 mm dicke Haut entsteht), dann wie gehabt mit Schaum oder Quarzharz füllen.
4. Entformen nach 15–60 min je nach Harz. Pro Teil also Minuten statt Stunden.

Geeignet sind Teile mit **einfacher Innenseite**: Schaft, Handschutz hinten,
Magazin, Schaftkappe. Die Gehäusehälften mit Platinentasche, Schächten und Abzug
bleiben gedruckt, weil ihre Innengeometrie eine mehrteilige Form bräuchte.

Kosten: Silikon ca. 25–35 €/kg, für Schaft und Handschutz zusammen grob 2–3 kg.
Die Details der Oberfläche werden 1:1 übernommen.

### Reihenfolge der Umsetzung

1. Druckzeit-Aufteilung im Slicer ansehen (Wände / Infill / Support / Flächen)
2. Hebel 1 + 2 am Probekörper, dann an `schaft_links`
3. Hebel 4: Schalldämpfer auf Rohr umkonstruieren
4. Hebel 3 und 5 nebenbei

---

## 5. Gewicht und Balance

Dichten (ca.):

| Füllung | g/cm³ |
|---|---|
| 2K-PU-Hartschaum | 0,05–0,15 |
| PU-Gießharz pur | 1,1 |
| PU-Harz + Quarzsand (dicht gerüttelt) | 1,8–2,0 |
| PU-Harz + Stahlschrot (nur weit weg von Antenne) | 4,0–4,5 |

Vorgehen:
1. Kammervolumen: `mp5_giessfuellung/volumen.json`. Ergebnis (45°-Regel, Gehäuse ganz Quarzharz): zusammen
   ca. 237 cm³ Quarzharz (ca. 450 g, davon 200 g im Schaft) und 132 cm³ Schaum. Gießbar sind je nach Teil
   ca. 33–56 % des Volumens. Mehr Ballast nur mit Stahlschrot im Schaft oder mit einem eingelegten Gewicht.
2. Gewicht je Zone = Volumen × Dichte, plus gedruckte Teile (Slicer), Elektronik,
   Stahlstege und Zuganker.
3. Schwerpunkt gegen die Griffachse rechnen. Ziel: knapp vor dem Griff.
4. **Zielgewicht festlegen** (Vorschlag: 2,0–2,5 kg, weil beim Lasertag gelaufen wird).
   Wird es zu schwer, Schaft teilweise auf Schaum umstellen.

---

## 6. Gießablauf

**Vorbereitung**
1. Quarzsand (0,1–0,5 mm) im Backofen trocknen: 2 h bei 120 °C, abkühlen lassen,
   luftdicht lagern. Feuchter Sand lässt PU-Harz aufschäumen.
2. Einschmelzmuttern **vorher** setzen. Gefettete M3-Schrauben eindrehen,
   damit kein Harz ins Gewinde läuft.
3. Stahlstege und Zuganker-Bohrungen mit gefetteten Dummy-Stäben (Ø 10 bzw. M4)
   belegen, oder die echten Stege mit eingießen, wenn sie nicht mehr heraus müssen.
4. Röhren, Nischen und offene Nuten mit Malerkrepp oder Knete abdecken.
5. Hälfte waagerecht ausrichten (Wasserwaage).

**Quarzharz**
1. Kammer zuerst mit trockenem Sand füllen und rütteln (z. B. Hälfte auf ein
   vibrierendes Gerät legen), bis sich der Sand gesetzt hat.
2. Dünnflüssiges PU-Gießharz mit **langer Topfzeit (10–20 min)** anmischen und
   langsam nachgießen, bis die Zwischenräume gefüllt sind.
3. **In Lagen von 1–2 cm** arbeiten und jede Lage abkühlen lassen.
   Große Volumen auf einmal werden heiß und verziehen die Schale.
4. Bis 0,5–1 mm unter die Teilungsfläche füllen.

**PU-Schaum**
1. Erst gießen, wenn das Quarzharz ausgehärtet ist.
2. Nur ca. ein Drittel des Kammervolumens einfüllen und frei aufgehen lassen.
3. Nach dem Aushärten Überstand mit einem Cutter bündig zum Rand abschneiden
   (bis 0,5–1 mm unter der Teilung).

**Danach**
- Mindestens 24 h aushärten lassen.
- Abdeckungen entfernen, Röhren und Gewinde freilegen, Dummy-Stäbe ziehen.
- Probe-Montage der Hälften: Passung, Schrauben, Kabel einlegen.

**Arbeitsschutz:** 2K-PU enthält Isocyanate. Nitrilhandschuhe, Schutzbrille, gut
lüften, beim Mischen größerer Mengen Atemschutz (A2/P2).

---

## 7. Material pro Waffe (aus den Kammervolumen, mit Verschnitt)

| Material | Menge |
|---|---|
| PU-Gießharz, dünnflüssig, lange Topfzeit | ca. 0,15 kg |
| Quarzsand 0,1–0,5 mm, getrocknet | ca. 0,45 kg |
| 2K-PU-Hartschaum | ca. 0,05 kg |
| Carbonstab Ø 6 oder Gewindestange M5 | 1 Stück (optional) |
| Mischbecher, Waage (0,1 g), Holzspatel, Malerkrepp, Silikonfett | – |

---

## 8. Testplan

1. **Probekörper:** Box 60 × 40 × 25 mm mit dem neuen Druckprofil (Abschnitt 4), eine Seite offen.
   Einmal Quarzharz, einmal Schaum. Prüfen: Verzug, Erwärmung (Thermometer),
   Haftung, Gewicht, Fallen aus 1,5 m auf Beton.
2. **Erstes echtes Teil:** `schaft_links`. Einfache Geometrie, viel Ballast, wenig Elektronik.
3. **Gehäusehälften:** erst nach erfolgreichem Schaft.
4. **Vergleich:** Druckzeit, Filament, Gewicht, Schwerpunkt, Falltest gegen ein
   konventionell gedrucktes Teil.
5. Erst danach Serie für mehrere Waffen.

---

## 9. Offene Punkte

- [ ] Geometrie-Bibliothek in `umbau.py` für Offset und Boolean prüfen (Innenoffset
      robust auf den Original-STLs?)
- [ ] Kollisionsprüfung Griffstab gegen Motorschacht und Drehgeber
- [x] Kammervolumen exportieren (`mp5_giessfuellung/volumen.json`)
- [ ] Gewichtsbudget rechnen (Schwerpunkt, Zielgewicht)
- [ ] Antennenvariante festlegen (WROOM-1 oder WROOM-1U) → Sperrzone
- [ ] Probekörper drucken und gießen
- [ ] Stahlstege eingießen oder lösbar lassen?
- [ ] Hinweis in `mp5_umbau/README.md` und Druckeinstellungen dort aktualisieren
