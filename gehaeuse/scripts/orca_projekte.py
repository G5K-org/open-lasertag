"""OrcaSlicer-Projekte (.3mf) der Gießvariante für Anycubic i3 Mega S und Artillery Sidewinder X2 (Düse 0,4, PETG).

Gleiche Teile und Einstellungen wie mp5_guss_p2s.3mf aus bambu_projekte.py, angepasst an den Drucker (PRINTERS):
  - i3 Mega S, Bett 210 × 210 mm: Schafthälften je auf eine eigene Platte, vorderer Handschutz (206 mm lang) um 45°
    gedreht, Systemprofil 0.20mm Standard @Anycubic i3MegaS, Filament Anycubic Generic PETG.
  - Sidewinder X2, Bett 300 × 300 mm: Platten wie beim P2S, Systemprofil 0.20mm Standard @Artillery X2, Filament
    Artillery Generic PETG.
  - Geschwindigkeiten und Beschleunigung bleiben wie im Systemprofil, Retract auch (außer X2, siehe filament_extra).
  - "Partial" der vertikalen Schalendicke heißt in Orca ensure_critical_only.
  - Orca übernimmt aus der Liste zum Zusammenfügen weder subtype noch print_params der Teile (alles wird
    normal_part, die Kammern würden mit Infill gefüllt). fix_parts trägt beides danach in die 3MF ein.
  - Die Kommandozeile lässt different_settings_to_system leer. Die Oberfläche lädt dann das Systemprofil
    unverändert (Brim, Skirt, 15 % Crosshatch ...). fix_settings trägt die geänderten Schlüssel ein.

Ergebnis: gehaeuse/orca/mp5_guss_<drucker>.3mf, Druckzeit und Filament je Drucker und Platte in
orca/druckzeiten.json.

Aufruf: ORCA_SLICER=/usr/bin/orca-slicer python orca_projekte.py [i3megas] [x2]     (ohne Angabe beide)
        (Profile aus ~/.config/OrcaSlicer/system, fehlt der Hersteller dort, aus resources/profiles neben
        orca-slicer; ORCA_PROFILES setzt einen anderen Ordner; braucht numpy, trimesh, manifold3d)
"""
import json
import math
import os
import re
import shutil
import sys
import tempfile
import zipfile

import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bambu_projekte as BP  # noqa: E402

OUT = os.path.join(BP.GEH, "orca")

GUSS_GLOBAL = {k: v for k, v in BP.GUSS_GLOBAL.items() if k != "curr_bed_type"}
GUSS_GLOBAL.update(ensure_vertical_shell_thickness="ensure_critical_only",
                   adaptive_layer_height="0")           # im Systemprofil an; Kammerdecken brauchen feste 0,2 mm

MARGIN = 5.0                                            # Rand zum Bettrand (Skirt liegt 2 mm neben dem Teil)
GAP = 12.0                                              # Abstand der Teile; bei 8 mm Bahnkonflikt im Tree-Support

