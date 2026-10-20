"""OrcaSlicer-Projekt (.3mf) der Gießvariante für den Anycubic i3 Mega S (Düse 0,4, PETG).

Gleiche Teile und Einstellungen wie mp5_guss_p2s.3mf aus bambu_projekte.py, angepasst an den kleineren Drucker:
  - Bett 210 × 210 mm: Schafthälften je auf eine eigene Platte, vorderer Handschutz (206 mm lang) um 45° gedreht.
  - Grundlage Systemprofil 0.20mm Standard @Anycubic i3MegaS (Geschwindigkeiten, Beschleunigung, Retract bleiben),
    Filament Anycubic Generic PETG.
  - "Partial" der vertikalen Schalendicke heißt in Orca ensure_critical_only.
  - Orca übernimmt aus der Liste zum Zusammenfügen weder subtype noch print_params der Teile (alles wird
    normal_part, die Kammern würden mit Infill gefüllt). fix_parts trägt beides danach in die 3MF ein.
  - Die Kommandozeile lässt different_settings_to_system leer. Die Oberfläche lädt dann das Systemprofil
    unverändert (Brim, Skirt, 15 % Crosshatch ...). fix_settings trägt die geänderten Schlüssel ein.

Ergebnis: gehaeuse/orca/mp5_guss_i3megas.3mf, Druckzeit und Filament je Platte in orca/druckzeiten.json.

Aufruf: ORCA_SLICER=/usr/bin/orca-slicer python orca_projekte.py
        (Profile aus ~/.config/OrcaSlicer/system, sonst ORCA_PROFILES auf den Ordner mit Anycubic/ setzen;
        braucht numpy, trimesh, manifold3d)
"""
import json
import math
import os
import re
import sys
import tempfile
import zipfile

import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bambu_projekte as BP  # noqa: E402

OUT = os.path.join(BP.GEH, "orca")

MACHINE = "Anycubic i3 Mega S 0.4 nozzle"
PROCESS = "0.20mm Standard @Anycubic i3MegaS"
FILAMENT = "Anycubic Generic PETG"

GUSS_GLOBAL = {k: v for k, v in BP.GUSS_GLOBAL.items() if k != "curr_bed_type"}
GUSS_GLOBAL.update(ensure_vertical_shell_thickness="ensure_critical_only",
                   adaptive_layer_height="0",           # im Systemprofil an; Kammerdecken brauchen feste 0,2 mm
                   brim_type="no_brim", skirt_loops="0")  # Brim und Skirt ragten bei den Gehäusehälften übers Bett

BED = 210.0
MARGIN = 5.0                                            # Rand zum Bettrand (Skirt liegt 2 mm neben dem Teil)
GAP = 12.0                                              # Abstand der Teile; bei 8 mm Bahnkonflikt im Tree-Support
ROT = {"handschutz_vorn_links": 45.0, "handschutz_vorn_rechts": 45.0}   # Grad um Z, sonst zu lang fürs Bett
# Gehäusehälften 4,5 mm nach hinten: Der Tree-Support an der Vorderkante reicht sonst bis Y 0,2 und liegt auf der
# Reinigungslinie des Startcodes (Y 1–2, X 5–205)
SHIFT_Y = {"gehaeuse_links": 4.5, "gehaeuse_rechts": 4.5}

PLATES = [("Gehäuse links", ["gehaeuse_links"]), ("Gehäuse rechts", ["gehaeuse_rechts"]),
          ("Handschutz vorn links", ["handschutz_vorn_links"]), ("Handschutz vorn rechts", ["handschutz_vorn_rechts"]),
          ("Schaft links", ["schaft_links"]), ("Schaft rechts", ["schaft_rechts"]),
          ("Handschutz hinten, Zwischenring, Magazin", ["handschutz_hinten", "zwischenring", "magazin", "magazin_unterteil"]),
          ("Kleinteile", ["abzug", "nachladehebel", "frontkappe", "linsenhuelse", "tsop_einsatz", "oled_rahmen", "korn",
                          "spannhebel_knauf", "spannhebel_stift"])]


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


