"""Bambu-Studio-Projekte (.3mf) für den Druck des MP5-Gehäuses, Drucker Bambu Lab P2S 0.4, Bambu PETG HF.

Zwei Projekte nach gehaeuse/bambu/, je eine Platte pro großem Teil, Kleinteile zusammen:
  mp5_massiv_p2s.3mf  Prototyp ohne Gießfüllung: 6 Wände, 50 % Gyroid (Zwischenring 100 %)
  mp5_guss_p2s.3mf    Gießvariante: Teile + Modifier aus mp5_giessfuellung/ (Einstellungen wie in dessen README)

Die Projekte werden mit der Kommandozeile von Bambu Studio gebaut (Liste zum Zusammenfügen, Profile aus den
Systemprofilen aufgelöst) und anschließend zur Kontrolle geslict; Druckzeit und Filament je Platte landen in
bambu/druckzeiten.json.

Aufruf: BAMBU_STUDIO=/pfad/zu/bambu-studio python bambu_projekte.py
        (AppImage: ./BambuStudio*.AppImage --appimage-extract, dann squashfs-root/AppRun; braucht numpy, trimesh)
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import baugruppe as B  # noqa: E402
import umbau as U  # noqa: E402

GEH = os.path.join(HERE, "..")
MOD = os.path.join(GEH, "mp5_umbau")
GUSS = os.path.join(GEH, "mp5_giessfuellung")
OUT = os.path.join(GEH, "bambu")

MACHINE = "Bambu Lab P2S 0.4 nozzle"
PROCESS = "0.20mm Standard @BBL P2S"
FILAMENT = "Bambu PETG HF @BBL P2S 0.4 nozzle"

COMMON = {
    "curr_bed_type": "Textured PEI Plate",
    "enable_support": "1", "support_type": "tree(auto)",
    "seam_position": "aligned", "ironing_type": "no ironing",
}
MASSIV = dict(COMMON, wall_loops="6", sparse_infill_density="50%", sparse_infill_pattern="gyroid")
GUSS_GLOBAL = dict(COMMON, wall_loops="2", sparse_infill_density="15%", sparse_infill_pattern="grid",
                   outer_wall_line_width="0.42", inner_wall_line_width="0.5", sparse_infill_line_width="0.5",
                   wall_generator="arachne", top_shell_layers="5", top_shell_thickness="1",
                   bottom_shell_layers="3", bottom_shell_thickness="0", infill_combination="1")
CHAMBER = {"bottom_shell_layers": "0", "bottom_shell_thickness": "0", "sparse_infill_pattern": "lightning",
           "sparse_infill_density": "15%"}
HOLLOW = {"sparse_infill_pattern": "lightning", "sparse_infill_density": "15%"}
SOLID_SMALL = {"wall_loops": "6", "sparse_infill_density": "50%", "sparse_infill_pattern": "gyroid"}
ZAPFEN = {"sparse_infill_density": "60%"}

CAST = ["gehaeuse_links", "gehaeuse_rechts", "handschutz_vorn_links", "handschutz_vorn_rechts", "handschutz_hinten",
        "schaft_links", "schaft_rechts"]
# Platten: (Name, Teile); mehrere Teile werden in Reihen ausgelegt (layout)
PLATES = [("Gehäuse links", ["gehaeuse_links"]), ("Gehäuse rechts", ["gehaeuse_rechts"]),
          ("Handschutz vorn links", ["handschutz_vorn_links"]), ("Handschutz vorn rechts", ["handschutz_vorn_rechts"]),
          ("Schaft", ["schaft_links", "schaft_rechts"]),
          ("Handschutz hinten, Zwischenring, Magazin", ["handschutz_hinten", "zwischenring", "magazin", "magazin_unterteil"]),
          ("Kleinteile", ["abzug", "nachladehebel", "frontkappe", "linsenhuelse", "tsop_einsatz", "oled_rahmen", "korn",
                          "spannhebel_knauf", "spannhebel_stift"])]


def profile(root, kind, name, extra):
    """Systemprofil mit aufgelöster Vererbung, dazu eigene Werte."""
    d = json.load(open(os.path.join(root, kind, name + ".json")))
    out = profile(root, kind, d["inherits"], {}) if d.get("inherits") else {}
    out.update(d)
    out.pop("inherits", None)
    out.update(name=name, **{"from": "system"})
    out.update(extra)
    return out


def zapfen_box(tmp):
    """Quader über dem Zapfen des hinteren Handschutzes (Drucklage), für 60 % Infill."""
    gun = {B.key_of(n): np.asarray(m, float) for n, f, m, _ in B.parts() if f is not None and m is not None}
    tm = trimesh.load(os.path.join(MOD, "handschutz_hinten.stl"))
    g = trimesh.transform_points(tm.vertices, gun["handschutz_hinten"])
    v = tm.vertices[g[:, 1] < U.JOINT_Y]
    lo, hi = v.min(0) - 1.0, v.max(0) + 1.0
    box = trimesh.creation.box(bounds=[lo, hi])
    p = os.path.join(tmp, "handschutz_hinten__zapfen.stl")
    box.export(p)
    return p


BED = 256.0
GAP = 10.0


def layout(names):
    """Teile in Reihen auf die Platte legen (ohne Drehen), Gruppe mittig; liefert Verschiebung je Teil."""
    box = {n: trimesh.load(os.path.join(MOD, n + ".stl")).bounds[:, :2] for n in names}
    order = sorted(names, key=lambda n: -(box[n][1][1] - box[n][0][1]))
    place, x, y, row = {}, 0.0, 0.0, 0.0
    for n in order:
        w, h = box[n][1] - box[n][0]
        if x > 0 and x + w > BED - 2 * GAP:
            x, y, row = 0.0, y + row + GAP, 0.0
        place[n] = (x, y)
        x, row = x + w + GAP, max(row, h)
    width = max(place[n][0] + box[n][1][0] - box[n][0][0] for n in names)
    height = max(place[n][1] + box[n][1][1] - box[n][0][1] for n in names)
    if width > BED - 2 * GAP or height > BED - 2 * GAP:
        sys.exit(f"Platte zu klein für {names}")
    ox, oy = (BED - width) / 2, (BED - height) / 2
    return {n: (ox + place[n][0] - box[n][0][0], oy + place[n][1] - box[n][0][1]) for n in names}


def assemble_list(guss, tmp):
    plates = []
    idx = 0
    zap = zapfen_box(tmp) if guss else None
    for title, names in PLATES:
        objs = []
        pos = layout(names)
        for name in names:
            idx += 1
            at = {"pos_x": [pos[name][0]], "pos_y": [pos[name][1]], "pos_z": [0.0]}
            part = {"path": os.path.abspath(os.path.join(MOD, name + ".stl")), "count": 1, "filaments": [1],
                    "assemble_index": [idx], "subtype": "normal_part", **at}
            mods = []
            if guss and name in CAST:
                for zone, params in (("quarzharz", CHAMBER), ("schaum", CHAMBER), ("hohl", HOLLOW)):
                    p = os.path.join(GUSS, f"{name}__{zone}.stl")
                    if os.path.exists(p):
                        mods.append({"path": os.path.abspath(p), "count": 1, "filaments": [1], "assemble_index": [idx],
                                     "subtype": "modifier_part", "print_params": params, **at})
                if name == "handschutz_hinten":
                    mods.append({"path": zap, "count": 1, "filaments": [1], "assemble_index": [idx],
                                 "subtype": "modifier_part", "print_params": ZAPFEN, **at})
            elif name == "zwischenring":
                part["print_params"] = {"sparse_infill_density": "100%"}
            elif guss and name not in CAST:
                part["print_params"] = SOLID_SMALL                  # unverändert wie im massiven Satz
            objs += [part] + mods
        plates.append({"plate_name": title, "need_arrange": False, "objects": objs})
    return {"plates": plates}


def rename_objects(path):
    """Objekte heißen nach dem Zusammenfügen assemble_N: nach dem Teil benennen (Name in Bambu Studio)."""
    with zipfile.ZipFile(path) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]

    def fix(block):
        b = block.group(0)
        part = re.search(r'subtype="normal_part".*?<metadata key="name" value="([^"]+?)(?:_1)?"/>', b, re.S)
        return re.sub(r'(<metadata key="name" value=")assemble_\d+(")', lambda m: m.group(1) + part.group(1) + m.group(2),
                      b, count=1) if part else b
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in items:
            if info.filename == "Metadata/model_settings.config":
                data = re.sub(r"<object .*?</object>", fix, data.decode(), flags=re.S).encode()
            z.writestr(info, data)
    os.replace(tmp, path)


def run(cli, args):
    r = subprocess.run([cli, "--debug", "1"] + args, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def slice_info(path):
    """Druckzeit (h) und Filament (g) je Platte aus einem geslicten 3MF."""
    with zipfile.ZipFile(path) as z:
        txt = z.read("Metadata/slice_info.config").decode()
    out = []
    for plate in re.findall(r"<plate>(.*?)</plate>", txt, re.S):
        meta = dict(re.findall(r'<metadata key="([^"]+)" value="([^"]*)"', plate))
        out.append({"platte": int(meta["index"]), "stunden": round(float(meta["prediction"]) / 3600, 2),
                    "gramm": round(float(meta["weight"]), 1)})
    return out


def build(cli):
    root = os.path.join(os.path.dirname(os.path.realpath(cli)), "resources", "profiles", "BBL")
    if not os.path.isdir(root):
        root = os.path.join(os.path.dirname(os.path.realpath(cli)), "..", "resources", "profiles", "BBL")
    os.makedirs(OUT, exist_ok=True)
    report = {}
    with tempfile.TemporaryDirectory() as tmp:
        for variant, guss, glob in (("massiv", False, MASSIV), ("guss", True, GUSS_GLOBAL)):
            files = {}
            for kind, name, extra in (("machine", MACHINE, {}), ("process", PROCESS, glob), ("filament", FILAMENT, {})):
                files[kind] = os.path.join(tmp, f"{variant}_{kind}.json")
                json.dump(profile(root, kind, name, extra), open(files[kind], "w"), indent=1)
            lst = os.path.join(tmp, f"{variant}_list.json")
            json.dump(assemble_list(guss, tmp), open(lst, "w"), indent=1)
            proj = os.path.join(OUT, f"mp5_{variant}_p2s.3mf")
            settings = ["--load-settings", f"{files['machine']};{files['process']}", "--load-filaments", files["filament"]]
            code, log = run(cli, settings + ["--load-assemble-list", lst, "--export-3mf", os.path.basename(proj),
                                             "--outputdir", OUT])
            if code != 0:
                sys.exit(f"{variant}: Export fehlgeschlagen ({code})\n{log[-2000:]}")
            rename_objects(proj)
            sliced = os.path.join(tmp, f"{variant}_sliced.3mf")
            code, log = run(cli, [proj, "--slice", "0", "--export-3mf", os.path.basename(sliced), "--outputdir", tmp])
            if code != 0:
                sys.exit(f"{variant}: Slicen fehlgeschlagen ({code})\n{log[-2000:]}")
            plates = slice_info(sliced)
            for p, (title, names) in zip(plates, PLATES):
                p["name"], p["teile"] = title, names
            report[variant] = {"platten": plates, "stunden": round(sum(p["stunden"] for p in plates), 1),
                               "gramm": round(sum(p["gramm"] for p in plates))}
            print(variant, report[variant]["stunden"], "h", report[variant]["gramm"], "g")
    for f in os.listdir(OUT):                                   # Ergebnisdatei der Kommandozeile
        if f == "result.json":
            os.remove(os.path.join(OUT, f))
    json.dump(report, open(os.path.join(OUT, "druckzeiten.json"), "w"), indent=1, ensure_ascii=False)
    return report


if __name__ == "__main__":
    cli = os.environ.get("BAMBU_STUDIO")
    if not cli:
        sys.exit("BAMBU_STUDIO auf die bambu-studio-Programmdatei (bzw. squashfs-root/AppRun) setzen")
    build(cli)
