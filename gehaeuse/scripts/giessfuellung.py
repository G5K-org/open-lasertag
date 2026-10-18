"""Gießfüllung (Variante B, siehe mp5_umbau/GIESSFUELLUNG.md): Modifier-STLs für die Gießkammern.

Die Teile in mp5_umbau/ bleiben unverändert (massiver Druck ohne Füllung). Dieses Skript legt je Teil
Modifier-Volumen in dessen Drucklage ab; zusammen mit dem Teil als ein Objekt mit mehreren Teilen in den
Slicer laden, die Modifier auf „Modifier“ stellen (Einstellungen in mp5_giessfuellung/README.md).

Kammer = alle Punkte des Teils mit mindestens WALL Abstand zu jeder Oberfläche, außer zur Druckbett-Fläche
(= Teilungsfläche bzw. Auflagefläche, dort bleibt die Kammer offen), und von dort über Flanken mit höchstens
45° Überhang erreichbar (beim Gießen liegt die offene Seite oben: Luft steigt an Decken ab 45° heraus,
gedruckt sind 45° ohne Stütze möglich). Damit bleiben automatisch stehen:
Außenhaut, Auflagerand an der Teilung, Röhren um Schächte, Dome um Einschmelzmuttern und Schrauben,
Dämme an offenen Nuten (je WALL).

Zonen: quarzharz / schaum (getrennt durch eine Wand SEP) und hohl (Antennenbereich: geschlossen, nicht gießen).

Ausgabe nach mp5_giessfuellung/: <teil>__<zone>.stl, volumen.json, bilder/*.png (Vorschau)

Aufruf: python giessfuellung.py   (braucht numpy, trimesh, rtree, manifold3d, scipy, scikit-image, shapely, contourpy,
        matplotlib, mapbox-earcut)
        python giessfuellung.py bilder   (nur die Vorschaubilder neu)
"""
import json
import os
import sys

import manifold3d as m3
import numpy as np
import trimesh
from scipy import ndimage
from skimage import draw, measure

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import platine_einbau as P  # noqa: E402
import baugruppe as B  # noqa: E402
import umbau as U  # noqa: E402

SRC = os.path.join(HERE, "..", "mp5_umbau")
OUT = os.path.join(HERE, "..", "mp5_giessfuellung")

H = 0.4                       # Rasterweite (mm)
WALL = 2.0                    # gedruckte Wand um jede Kammer (Außenhaut, Röhren, Dome, Rand an der Teilung)
SEP = 1.5                     # Trennwand zwischen Quarzharz und Schaum
MIN_VOL = 500.0               # kleinere Kammern (mm³) werden nicht gegossen, sondern gedruckt
BELOW = 0.6                   # Modifier reicht so weit unter das Bett (sicher offen ab der ersten Schicht)
DENSITY = {"quarzharz": 1.9, "schaum": 0.1}   # g/cm³

# Antenne des ESP32-S3-WROOM-1 (Platinen-Sperrzone, Gun-Rahmen) + 15 mm: nicht füllen
_ax0, _ay0, _ax1, _ay1 = P.ZONES[0]
ANT_BOX = (P.X0 + _ay0, P.X0 + _ay1, P.Y0 + _ax0, P.Y0 + _ax1, -3.0, 3.0)   # X0, X1, Y0, Y1, Z0, Z1
ANT_CLR = 15.0


def _box_dist(p, b):
    x0, x1, y0, y1, z0, z1 = b
    q = np.maximum(np.stack([x0 - p[:, 0], p[:, 0] - x1, y0 - p[:, 1], p[:, 1] - y1, z0 - p[:, 2], p[:, 2] - z1], 1), 0)
    return np.sqrt((np.maximum(q[:, 0], q[:, 1])) ** 2 + np.maximum(q[:, 2], q[:, 3]) ** 2 + np.maximum(q[:, 4], q[:, 5]) ** 2)


def antenna(p):
    return _box_dist(p, ANT_BOX) < ANT_CLR


