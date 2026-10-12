# MP5-Umbau für die Lasertag-Elektronik

Geänderte Druckteile und neue Teile, erzeugt mit [`../scripts/umbau.py`](../scripts/umbau.py).
Geänderte Originalteile liegen in derselben Drucklage wie die Originale, neue Teile druckfertig
(flach bzw. stehend). Zusammengesetzt: [`../baugruppe/`](../baugruppe/).

## Dateien

Vollständiger Drucksatz, jedes Teil mit eindeutigem Namen (gleicher Name als Knoten in der Baugruppe).

| Datei | Teil | aus Original | Änderung |
|---|---|---|---|
| `gehaeuse_links.stl` | Gehäuse links | `obj_1_3` | Platinentasche (Bauteilseite), Abzugsmechanik, Kabelschächte, Motor, Drehgeber, Einschmelzmuttern |
| `gehaeuse_rechts.stl` | Gehäuse rechts | `obj_3_6` | Platinentasche mit Domen, Abzugsmechanik, Kabelschächte, Motor, Drehgeber, Schraubensenkungen |
| `zwischenring.stl` | Zwischenring | `obj_5_5` | Kabelschacht |
| `handschutz_hinten.stl` | Handschutz hinten | `obj_10_2` | Schallkammer mit Löchern in den Rillen, Kabelschacht |
| `handschutz_vorn_links.stl` | Handschutz vorn mit Schalldämpfer links | `obj_10_2` | links/rechts geteilt (flach auf der Teilungsfläche), Einschmelzmuttern; Lautsprechertasche, Basskammer, TSOP-Aufnahme, Gewinde M24 × 1,5, LED-Sitz, Kabelkanäle, Zapfen für die Frontkappe |
| `handschutz_vorn_rechts.stl` | Handschutz vorn mit Schalldämpfer rechts | `obj_10_2` | Gegenstück, Schraubensenkungen |
| `frontkappe.stl` | Frontkappe | neu | 12 Fenster für das Ringlicht (Front unten drucken) |
| `linsenhuelse.stl` | Linsenhülse | neu | Gewinde M24 × 1,5 für die Linse Ø 20 |
| `tsop_einsatz.stl` | TSOP-Einsatz | neu | Halter für den TSOP34838 mit Linsenfenster (Fensterseite oben drucken) |
| `korn.stl` | Korn | `obj_7_1` | unverändert |
| `spannhebel_stift.stl` | Spannhebel Stift | `obj_11_12` | unverändert |
| `spannhebel_knauf.stl` | Spannhebel Knauf | `obj_9_10` | unverändert |
| `schaft_links.stl` | Schaft links | `obj_4_7` | OLED-Sockel, Kabelschacht |
| `schaft_rechts.stl` | Schaft rechts | `obj_2_4` | OLED-Sockel, Kabelschacht |
| `oled_rahmen.stl` | OLED-Rahmen | neu | Fenster 24 × 14 mit Fase (Außenseite oben drucken) |
| `steg_vorn_100mm.stl` | Steg vorn (Rundstab 100 mm) | `obj_8_8` | ein Stab, unverändert |
| `steg_hinten_77mm.stl` | Steg hinten (Rundstab 77 mm) | `obj_8_8` | auf 77 mm gekürzt |
| `magazin.stl` | Magazin | `obj_6_9` | Akkuhalter (3 Rippen), unteres Drittel abgetrennt, Öffnung oben |
| `magazin_unterteil.stl` | Magazin Unterteil | `obj_6_9` | abnehmbar, Zapfen stützt den Akku |
| `abzug.stl` | Abzug | `obj_1_3`/`obj_3_6` | aus dem Gehäuse gelöst, Nabe und Hebel (flach drucken) |
| `lage.json` | – | – | Lage der neuen Teile in der Waffe (für `baugruppe.py`) |

`obj_12_11` (Sechskantstift 6 × 17,6 mm) aus dem Originalsatz hat keine erkennbare Aufnahme und ist nicht enthalten.

## Kaufteile