PRINTERS = {
    "i3megas": {
        "vendor": "Anycubic", "machine": "Anycubic i3 Mega S 0.4 nozzle",
        "process": "0.20mm Standard @Anycubic i3MegaS", "filament": "Anycubic Generic PETG",
        "bed": 210.0,
        # Brim und Skirt ragten bei den Gehäusehälften übers Bett
        "extra": {"brim_type": "no_brim", "skirt_loops": "0"},
        "rot": {"handschutz_vorn_links": 45.0, "handschutz_vorn_rechts": 45.0},   # Grad um Z, sonst zu lang
        # Gehäusehälften 4,5 mm nach hinten: Der Tree-Support an der Vorderkante reicht sonst bis Y 0,2 und liegt auf
        # der Reinigungslinie des Startcodes (Y 1–2, X 5–205)
        "shift_y": {"gehaeuse_links": 4.5, "gehaeuse_rechts": 4.5},
        "plates": [("Gehäuse links", ["gehaeuse_links"]), ("Gehäuse rechts", ["gehaeuse_rechts"]),
                   ("Handschutz vorn links", ["handschutz_vorn_links"]),
                   ("Handschutz vorn rechts", ["handschutz_vorn_rechts"]),
                   ("Schaft links", ["schaft_links"]), ("Schaft rechts", ["schaft_rechts"])] + BP.PLATES[5:],
    },
    # Reinigungslinie im Startcode bei Y 0,2–0,5, X 10–100; die mittig liegenden Teile bleiben weit davon weg
    "x2": {
        "vendor": "Artillery", "machine": "Artillery Sidewinder X2 0.4 nozzle",
        "process": "0.20mm Standard @Artillery X2", "filament": "Artillery Generic PETG",
        # Auto-Brim des Profils wird um die Gehäusehälften 17 mm breit und lief neben dem Handschutz übers Bett;
        # Skirt (3 Runden, 2 mm Abstand) bleibt, 10 mm Rand reichen dafür
        "bed": 300.0, "margin": 10.0, "rot": {}, "shift_y": {},
        # Starkes Stringing mit dem Systemprofil (255 °C, 1 mm Retract, kein Wipe): Leerfahrten innerhalb der Wände
        "extra": {"brim_type": "no_brim", "reduce_crossing_wall": "1"},
        # PETG kühler, mehr und schneller zurückziehen, beim Zurückziehen wischen, niedrigerer Z-Hop
        "filament_extra": {"nozzle_temperature": ["240"], "nozzle_temperature_initial_layer": ["245"],
                           "filament_retraction_length": ["1.6"], "filament_retraction_speed": ["40"],
                           "filament_deretraction_speed": ["30"], "filament_wipe": ["1"],
                           "filament_wipe_distance": ["2"], "filament_retract_before_wipe": ["70%"],
                           "filament_z_hop": ["0.2"]},
        # Gehäusehälfte und vorderer Handschutz nebeneinander, alles Übrige auf eine Platte
        "plates": [("Gehäuse links, Handschutz vorn links", ["gehaeuse_links", "handschutz_vorn_links"]),
                   ("Gehäuse rechts, Handschutz vorn rechts", ["gehaeuse_rechts", "handschutz_vorn_rechts"]),
                   ("Schaft, Handschutz hinten, Zwischenring, Magazin, Kleinteile",
                    ["schaft_links", "schaft_rechts"] + BP.PLATES[5][1] + BP.PLATES[6][1])],
    },
}


def rotated(path, deg, center, tmp):
    """STL um Z drehen (um den Mittelpunkt des Teils, damit Blocker und Modifier deckungsgleich bleiben)."""
    if not deg:
        return path
    tm = trimesh.load(path)
    tm.apply_transform(trimesh.transformations.rotation_matrix(math.radians(deg), [0, 0, 1], center))
    os.makedirs(os.path.join(tmp, "rot"), exist_ok=True)
    p = os.path.join(tmp, "rot", os.path.basename(path))         # gleicher Dateiname = Objektname in Orca
    tm.export(p)
    return p


def layout(paths, bed, margin):
    """Reihen wie BP.layout, für das Bett des Druckers und mit den (gedrehten) Dateien. Jedes Teil kommt in die erste
    Reihe, in der es noch Platz hat (sonst bliebe hinter einem breiten Teil die Reihe halb leer)."""
    box = {n: trimesh.load(p).bounds[:, :2] for n, p in paths.items()}
    order = sorted(paths, key=lambda n: -(box[n][1][1] - box[n][0][1]))
    place, rows = {}, []                                # Reihe: [y, Tiefe, nächstes x]
    for n in order:
        w, h = box[n][1] - box[n][0]
        row = next((r for r in rows if r[2] + w <= bed - 2 * margin), None)
        if row is None:
            row = [rows[-1][0] + rows[-1][1] + GAP if rows else 0.0, h, 0.0]
            rows.append(row)
        place[n] = (row[2], row[0])
        row[2] += w + GAP
    width = max(place[n][0] + box[n][1][0] - box[n][0][0] for n in paths)
    height = max(place[n][1] + box[n][1][1] - box[n][0][1] for n in paths)
    if width > bed - 2 * margin or height > bed - 2 * margin:
        sys.exit(f"Platte zu klein für {list(paths)}: {width:.1f} × {height:.1f} mm")
    ox, oy = (bed - width) / 2, (bed - height) / 2
    return {n: (ox + place[n][0] - box[n][0][0], oy + place[n][1] - box[n][0][1]) for n in paths}


