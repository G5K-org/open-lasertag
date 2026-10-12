# MP5-Umbau für die Lasertag-Elektronik

Geänderte Druckteile und neue Teile, erzeugt mit [`../scripts/umbau.py`](../scripts/umbau.py).
Geänderte Originalteile liegen in derselben Drucklage wie die Originale, neue Teile druckfertig
(flach bzw. stehend). Zusammengesetzt: [`../baugruppe/`](../baugruppe/).

## Dateien

| Datei | ersetzt / neu | Inhalt |
|---|---|---|
| `obj_1_3_links.stl`, `obj_3_6_rechts.stl` | `obj_1_3`, `obj_3_6` | Platinentasche, Abzugsmechanik, Kabelschächte, Motor, Drehgeber (Kimme bleibt) |
| `obj_4_7_schaft_links.stl`, `obj_2_4_schaft_rechts.stl` | `obj_4_7`, `obj_2_4` | OLED-Sockel in der Schrägfläche vorn oben, Kabelschacht |
| `obj_10_2_handschutz.stl` | `obj_10_2` | Innengewinde für die Linsenhülse, LED-Sitz, Kabelkanäle, Zapfen für die Frontkappe |
| `obj_5_5_zwischenring.stl` | `obj_5_5` | Kabelschacht |
| `obj_6_9_magazin.stl` | `obj_6_9` | Akkuhalter (3 Rippen), unteres Drittel abgetrennt, Öffnung oben |
| `steg_schaft_77mm.stl` | ein Stab aus `obj_8_8` | Steg zum Schaft, 77 mm |
| `abzug.stl` | neu | Abzug mit Nabe und Hebel (flach drucken) |
| `linsenhuelse.stl` | neu | Hülse M24 × 1,5 für die Linse Ø 20 |
| `frontkappe.stl` | neu | Kappe vorn am Schalldämpfer, 12 Fenster für das Ringlicht |
| `magazinboden.stl` | neu | abnehmbares Magazin-Unterteil mit Zapfen (stützt den Akku) |
| `oled_rahmen.stl` | neu | Rahmen über dem OLED, Fenster 24 × 14 mit Fase (Außenseite oben drucken) |
| `lage.json` | – | Lage der neuen Teile in der Waffe (für `baugruppe.py`) |

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