# Teil: (Quarzharz-Regel im Gun-Rahmen, Hohl-Regel); der Rest der Kammern wird Schaum
ALL = lambda p: np.ones(len(p), bool)        # noqa: E731
NONE = lambda p: np.zeros(len(p), bool)      # noqa: E731
PARTS = {
    "gehaeuse_links": (ALL, antenna),        # ganz Quarzharz: Griff, Einschmelzmuttern, Zuganker, Stege; keine
    "gehaeuse_rechts": (ALL, antenna),       # Trennwände um einzelne Inseln
    "handschutz_hinten": (lambda p: p[:, 1] < U.JOINT_Y, None),   # Zapfen: Einschmelzmuttern, Muttern der Zuganker
    "handschutz_vorn_links": (NONE, None),
    "handschutz_vorn_rechts": (NONE, None),
    "schaft_links": (ALL, None),             # Hauptballast
    "schaft_rechts": (ALL, None),
}


def load(name):
    tm = trimesh.load(os.path.join(SRC, name + ".stl"))
    tm.merge_vertices()
    return U.to_man(tm), tm.bounds


def occupancy(man, bounds, pad):
    """Belegung auf dem Raster (Zellmitten); z-Index 0 = erste Zelle über dem Bett."""
    lo = np.floor(bounds[0][:2] / H) * H - pad * H
    nx, ny = (np.ceil((bounds[1][:2] - lo) / H).astype(int) + pad)
    nz = int(np.ceil(bounds[1][2] / H))
    occ = np.zeros((nx, ny, nz), bool)
    for k in range(nz):
        layer = np.zeros((nx, ny), bool)
        for ring in man.slice((k + 0.5) * H).to_polygons():
            r = np.asarray(ring)
            ii, jj = draw.polygon((r[:, 0] - lo[0]) / H - 0.5, (r[:, 1] - lo[1]) / H - 0.5, (nx, ny))
            layer[ii, jj] ^= True                           # gerade/ungerade: Löcher heben sich auf
        occ[:, :, k] = layer
    return occ, lo


def reach45(c):
    """Teil von c, der vom Bett aus über Flanken mit höchstens 45° Überhang erreichbar ist."""
    st = ndimage.generate_binary_structure(2, 1)                       # je Schicht H höchstens H seitlich
    r = np.zeros_like(c)
    r[:, :, 0] = c[:, :, 0]
    for k in range(1, c.shape[2]):
        r[:, :, k] = ndimage.binary_dilation(r[:, :, k - 1], st) & c[:, :, k]
    return r


def chambers(occ):
    """Kammer: Abstand >= WALL zu jeder Oberfläche außer dem Bett, vom Bett aus erreichbar (reach45)."""
    m = int(np.ceil(WALL / H)) + 2
    full = np.concatenate([occ[:, :, :m][:, :, ::-1], occ], axis=2)     # am Bett gespiegelt: dort keine Wand
    dist = ndimage.distance_transform_edt(full, sampling=H)[:, :, m:]
    return reach45(dist > WALL + H / 2)


def clean(mask):
    """Dünne Grate weg, zu kleine Kammern drucken statt gießen."""
    mask = ndimage.binary_opening(mask, ndimage.generate_binary_structure(3, 1), iterations=2) & mask
    lab, n = ndimage.label(mask)
    if n == 0:
        return mask
    vol = ndimage.sum(mask, lab, range(1, n + 1)) * H ** 3
    keep = np.zeros(n + 1, bool)
    keep[1:] = vol >= MIN_VOL
    return reach45(keep[lab])


def mesh(mask, lo):
    """Oberfläche der Zellen; unten bis BELOW unter das Bett verlängert."""
    nb = int(round(BELOW / H)) + 1
    vol = np.concatenate([np.repeat(mask[:, :, :1], nb, axis=2), mask], axis=2)
    vol = np.pad(vol, 1).astype(np.float32)
    v, f, _, _ = measure.marching_cubes(vol, 0.5, spacing=(H, H, H))
    v += np.array([lo[0] - 0.5 * H, lo[1] - 0.5 * H, -(nb + 0.5) * H])
    tm = trimesh.Trimesh(v, f)
    if tm.volume < 0:
        tm.invert()
    man = U.to_man(tm)
    if hasattr(man, "simplify"):
        man = man.simplify(0.05)
    return U.to_tm(man)