def layout(paths):
    """Wie BP.layout, für das kleinere Bett und mit den (gedrehten) Dateien."""
    box = {n: trimesh.load(p).bounds[:, :2] for n, p in paths.items()}
    order = sorted(paths, key=lambda n: -(box[n][1][1] - box[n][0][1]))
    place, x, y, row = {}, 0.0, 0.0, 0.0
    for n in order:
        w, h = box[n][1] - box[n][0]
        if x > 0 and x + w > BED - 2 * MARGIN:
            x, y, row = 0.0, y + row + GAP, 0.0
        place[n] = (x, y)
        x, row = x + w + GAP, max(row, h)
    width = max(place[n][0] + box[n][1][0] - box[n][0][0] for n in paths)
    height = max(place[n][1] + box[n][1][1] - box[n][0][1] for n in paths)
    if width > BED - 2 * MARGIN or height > BED - 2 * MARGIN:
        sys.exit(f"Platte zu klein für {list(paths)}: {width:.1f} × {height:.1f} mm")
    ox, oy = (BED - width) / 2, (BED - height) / 2
    return {n: (ox + place[n][0] - box[n][0][0], oy + place[n][1] - box[n][0][1]) for n in paths}


def assemble_list(tmp):
    plates, idx = [], 0
    for title, names in PLATES:
        src, center = {}, {}
        for name in names:
            src[name] = os.path.join(BP.GUSS if name in BP.CAST else BP.MOD, name + ".stl")
            center[name] = trimesh.load(src[name]).bounds.mean(0)
        paths = {n: rotated(src[n], ROT.get(n, 0), center[n], tmp) for n in names}
        pos = layout(paths)
        objs = []
        for name in names:
            idx += 1
            at = {"pos_x": [pos[name][0]], "pos_y": [pos[name][1] + SHIFT_Y.get(name, 0.0)], "pos_z": [0.0]}
            part = {"path": os.path.abspath(paths[name]), "count": 1, "filaments": [1], "assemble_index": [idx],
                    "subtype": "normal_part", **at}
            mods = []
            if name in BP.CAST:
                blk = rotated(BP.kammer_blocker(name, tmp), ROT.get(name, 0), center[name], tmp)
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


def build(cli, root):
    os.makedirs(OUT, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        files, changed = {}, {}
        for kind, name, extra in (("machine", MACHINE, {}), ("process", PROCESS, GUSS_GLOBAL), ("filament", FILAMENT, {})):
            files[kind] = os.path.join(tmp, f"{kind}.json")
            json.dump(BP.profile(root, kind, name, extra), open(files[kind], "w"), indent=1)
            changed[kind] = differs(BP.profile(root, kind, name, {}), extra)
        lst = os.path.join(tmp, "list.json")
        json.dump(assemble_list(tmp), open(lst, "w"), indent=1)
        proj = os.path.join(OUT, "mp5_guss_i3megas.3mf")
        settings = ["--load-settings", f"{files['machine']};{files['process']}", "--load-filaments", files["filament"]]
        code, log = BP.run(cli, settings + ["--load-assemble-list", lst, "--export-3mf", os.path.basename(proj),
                                            "--outputdir", OUT])
        if code != 0:
            sys.exit(f"Export fehlgeschlagen ({code})\n{log[-2000:]}")
        BP.rename_objects(proj)
        fix_parts(proj)
        fix_settings(proj, changed)
        sliced = os.path.join(tmp, "sliced.3mf")
        code, log = BP.run(cli, [proj, "--slice", "0", "--export-3mf", os.path.basename(sliced), "--outputdir", tmp])
        if code != 0:
            sys.exit(f"Slicen fehlgeschlagen ({code})\n{log[-2000:]}")
        plates = BP.slice_info(sliced)
    for p, (title, names) in zip(plates, PLATES):
        p["name"], p["teile"] = title, names
    report = {"guss": {"platten": plates, "stunden": round(sum(p["stunden"] for p in plates), 1),
                       "gramm": round(sum(p["gramm"] for p in plates))}}
    if os.path.exists(os.path.join(OUT, "result.json")):
        os.remove(os.path.join(OUT, "result.json"))
    json.dump(report, open(os.path.join(OUT, "druckzeiten.json"), "w"), indent=1, ensure_ascii=False)
    print("guss", report["guss"]["stunden"], "h", report["guss"]["gramm"], "g")
    return report


if __name__ == "__main__":
    cli = os.environ.get("ORCA_SLICER", "orca-slicer")
    root = os.path.join(os.environ.get("ORCA_PROFILES", os.path.expanduser("~/.config/OrcaSlicer/system")), "Anycubic")
    build(cli, root)