| Teil | Typ |
|---|---|
| Achse Abzug | Stahlstift Ø 3 × 25 mm |
| Abzugsfeder | Druckfeder Ø 5 × 15 mm, Draht 0,5–0,6 mm (härter/weicher tauschbar) |
| Abzugsschalter | Omron D2F-01 (Stößel unten, Grundfläche oben) |
| Linse | Ø 20 mm, bis 7 mm dick, in die Hülse geklebt |
| IR-LED | 5 mm (z. B. TSAL6100), von vorn in den Sitz gesteckt |
| Ringlicht | 12 × WS2812/SK6812, Ø 36,8/23,3 mm (Adafruit #1643 o. ä.) |
| Akku | 1 × 18650 mit Kabel und JST-PH-2-Stecker |
| OLED | 0,96″ SSD1306 I²C 128 × 64 (Platine 27,3 × 27,8), Kabel direkt angelötet, ohne Stiftleiste |
| Drehgeber | EC11 mit Taster, Welle Ø 6, 20 mm |
| Vibrationsmotor | Ø 10 × 20 mm mit Unwucht |
| Platine | M2 × 8 ISO 7380 (2 ×) |
| Gehäusehälften | 6 × M3 × 10 ISO 4762, 6 × Einschmelzmutter M3 × 5,7 (Loch Ø 4,0) |
| Handschutz vorn | 5 × M3 × 10 ISO 4762, 5 × Einschmelzmutter M3 × 5,7 (Loch Ø 4,0) |
| Lautsprecher | Ø 40 mm, 4–8 Ω, 2–3 W, bis 6 mm Einbautiefe |
| Handschutz-Teilung | 2 × Stift Ø 2 × 12 mm |
| TSOP 6 | TSOP34838 (6 × 6,95 × 5,6 mm) |

## Einbau

- **Platine** in der rechten Hälfte, Oberkante X = 76 (4 mm höher als zuvor, Platz für den Abzug)
- **USB-C** durch die linke Seitenwand (Langloch 13,0 × 7,5)
- **Abzug:** Achse X = 136 / Y = 129, Stift durch beide Hälften; Hebel nach hinten unter
  Mikroschalter und Feder; Schalter löst bei ca. 4,5° aus, Anschlag bei 5° (Abzugsweg vorn ca. 3 mm)
- **Schalldämpfer:** Linsenhülse von vorn einschrauben und mit Werkzeug in den Schlitzen verstellen
  (LED-Abstand 13–26 mm, nominal 21 mm); ganz heraus nur bei abgenommener Frontkappe.
  LED von vorn in den Sitz stecken, Kabel nach hinten
- **Ringlicht** von hinten in die Frontkappe legen, Kabel durch den Kanal unten im Schalldämpfer;
  Frontkappe auf den Zapfen stecken
- **Kabelschacht** Ø 5 von der Mündung durch Handschutz, Zwischenring und Gehäuse bis zur Platine;
  Abzweig Ø 6 in den Magazinschacht (Akkukabel)
- **Magazin:** geteilt direkt unter dem Akku (der starre 18650 passt nicht durch den gebogenen
  unteren Teil); Akku von dort gerade einschieben, Unterteil aufstecken. Kabel mit JST-PH-Stecker
  oben heraus; vor dem Einsetzen mit dem Kabel aus dem Schacht verbinden, Stecker in den oberen
  Magazinraum schieben. Der Akku sitzt mit nur ca. 0,5 mm Luft – Zelle ohne dicken Schrumpfschlauch
- **OLED** angewinkelt in der Schrägfläche vorn oben am Schaft: abgerundeter Sockel, Modul von oben
  einkleben (Glas liegt unter der Rahmenstufe), Rahmen in die Stufe setzen; Kabel (Stiftleiste nicht
  bestücken) durch den Schacht im Schaft und Gehäuse zur Platine (OLED). Kimme und Korn bleiben
- **Drehgeber** hinten in der schrägen Griffunterseite, Achse entlang des Griffs, Buchse bündig,
  Welle schaut heraus (Kappe aufstecken)
- **Vibrationsmotor** über dem Griff, Unwucht hinten; Kabel mit dem Drehgeberkabel zur Platine (VIB)
- **Gehäusehälften** verschraubt: Einschmelzmuttern von der Teilungsebene in die linke Hälfte,
  Schrauben M3 × 10 von rechts (Kopf versenkt); vorn oben, Mitte oben, hinten oben, vor dem Abzug,
  hinten über dem Griff, unten im Griff
- **Handschutz vorn mit Schalldämpfer** links/rechts geteilt (Z = 0), beide Hälften flach drucken:
  Einschmelzmuttern in die linke Hälfte, Schrauben M3 × 10 von rechts (Kopf versenkt); 2 Schrauben
  direkt vor der Basskammer, 3 am Schalldämpfer. Lautsprecher, LED, TSOP-Einsatz und Kabel vor dem Verschrauben einlegen.
  Der Handschutz hinten bleibt einteilig
- **Lautsprecher** Ø 40 im Handschutz, Teilung bei Y = −56: Lautsprecher in die Tasche des vorderen
  Teils legen (Membran nach hinten), Kabel durch die kleine Bohrung in den Schacht und abdichten
  (Basskammer ca. 42 cm³ bleibt geschlossen), hinteren Teil mit 2 Stiften Ø 2 (einer je Hälfte) aufsetzen und verkleben.
  Der Schall geht durch 2 Reihen Löcher Ø 1,8 in den Rillen zwischen den Rippen
- **TSOP 6** vorn an der Rundung unter dem Korn, über dem Schalldämpfer, Linse nach vorn: TSOP von
  hinten in den Einsatz schieben, Kabel an die Beinchen (zeigen nach unten), Einsatz in die Aufnahme
  stecken; Kabel senkrecht nach unten in den Hauptschacht
- **Kabelschächte** laufen als gerade Stücke in beliebiger Richtung (auch diagonal), z. B. vom OLED
  schräg durch das Gehäuse und im Handschutz oben im Rohr um den Lautsprecher herum
