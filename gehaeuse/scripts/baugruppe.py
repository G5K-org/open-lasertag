"""Baugruppe: alle Gehäuseteile, Stege, Magazin und die bestückte Platine an ihrem Platz.

Gun-Rahmen wie in platine_einbau.py (Koordinaten von obj_1_3): X nach unten, Y nach hinten,
Z zur linken Außenseite, mm. Die Lage der Teile folgt aus ihren Passungen:
  - Zwischenring obj_5_5 und Handschutz/Schalldämpfer obj_10_2: Profil (Ø 49,4 / 46,6 mit Rohr oben)
    und Tropfenkanal des vorderen Stegs fluchten mit der Vorderseite des Gehäuses (Y = 30)
  - Schafthälften obj_4_7 / obj_2_4: Kanal des hinteren Stegs fluchtet mit dem Gehäusekanal,
    Anlage an der Gehäuserückseite
  - Magazin obj_6_9: oberer Teil im Magazinschacht (22,6 mm breit), Rücken an der Schachtrückwand,
    unteres Ende nach vorn gebogen
  - Korn obj_7_1: Steg im Schlitz vorn oben auf dem Handschutz
  - Spannhebel: Stift obj_11_12 im Loch der linken Mulde, Knauf obj_9_10 außen darauf
  - Platine: wie in platine_einbau.py (X = X0 + by, Y = Y0 + bx, Oberseite in der Teilungsebene)

Ausgabe: baugruppe/mp5_baugruppe.glb (Meter, y oben, Mündung in +x) und baugruppe/mp5_baugruppe.3mf (mm).

Aufruf: python baugruppe.py   (braucht numpy, trimesh, manifold3d, kicad-cli)
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import platine_einbau as P  # noqa: E402

SRC = P.SRC
MOD = os.path.join(HERE, "..", "mp5_umbau")
OUT = os.path.join(HERE, "..", "baugruppe")
PCB = os.path.join(HERE, "..", "..", "kicad", "waffe_elektronik", "waffe_elektronik.kicad_pcb")

BLACK = (40, 40, 42, 255)
DARK = (70, 72, 76, 255)
STEEL = (150, 150, 155, 255)
YELLOW = (230, 190, 40, 255)

Y_FRONT = 30.0      # Vorderseite Gehäuse
Y_REAR = 211.1      # Rückseite Gehäuse (oberer Teil)
RING_L = 20.9       # Länge Zwischenring obj_5_5
X_AXIS = 79.52      # Mitte Rohr/Handschutz (Ø 49,4 an der Vorderseite)
X_REAR_BAR = 82.25  # Mitte hinterer Stegkanal
X_FRONT_BAR = 71.07  # Mitte vorderer Stegkanal (Tropfenkanal X 63,5..76,5, rund unten Ø 10,9)


def m4(rot, src, dst):
    """Matrix für: Punkt p -> rot @ (p - src) + dst."""
    m = np.eye(4)
    m[:3, :3] = rot
    m[:3, 3] = np.asarray(dst, float) - np.asarray(rot) @ np.asarray(src, float)
    return m


def rot(cols):
    """Rotation aus den Bildern der lokalen x-, y-, z-Achse (Spalten)."""
    r = np.array(cols, float).T
    assert abs(np.linalg.det(r) - 1) < 1e-6, np.linalg.det(r)
    return r


def load(path):
    return trimesh.load(path, force="mesh")


MAG_TILT = 12.0     # Neigung des Magazinschachts gegen X (Grad), oben nach hinten
MAG_TOP = 86.0      # Oberkante Magazin = Decke des Schachts
MAG_REAR = (100.0, 78.5)   # Punkt (X, Y), durch den die Rückseite des Magazins läuft


def magazine():
    """Lage des Magazins aus seinen Querschnitten (gedruckt schräg und gebogen).
    Neigung und Lage aus einer Suche mit minimaler Überschneidung; voll eingesteckt bleibt nur die
    Mittelrippe hinten im Schacht (Z ±3,6) im Magazinrücken."""
    m = load(os.path.join(SRC, "obj_6_9.stl"))

    def centre(z):
        s = m.section([0, 0, 1], [0, 0, z])
        p, t = s.to_2D()
        q = max(p.polygons_full, key=lambda q: q.area)
        return (t @ np.r_[np.array(q.centroid.coords[0]), 0, 1])[:3]

    a = centre(140) - centre(110)                 # Achse oben (im Schacht)
    a /= np.linalg.norm(a)
    u = np.array([a[0], a[1], 0.0])
    u -= (u @ a) * a
    u /= np.linalg.norm(u)
    b = centre(40) - centre(10)
    b /= np.linalg.norm(b)
    if (b - a) @ u > 0:                           # unteres Ende soll nach vorn (-Y) zeigen
        u = -u
    th = np.radians(MAG_TILT)
    ag = np.array([-np.cos(th), np.sin(th), 0.0])     # Achse nach oben
    ug = np.array([-np.sin(th), -np.cos(th), 0.0])    # nach vorn
    r = np.column_stack([ag, ug, np.cross(ag, ug)]) @ np.linalg.inv(np.column_stack([a, u, np.cross(a, u)]))
    v = (r @ m.vertices.T).T
    top = v @ ag
    shift = -ag * top.max()                       # Oberkante in den Ursprung
    rear = ((v + shift) @ -ug)[top > top.max() - 40].max()
    shift = shift + ug * rear                     # Rückseite durch den Ursprung
    shift[2] -= (v[:, 2].max() + v[:, 2].min()) / 2
    p = np.array([MAG_REAR[0], MAG_REAR[1], 0.0])
    shift = shift + p + ag * ((p[0] - MAG_TOP) / np.cos(th))
    mat = np.eye(4)
    mat[:3, :3] = r
    mat[:3, 3] = shift
    return mat


def board(tmp):
    glb = os.path.join(tmp, "board.glb")
    subprocess.run(["kicad-cli", "pcb", "export", "glb", "--subst-models", "-o", glb, PCB],
                   check=True, capture_output=True)
    scene = trimesh.load(glb)
    # glTF der Platine: x = bx, y = Höhe über der Rückseite, z = by (m)
    s = np.diag([1000.0, 1000.0, 1000.0, 1.0])
    g = m4(rot([[0, 1, 0], [0, 0, 1], [1, 0, 0]]), (0, 0, 0), (P.X0, P.Y0, -P.T_PCB))
    return scene, g @ s


# Eindeutige Teilenamen: Schlüssel = Dateiname in mp5_umbau/ (ohne .stl), Wert = Name in der Baugruppe
NAMES = {
    "gehaeuse_links": "Gehäuse links", "gehaeuse_rechts": "Gehäuse rechts",
    "zwischenring": "Zwischenring", "handschutz_hinten": "Handschutz hinten",
    "handschutz_vorn": "Handschutz vorn mit Schalldämpfer", "frontkappe": "Frontkappe",
    "linsenhuelse": "Linsenhülse", "tsop_einsatz": "TSOP-Einsatz", "korn": "Korn",
    "spannhebel_stift": "Spannhebel Stift", "spannhebel_knauf": "Spannhebel Knauf",
    "schaft_links": "Schaft links", "schaft_rechts": "Schaft rechts", "oled_rahmen": "OLED-Rahmen",
    "steg_vorn_100mm": "Steg vorn (Rundstab 100 mm)", "steg_hinten_77mm": "Steg hinten (Rundstab 77 mm)",
    "magazin": "Magazin", "magazin_unterteil": "Magazin Unterteil", "abzug": "Abzug", "platine": "Platine",
}
# Herkunft im Originalsatz (mp5_toygun_stls)
ORIGINAL = {"gehaeuse_links": "obj_1_3", "gehaeuse_rechts": "obj_3_6", "zwischenring": "obj_5_5",
            "handschutz_hinten": "obj_10_2", "handschutz_vorn": "obj_10_2", "korn": "obj_7_1",
            "spannhebel_stift": "obj_11_12", "spannhebel_knauf": "obj_9_10", "schaft_links": "obj_4_7",
            "schaft_rechts": "obj_2_4", "steg_vorn_100mm": "obj_8_8", "steg_hinten_77mm": "obj_8_8",
            "magazin": "obj_6_9"}


def parts():
    """(Name, Datei, Matrix in den Gun-Rahmen, Farbe)."""
    to_right = np.linalg.inv(np.vstack([P.TO_RIGHT, [0, 0, 0, 1]]))
    rear_ref = load(os.path.join(SRC, "obj_4_7.stl")).vertices[:, 1].min()
    rear_ref_r = load(os.path.join(SRC, "obj_2_4.stl")).vertices[:, 1].min()
    n_sight = np.array([0, 0.987, 0.16]); n_sight /= np.linalg.norm(n_sight)
    a_sight = np.cross([1, 0, 0], n_sight)        # Ringachse
    knob_axis = np.array([-0.385, 0.923, 0.0]); knob_axis /= np.linalg.norm(knob_axis)
    y_hg = Y_FRONT - RING_L                       # Rückseite Handschutz
    hg = m4(rot([[0, 0, 1], [-1, 0, 0], [0, -1, 0]]), (200.27, 60.73, 0), (X_AXIS, y_hg, 0))
    N = NAMES
    out = [
        (N["gehaeuse_links"], mod("gehaeuse_links"), np.eye(4), DARK),
        (N["gehaeuse_rechts"], mod("gehaeuse_rechts"), to_right, DARK),
        (N["zwischenring"], mod("zwischenring"),
         m4(rot([[0, 0, -1], [1, 0, 0], [0, -1, 0]]), (37.7, -182.72, 0), (X_AXIS, Y_FRONT, 0)), BLACK),
        (N["handschutz_vorn"], mod("handschutz_vorn"), hg, BLACK),
        (N["handschutz_hinten"], mod("handschutz_hinten", None), hg, BLACK),
        (N["korn"], mod("korn"), _sight_matrix(n_sight, a_sight, y_hg), BLACK),
        (N["spannhebel_stift"], mod("spannhebel_stift"), _rod_matrix(y_hg), STEEL),
        (N["spannhebel_knauf"], mod("spannhebel_knauf"), _knob_matrix(knob_axis, y_hg), BLACK),
        (N["schaft_links"], mod("schaft_links"),
         m4(np.eye(3), (374.2, rear_ref, 0), (X_REAR_BAR, Y_REAR, 0)), BLACK),
        (N["schaft_rechts"], mod("schaft_rechts"),
         m4(rot([[-1, 0, 0], [0, 1, 0], [0, 0, -1]]), (507.3, rear_ref_r, 0), (X_REAR_BAR, Y_REAR, 0)), BLACK),
        (N["steg_vorn_100mm"], None, None, STEEL),
        (N["steg_hinten_77mm"], None, None, STEEL),
        (N["magazin"], mod("magazin"), magazine(), BLACK),
    ] + new_parts()
    return [p for p in out if p[1] is not None or p[0].startswith("Steg")]


def key_of(name):
    return next(k for k, v in NAMES.items() if v == name)


def mod(key, fallback=""):
    """Teil aus mp5_umbau (gleiche Drucklage wie das Original), sonst das Original."""
    p = os.path.join(MOD, key + ".stl")
    if os.path.exists(p):
        return p
    return ORIGINAL.get(key) if fallback == "" else fallback


NEW = {"abzug": DARK, "linsenhuelse": STEEL, "frontkappe": BLACK, "magazin_unterteil": BLACK,
       "oled_rahmen": BLACK, "tsop_einsatz": BLACK}


def new_parts():
    """Neue Teile aus umbau.py: Drucklage + Matrix aus lage.json."""
    path = os.path.join(MOD, "lage.json")
    if not os.path.exists(path):
        return []
    lage = json.load(open(path))
    return [(NAMES[k], os.path.join(MOD, k + ".stl"), np.array(m), NEW[k]) for k, m in lage.items() if k in NEW]


def _hg_to_gun(p, y_hg):
    """Punkt im Handschutz (obj_10_2) -> Gun-Rahmen."""
    return np.array([X_AXIS - (p[1] - 60.73), y_hg - p[2], p[0] - 200.27])


def _sight_matrix(n, a, y_hg):
    """Steg-Unterseite (Normale n) zeigt nach unten (+X) in den Schlitz oben am Handschutz,
    Ringachse nach vorn (-Y); der Ring liegt auf dem Rohr auf."""
    r = np.column_stack([[1, 0, 0], [0, -1, 0], [0, 0, -1]]) @ np.linalg.inv(np.column_stack([n, a, np.cross(n, a)]))
    stem = np.array([82.51, -216.77, 6.23])       # Mitte der Steg-Unterseite
    slot = _hg_to_gun((200.27, 92.8, (127.67 + 135.81) / 2), y_hg)   # Schlitz, Oberkante Rohr
    mat = m4(r, stem, slot)
    v = trimesh.transform_points(load(os.path.join(SRC, "obj_7_1.stl")).vertices, mat)
    ring = np.abs(v[:, 2]) > 5.0                  # Ring seitlich vom Steg
    mat[0, 3] += slot[0] - v[ring, 0].max()       # Ring unten auf Oberkante Rohr
    return mat


# Loch des Spannhebels in der linken Mulde: schräg nach oben außen, Ø 2,4, etwa 6 tief
HOLE_BOTTOM = (201.0, 83.0, 74.03)                # im Handschutz
HOLE_DIR = np.array([0.819, 0.573, 0.0])          # im Handschutz, nach außen


def _hole(y_hg):
    d = np.array([-HOLE_DIR[1], 0.0, HOLE_DIR[0]])    # Richtung im Gun-Rahmen
    return _hg_to_gun(HOLE_BOTTOM, y_hg), d / np.linalg.norm(d)


def _rod_matrix(y_hg):
    """Stift (Ø 2, 16 lang, liegt schräg in der xy-Ebene) bis zum Grund im Loch."""
    bottom, dg = _hole(y_hg)
    d = np.array([84.98 - 68.95, -263.44 + 275.27, 0.0])
    d /= np.linalg.norm(d)
    e = np.array([0, 0, 1.0])
    r = np.column_stack([dg, [0, -1, 0], np.cross(dg, [0, -1, 0])]) @ np.linalg.inv(np.column_stack([d, e, np.cross(d, e)]))
    centre = np.array([(68.95 + 84.98) / 2, (-275.27 - 263.44) / 2, 1.015])
    return m4(r, centre, bottom + 8.0 * dg)


def _knob_matrix(axis, y_hg):
    """Knauf auf dem herausstehenden Stiftende, Lochachse auf der Stiftachse."""
    bottom, dg = _hole(y_hg)
    z = np.array([0, 0, 1.0])
    r = np.column_stack([-dg, [0, 1, 0], np.cross(-dg, [0, 1, 0])]) @ np.linalg.inv(np.column_stack([axis, z, np.cross(axis, z)]))
    face = np.array([110.7, -248.4, 3.4])         # Lochachse an der stiftseitigen Fläche
    return m4(r, face, bottom + 7.5 * dg)         # 0,5 vor der Oberfläche der Mulde


def bar(length, x, y0):
    """Steg (Rundstab Ø 10 aus obj_8_8, ggf. gekürzt) entlang +Y ab y0, Achse bei (x, 0)."""
    if length < 100.0:
        mm = P.steg().to_mesh()
        b = trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts)
    else:
        b = load(os.path.join(SRC, "obj_8_8.stl")).split(only_watertight=False)[0]
    lo, hi = b.bounds
    c = (lo + hi) / 2
    b.apply_transform(m4(rot([[0, 0, 1], [1, 0, 0], [0, 1, 0]]), (c[0], c[1], lo[2]), (x, y0, 0)))
    return b


def main():
    os.makedirs(OUT, exist_ok=True)
    # Ausgaberahmen: x = Mündung (-Y), y = oben (-X), z = rechts (-Z); Meter
    view = np.array([[0, -1, 0, 0], [-1, 0, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1.0]])
    scene = trimesh.Scene()
    mm_scene = trimesh.Scene()
    for name, src, mat, color in parts():
        if name.startswith("Steg vorn"):
            mesh = bar(100.0, X_FRONT_BAR, Y_FRONT + 34.4 - 100.0)
        elif name.startswith("Steg hinten"):
            mesh = bar(P.STEG_L, X_REAR_BAR, P.STOP[3])
        else:
            mesh = load(src if os.path.isabs(src) else os.path.join(SRC, src + ".stl"))
            mesh.apply_transform(mat)
        mesh.visual = trimesh.visual.ColorVisuals(mesh, face_colors=color)
        mm_scene.add_geometry(mesh.copy(), node_name=name, geom_name=name)
        m = mesh.copy()
        m.apply_transform(view)
        m.apply_scale(0.001)
        scene.add_geometry(m, node_name=name, geom_name=name)
    with tempfile.TemporaryDirectory() as tmp:
        bscene, g = board(tmp)
        pcb = []
        for node in bscene.graph.nodes_geometry:
            t, gname = bscene.graph[node]
            geo = bscene.geometry[gname].copy()
            geo.apply_transform(g @ t)
            pcb.append(trimesh.Trimesh(geo.vertices, geo.faces))
            geo.apply_transform(view)
            geo.apply_scale(0.001)
            scene.add_geometry(geo, node_name="Platine/" + node, geom_name="Platine/" + gname)
    pcb = trimesh.util.concatenate(pcb)          # im 3MF ein Objekt statt ~4400 Einzelteile
    pcb.visual = trimesh.visual.ColorVisuals(pcb, face_colors=(30, 110, 50, 255))
    mm_scene.add_geometry(pcb, node_name="Platine", geom_name="Platine")
    scene.export(os.path.join(OUT, "mp5_baugruppe.glb"))
    mm_scene.export(os.path.join(OUT, "mp5_baugruppe.3mf"))
    print("geschrieben nach", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