def build():
    gun = {B.key_of(n): np.asarray(mat, float) for n, f, mat, _ in B.parts() if f is not None and mat is not None}
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".stl"):
            os.remove(os.path.join(OUT, f))
    report = {}
    for name, (rule, hollow) in PARTS.items():
        man, bounds = load(name)
        occ, lo = occupancy(man, bounds, pad=3)
        cham = chambers(occ)
        idx = np.argwhere(cham)
        pts = np.column_stack([lo[0] + (idx[:, 0] + 0.5) * H, lo[1] + (idx[:, 1] + 0.5) * H, (idx[:, 2] + 0.5) * H])
        g = (gun[name][:3, :3] @ pts.T).T + gun[name][:3, 3]              # Drucklage -> Gun-Rahmen
        zone = {k: np.zeros_like(cham) for k in ("quarzharz", "schaum", "hohl")}

        def put(key, sel):
            zone[key][tuple(idx[sel].T)] = True
        hol = hollow(g) if hollow else np.zeros(len(g), bool)
        put("hohl", hol)
        put("quarzharz", rule(g) & ~hol)
        q = zone["quarzharz"]
        sep = ndimage.distance_transform_edt(~q, sampling=H) > SEP if q.any() else np.ones_like(q)
        put("schaum", ~hol)
        zone["schaum"] &= ~q & sep
        if hollow:
            hsep = ndimage.distance_transform_edt(~zone["hohl"], sampling=H) > SEP
            zone["quarzharz"] &= hsep
            zone["schaum"] &= hsep
        report[name] = {"teil_cm3": round(man.volume() / 1000, 1)}
        for key, mask in zone.items():
            mask = clean(mask) if key != "hohl" else mask & ndimage.binary_opening(mask, iterations=2)
            v = mask.sum() * H ** 3 / 1000
            if v < MIN_VOL / 1000:
                continue
            tm = mesh(mask, lo)
            tm.export(os.path.join(OUT, f"{name}__{key}.stl"))
            report[name][key + "_cm3"] = round(float(v), 1)
            if key in DENSITY:
                report[name][key + "_g"] = round(float(v) * DENSITY[key])
        print(name, report[name])
    json.dump(report, open(os.path.join(OUT, "volumen.json"), "w"), indent=1, ensure_ascii=False)
    return report


# ---------------------------------------------------------------- Vorschaubilder
COLOR = {"teil": (0.62, 0.64, 0.67), "quarzharz": (0.80, 0.30, 0.22), "schaum": (0.95, 0.77, 0.15),
         "hohl": (0.25, 0.55, 0.85)}
LABEL = {"quarzharz": "Quarzharz", "schaum": "PU-Schaum", "hohl": "hohl (Antenne)"}


def _view(screen_x, screen_y):
    """Drehung: Zeilen = Bild-x, Bild-y, Richtung zum Betrachter."""
    a, b = np.asarray(screen_x, float), np.asarray(screen_y, float)
    return np.array([a, b, np.cross(a, b)])


def _draw(ax, items, R, ghost=False):
    """Maleralgorithmus: items = [(Trimesh, Farbe, Deckkraft)], Licht schräg von vorn oben."""
    from matplotlib.collections import PolyCollection
    light = np.array([-0.35, 0.55, 0.76])
    polys, cols, depth = [], [], []
    for tm, c, alpha in items:
        tri = tm.triangles @ R.T
        n = tm.face_normals @ R.T
        vis = n[:, 2] > 0                                    # Rückseiten weg
        shade = 0.35 + 0.65 * np.clip(n[vis] @ light, 0, 1)
        polys.append(tri[vis][:, :, :2])
        cols.append(np.column_stack([np.clip(np.outer(shade, c), 0, 1), np.full(vis.sum(), alpha)]))
        depth.append(tri[vis][:, :, 2].mean(1) + (1000.0 if alpha >= 1 and ghost else 0.0))
    polys, cols, depth = np.concatenate(polys), np.concatenate(cols), np.concatenate(depth)
    o = np.argsort(depth)
    ax.add_collection(PolyCollection(polys[o], facecolors=cols[o], edgecolors="none", antialiased=False))
    ax.set_xlim(polys[..., 0].min() - 3, polys[..., 0].max() + 3)
    ax.set_ylim(polys[..., 1].min() - 3, polys[..., 1].max() + 3)
    ax.set_aspect("equal")
    ax.axis("off")