def assemble_list(pr, tmp):
    plates, idx = [], 0
    for title, names in pr["plates"]:
        src, center = {}, {}
        for name in names:
            src[name] = os.path.join(BP.GUSS if name in BP.CAST else BP.MOD, name + ".stl")
            center[name] = trimesh.load(src[name]).bounds.mean(0)
        paths = {n: rotated(src[n], pr["rot"].get(n, 0), center[n], tmp) for n in names}
        pos = layout(paths, pr["bed"], pr.get("margin", MARGIN))
        objs = []
        for name in names:
            idx += 1
            at = {"pos_x": [pos[name][0]], "pos_y": [pos[name][1] + pr["shift_y"].get(name, 0.0)], "pos_z": [0.0]}
            part = {"path": os.path.abspath(paths[name]), "count": 1, "filaments": [1], "assemble_index": [idx],
                    "subtype": "normal_part", **at}
            mods = []
            if name in BP.CAST:
                blk = rotated(BP.kammer_blocker(name, tmp), pr["rot"].get(name, 0), center[name], tmp)
                mods.append({"path": blk, "count": 1, "filaments": [1], "assemble_index": [idx],
                             "subtype": "support_blocker", **at})
            if name == "handschutz_hinten":
                mods.append({"path": BP.zapfen_box(tmp), "count": 1, "filaments": [1], "assemble_index": [idx],
                             "subtype": "modifier_part", "print_params": BP.ZAPFEN, **at})
            elif name == "zwischenring":
                part["print_params"] = {"sparse_infill_density": "100%"}
            elif name not in BP.CAST:
                part["print_params"] = BP.SOLID_SMALL
            objs += [part] + mods
        plates.append({"plate_name": title, "need_arrange": False, "objects": objs})
    return {"plates": plates}


def fix_parts(path):
    """Blocker und Zapfen-Modifier wie im Bambu-Projekt kennzeichnen (Teilnamen aus den Dateinamen)."""
    def fix(m):
        part, name = m.group(0), m.group(1)
        if "__kammer_blocker" in name:
            return part.replace('subtype="normal_part"', 'subtype="support_blocker"', 1)
        if "__zapfen" in name:
            extra = "".join(f'\n      <metadata key="{k}" value="{v}"/>' for k, v in BP.ZAPFEN.items())
            part = part.replace('subtype="normal_part"', 'subtype="modifier_part"', 1)
            return re.sub(r'(<metadata key="name" value="[^"]*"/>)', lambda n: n.group(1) + extra, part, count=1)
        return part
    with zipfile.ZipFile(path) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in items:
            if info.filename == "Metadata/model_settings.config":
                data = re.sub(r'<part [^>]*>\s*<metadata key="name" value="([^"]*)"/>.*?</part>', fix, data.decode(),
                              flags=re.S).encode()
            z.writestr(info, data)
    os.replace(tmp, path)


def fix_settings(path, changed):
    """different_settings_to_system füllen: [Prozess, Filament, Drucker], je Schlüssel mit ';' getrennt."""
    with zipfile.ZipFile(path) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in items:
            if info.filename == "Metadata/project_settings.config":
                cfg = json.loads(data)
                cfg["different_settings_to_system"] = [";".join(sorted(changed[k])) for k in ("process", "filament",
                                                                                            "machine")]
                data = json.dumps(cfg, indent=4, ensure_ascii=False).encode()
            z.writestr(info, data)
    os.replace(tmp, path)


def differs(base, extra):
    """Schlüssel aus extra, deren Wert vom Systemprofil abweicht (Listenwerte wie im Profil verglichen)."""
    def norm(v):
        return [str(x) for x in v] if isinstance(v, list) else [str(v)]
    return [k for k, v in extra.items() if k not in base or norm(base[k]) != norm(v)]


def profiles_root(cli, vendor):
    """Systemprofile des Herstellers: ORCA_PROFILES, ~/.config/OrcaSlicer/system oder die mitgelieferten."""
    if os.environ.get("ORCA_PROFILES"):
        return os.path.join(os.environ["ORCA_PROFILES"], vendor)
    for base in (os.path.expanduser("~/.config/OrcaSlicer/system"),
                 os.path.join(os.path.dirname(os.path.realpath(shutil.which(cli) or cli)), "resources", "profiles")):
        if os.path.isdir(os.path.join(base, vendor)):
            return os.path.join(base, vendor)
    sys.exit(f"Keine Orca-Profile für {vendor} gefunden, ORCA_PROFILES setzen")


def build(cli, key):
    pr = PRINTERS[key]
    root = profiles_root(cli, pr["vendor"])
    glob = dict(GUSS_GLOBAL, **pr["extra"])
    os.makedirs(OUT, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        files, changed = {}, {}
        for kind, extra in (("machine", {}), ("process", glob), ("filament", pr.get("filament_extra", {}))):
            files[kind] = os.path.join(tmp, f"{kind}.json")
            json.dump(BP.profile(root, kind, pr[kind], extra), open(files[kind], "w"), indent=1)
            changed[kind] = differs(BP.profile(root, kind, pr[kind], {}), extra)
        lst = os.path.join(tmp, "list.json")
        json.dump(assemble_list(pr, tmp), open(lst, "w"), indent=1)
        proj = os.path.join(OUT, f"mp5_guss_{key}.3mf")
        settings = ["--load-settings", f"{files['machine']};{files['process']}", "--load-filaments", files["filament"]]
        code, log = BP.run(cli, settings + ["--load-assemble-list", lst, "--export-3mf", os.path.basename(proj),
                                            "--outputdir", OUT])
        if code != 0:
            sys.exit(f"{key}: Export fehlgeschlagen ({code})\n{log[-2000:]}")
        BP.rename_objects(proj)
        fix_parts(proj)
        fix_settings(proj, changed)
        sliced = os.path.join(tmp, "sliced.3mf")
        code, log = BP.run(cli, [proj, "--slice", "0", "--export-3mf", os.path.basename(sliced), "--outputdir", tmp])
        if code != 0:
            sys.exit(f"{key}: Slicen fehlgeschlagen ({code})\n{log[-2000:]}")
        plates = BP.slice_info(sliced)
    for p, (title, names) in zip(plates, pr["plates"]):
        p["name"], p["teile"] = title, names
    report = {"platten": plates, "stunden": round(sum(p["stunden"] for p in plates), 1),
              "gramm": round(sum(p["gramm"] for p in plates))}
    if os.path.exists(os.path.join(OUT, "result.json")):
        os.remove(os.path.join(OUT, "result.json"))
    times = os.path.join(OUT, "druckzeiten.json")
    data = json.load(open(times)) if os.path.exists(times) else {}
    data[key] = {"guss": report}
    json.dump(data, open(times, "w"), indent=1, ensure_ascii=False)
    print(key, "guss", report["stunden"], "h", report["gramm"], "g")
    return report


if __name__ == "__main__":
    cli = os.environ.get("ORCA_SLICER", "orca-slicer")
    keys = sys.argv[1:] or list(PRINTERS)
    for k in keys:
        if k not in PRINTERS:
            sys.exit(f"Unbekannter Drucker {k}, möglich: {', '.join(PRINTERS)}")
    for k in keys:
        build(cli, k)