def _preview(tm, factor=0.05):
    man = U.to_man(tm)
    return U.to_tm(man.simplify(factor)) if hasattr(man, "simplify") else tm


def _zones(name):
    out = []
    for key in ("quarzharz", "schaum", "hohl"):
        p = os.path.join(OUT, f"{name}__{key}.stl")
        if os.path.exists(p):
            out.append((key, trimesh.load(p)))
    return out


def _legend(fig, keys):
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=COLOR[k], label=LABEL[k]) for k in keys], loc="lower center", ncol=len(keys),
               frameon=False, fontsize=11)


def images():
    """Je Teil: Gießseite (offene Seite oben, wie beim Gießen) und Durchsicht; dazu Übersicht der Waffe."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    report = json.load(open(os.path.join(OUT, "volumen.json")))
    gun = {B.key_of(n): np.asarray(mat, float) for n, f, mat, _ in B.parts() if f is not None and mat is not None}
    d = os.path.join(OUT, "bilder")
    os.makedirs(d, exist_ok=True)
    below = _view((1, 0, 0), (0, -1, 0))                    # von der Bettseite: Teil umgedreht, offen nach oben
    iso = _view((0.82, 0.57, 0), (-0.25, 0.36, 0.9))        # schräg von oben (Druckseite)
    parts = {}
    for name in PARTS:
        part = _preview(trimesh.load(os.path.join(SRC, name + ".stl")))
        zones = _zones(name)
        parts[name] = (part, zones)
        fig, axs = plt.subplots(1, 2, figsize=(16, 8.5))
        _draw(axs[0], [(part, COLOR["teil"], 1.0)] + [(z, COLOR[k], 1.0) for k, z in zones], below)
        axs[0].set_title("Gießseite (offene Kammern)", fontsize=13)
        _draw(axs[1], [(part, COLOR["teil"], 0.10)] + [(z, COLOR[k], 1.0) for k, z in zones], iso, ghost=True)
        axs[1].set_title("Durchsicht (Kammern im Teil)", fontsize=13)
        r = report[name]
        vol = ", ".join(f"{LABEL[k]} {r[k + '_cm3']:.1f} cm³".replace(".", ",") for k, _ in zones)
        fig.suptitle(f"{name}  –  {vol}", fontsize=15)
        _legend(fig, [k for k, _ in zones])
        fig.tight_layout(rect=(0, 0.04, 1, 0.95))
        fig.savefig(os.path.join(d, name + ".png"), dpi=90)
        plt.close(fig)
        print("Bild", name)
    # Übersicht: Innenseiten der linken und rechten Hälften an ihrem Platz in der Waffe
    fig, axs = plt.subplots(2, 1, figsize=(18, 13))
    for ax, side, R, title in ((axs[0], 1, _view((0, -1, 0), (-1, 0, 0)), "linke Hälften, Innenseite"),
                               (axs[1], -1, _view((0, 1, 0), (-1, 0, 0)), "rechte Hälften, Innenseite")):
        items = []
        for name, (part, zones) in parts.items():
            if name.endswith("_rechts" if side > 0 else "_links"):
                continue
            mats = [(part, COLOR["teil"])] + [(z, COLOR[k]) for k, z in zones]
            for tm, c in mats:
                t = tm.copy()
                t.apply_transform(gun[name])
                if name == "handschutz_hinten":                 # ungeteilt: an der Teilungsebene aufschneiden
                    t = t.slice_plane((0, 0, 0), (0, 0, side), cap=True)
                    if t is None or len(t.faces) == 0:
                        continue
                    if c != COLOR["teil"]:                      # Schnittfläche der Kammer vor die des Teils
                        t.apply_translation((0, 0, -side * 0.3))
                items.append((t, c, 1.0))
        _draw(ax, items, R)
        ax.set_title(title, fontsize=13)
    fig.suptitle("Gießkammern in der Waffe", fontsize=15)
    _legend(fig, ["quarzharz", "schaum", "hohl"])
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(os.path.join(d, "uebersicht.png"), dpi=80)
    plt.close(fig)


if __name__ == "__main__":
    if sys.argv[1:] != ["bilder"]:
        build()
    images()
    print("geschrieben nach", os.path.abspath(OUT))
