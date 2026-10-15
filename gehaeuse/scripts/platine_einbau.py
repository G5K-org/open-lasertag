"""Platinentasche in den MP5-Gehäusehälften (Geometrie für umbau.py).

Gun-Rahmen = Koordinaten von obj_1_3 (linke Hälfte, liegt mit der Teilungsebene auf z=0):
  X = nach unten, Y = nach hinten (Mündung bei Y=30), Z = von der Teilungsebene zur linken Außenseite.
obj_3_6 (rechte Hälfte) ist gespiegelt: x' = 274 - X, y' = Y - 294.85, z' = -Z.

Die Platine liegt mit der Rückseite in der rechten Hälfte, die Bauteile zeigen nach links;
Oberseite der Platine = Teilungsebene. Platinenkoordinaten (bx, by) wie in KiCad:
X = X0 + by, Y = Y0 + bx.

Wird von umbau.py verwendet, das alle Einbauten zusammen erzeugt.
"""
import os
import sys

import manifold3d as m3
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "mp5_toygun_stls")

MIR_X, MIR_Y = 274.0, -294.85  # obj_1_3 -> obj_3_6

# ---------------------------------------------------------------- Platine
X0, Y0 = 76.0, 92.9      # Oberkante / linke Kante der Platine im Gun-Rahmen
T_PCB = 1.6
STANDOFF = 2.5           # Luft unter der Platine (Dome)
DEPTH_R = STANDOFF + T_PCB   # Tasche rechte Hälfte (Platinenrückseite)
DEPTH_L = 6.0            # Tasche linke Hälfte (Bauteile bis 4,85 über der Platine)
CLR = 0.3                # Spiel um die Platinenkontur
BOARD = [(0, -9.0), (18.6, -9.0), (18.6, 0), (59.6, 0), (59.6, 18.5), (54.0, 18.5), (54.0, 26.5), (59.6, 26.5),
         (59.6, 46.0), (0, 46.0)]   # Lasche oben links: Akkuschutz und Ein/Aus; Aussparung rechts nur noch für VIB
HOLES = [(20.4, 14.8), (37.0, 42.5)]   # M2, ISO 7380
BOSS_D = 3.6             # innerhalb der Kupfer-Sperrfläche (Ø 3,7)
PILOT_D = 1.6            # M2 selbstformend in PLA/PETG
PILOT_DEPTH = 6.0        # unter der Platinenrückseite
# Freiräume für Stecker und Kabel (bx0, by0, bx1, by1)
ZONES = [
    (33.5 - 1, -6.0 - 1, 51.5 + 1, 0),   # Antenne des ESP32-S3
    (-6.4, -1.0, 0, 45.5),              # links (vorn, zum Hauptschacht): AKKU, LED/TSOP, WS2812, LAUTSPR.
    (59.6, -1.0, 67.6, 23.0),           # rechts oben: OLED, GEBER (offen zur VIB-Zone: Drehgeberkabel)
    (52.0, 20.5, 67.6, 26.5),           # rechts (hinten, zum Motorschacht): VIB, Drehgeber
    (59.6, 26.5, 67.6, 40.5),           # rechts: SENSOR (Weste), Kabel nach oben in die VIB-Zone
    (6.0, 46.0, 55.0, 54.0),            # unten (Kanal zum Abzugsschalter): ABZUG, NACHL.
    (41.5, 45.5, 53.5, 55.0),           # microSD-Karte (J7), steht ~8,6 mm über die Unterkante
]
# USB-C steht senkrecht auf der Platine (hanxia HX-TYPE-C 16P 180 LT H10.5, 10,5 mm hoch) und reicht durch
# die linke Seitenwand bis außen: Durchbruch eng um das Blechgehäuse, außen eine flache Mulde auf Höhe der
# Buchsenoberkante (Auflage für den Stecker), die Buchse schließt bündig mit der Mulde ab
USB_B = (28.2, 41.0)     # Mitte der Buchse, Platinenkoordinaten
USB_H = 10.5             # Oberkante der Buchse über der Platine = Boden der Mulde
USB_SHELL = (9.3, 3.5)   # Durchbruch Y x X (Blechgehäuse 8,94 x 3,16)
USB_OPEN = (14.0, 8.5)   # Mulde Y x X (Steckerkörper bis 12,4 x 6,5)
# Der Kanal für den Steg zum Schaft (obj_8_8, Rundstab Ø 10) beginnt original bei Y = 141 und läuft
# jetzt in die Tasche. Ein Anschlag dahinter begrenzt ihn; der Steg wird dafür auf STEG_L gekürzt.
STOP = (76.5, 91.0, 160.5, 164.0, 6.0)   # X0, X1, Y0, Y1, halbe Dicke
STEG_L = 100.0 - (STOP[3] - 141.0)


# Externe Antenne (Variante mit ESP32-S3-WROOM-1U): RP-SMA-Buchse quer durch die linke Seitenwand über dem
# Modul, Knick-Stabantenne außen senkrecht nach oben neben Kimme und Korn, Pigtail RP-SMA -> U.FL innen
ANT = (71.5, 134.0)          # Achse der Buchse (X, Y), entlang +Z
ANT_WALL = (9.0, 11.5)       # Wand an der Buchse: Innenseite, Planfläche außen (Z)
ANT_SPOT = 14.0              # Planfläche Ø (Mutter SW 8, Steckschlüssel)
ANT_HOLE = 6.6               # Durchgang Gewinde 1/4"-36
ANT_INNER = 11.0             # Freiraum innen um den Sechskant der Buchse
ANT_LOOP = (66.5, 76.0, 119.0, 148.5)   # Raum für die Kabelschlaufe in der linken Tasche (X0, X1, Y0, Y1)
UFL = (78.76, 141.4, 2.7)    # U.FL des WROOM-1U: Mitte, Kabelachse des Steckers (Z)
ANT_ROD = (130.0, 10.0, 8.0)   # Stab ab Gelenkmitte: Länge, Ø unten, Ø oben (Linx ANT-2.4-CW-HWR-RPS, 142 hoch)


def rect(x0, y0, x1, y1):
    return m3.CrossSection([[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]])


def to_gun(cs):
    """Querschnitt in Platinenkoordinaten -> Gun-Rahmen (X = X0 + by, Y = Y0 + bx)."""
    pts = []
    for poly in cs.to_polygons():
        p = np.asarray(poly)[:, ::-1] + (X0, Y0)
        pts.append(p[::-1])            # Vertauschen dreht den Umlaufsinn -> zurückdrehen
    return m3.CrossSection(pts)


def slab(cs, z0, z1):
    return cs.extrude(z1 - z0).translate((0, 0, z0))


def pocket_shapes():
    board = m3.CrossSection([BOARD]).offset(CLR, m3.JoinType.Miter)
    zones = rect(*ZONES[0])
    for z in ZONES[1:]:
        zones = zones + rect(*z)
    left = to_gun(m3.CrossSection([BOARD]).offset(1.0, m3.JoinType.Round) + zones)
    right = to_gun(board + zones)
    cut = slab(left, -0.01, DEPTH_L) + slab(right, -DEPTH_R, 0.01)
    cx, cy = X0 + USB_B[1], Y0 + USB_B[0]

    def obround(ly, lx):
        r = lx / 2
        return (m3.CrossSection.circle(r, 48).translate((cx, cy - (ly / 2 - r)))
                + m3.CrossSection.circle(r, 48).translate((cx, cy + (ly / 2 - r)))
                + rect(cx - r, cy - (ly / 2 - r), cx + r, cy + (ly / 2 - r)))
    cut = cut + slab(obround(*USB_SHELL), DEPTH_L - 0.01, 60.0) + slab(obround(*USB_OPEN), USB_H, 60.0)
    bosses = None
    pilots = None
    for hx, hy in HOLES:
        cx, cy = X0 + hy, Y0 + hx
        b = m3.Manifold.cylinder(STANDOFF + 0.01, BOSS_D / 2, BOSS_D / 2, 48).translate((cx, cy, -DEPTH_R - 0.005))
        p = m3.Manifold.cylinder(PILOT_DEPTH + 1, PILOT_D / 2, PILOT_D / 2, 24).translate((cx, cy, -T_PCB - PILOT_DEPTH))
        bosses = b if bosses is None else bosses + b
        pilots = p if pilots is None else pilots + p
    x0, x1, y0, y1, h = STOP
    stop = m3.Manifold.cube((x1 - x0, y1 - y0, 2 * h)).translate((x0, y0, -h))
    return cut, bosses, pilots, stop


def load(name):
    tm = trimesh.load(os.path.join(SRC, name + ".stl"))
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(tm.vertices, np.float32),
                               tri_verts=np.asarray(tm.faces, np.uint32)))


def save(man, path):
    mesh = man.to_mesh()
    trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts).export(path)


# Gun-Rahmen -> obj_3_6: x' = 274 - X, y' = Y - 294.85, z' = -Z
TO_RIGHT = [[-1, 0, 0, MIR_X], [0, 1, 0, MIR_Y], [0, 0, -1, 0]]
HALF_L = m3.Manifold.cube((1000, 1000, 100)).translate((-500, -500, 0))
HALF_R = HALF_L.translate((0, 0, -100))


def steg(length=STEG_L):
    """Gekürzter Steg (Standard: Gehäuse <-> Schaft): einer der beiden Rundstäbe Ø 10 x 100 aus obj_8_8."""
    tm = trimesh.load(os.path.join(SRC, "obj_8_8.stl")).split(only_watertight=False)[0]
    bar = m3.Manifold(m3.Mesh(vert_properties=np.asarray(tm.vertices, np.float32),
                              tri_verts=np.asarray(tm.faces, np.uint32)))
    lo, hi = tm.bounds
    keep = m3.Manifold.cube((50.0, 50.0, length)).translate((lo[0] - 20, lo[1] - 20, lo[2]))
    return bar ^ keep


def _zcyl(d, z0, z1, x=None, y=None, seg=64):
    x, y = ANT if x is None else (x, y)
    return m3.Manifold.cylinder(z1 - z0, d / 2, d / 2, seg).translate((x, y, z0))


def _zhex(af, z0, z1):
    return m3.Manifold.cylinder(z1 - z0, af / np.sqrt(3), af / np.sqrt(3), 6).translate((ANT[0], ANT[1], z0))


def antenna_cut():
    """Planfläche außen, Durchgang, Freiraum für Sechskant und Kabelschlaufe innen (Gun-Rahmen, linke Hälfte)."""
    zi, zo = ANT_WALL
    x0, x1, y0, y1 = ANT_LOOP
    loop = m3.Manifold.cube((x1 - x0, y1 - y0, DEPTH_L + 0.01)).translate((x0, y0, -0.01))
    return (_zcyl(ANT_SPOT, zo, 60.0) + _zcyl(ANT_HOLE, zi - 0.01, zo + 0.01)
            + _zcyl(ANT_INNER, DEPTH_L - 0.01, zi) + loop)


def _ellipse_coil(c, a, z0, z1, t0, t1, n=120):
    t = np.linspace(t0, t1, n)
    return [(c[0] + a[0] * np.cos(u), c[1] + a[1] * np.sin(u), z0 + (z1 - z0) * (u - t0) / (t1 - t0)) for u in t]


def pigtail_path():
    """Kabelachse des Pigtails (Linx CSI-RGFB-100-UFFR, 100 mm): Buchse -> Bogen -> Schlaufe vor der Buchse
    -> U.FL."""
    x, y = ANT
    zb = ANT_WALL[0] - 5.5                                   # Ende der Crimphülse
    r = 2.5
    bend = [(x, y - r + r * np.cos(a), zb - r * np.sin(a)) for a in np.linspace(0, np.pi / 2, 10)]
    coil = _ellipse_coil((71.0, 125.6), (3.0, 5.8), 1.0, 3.4, np.pi / 2, 2 * np.pi * 2)
    return bend + coil + [(75.2, 131.0, 2.4), (75.2, 139.0, 2.7), (UFL[0] - 1.6, UFL[1], UFL[2])]


def antenna_parts():
    """Kaufteile im Gun-Rahmen: Buchse mit Mutter, Antenne geklappt (Stab nach oben, -X), Pigtail."""
    zi, zo = ANT_WALL
    jack = (_zhex(8.0, zi - 1.8, zi) + _zcyl(6.35, zi, zi + 9.5) + _zcyl(4.5, zi - 5.5, zi - 1.8)
            + _zcyl(10.0, zo, zo + 0.5) + _zhex(8.0, zo + 0.5, zo + 2.5))
    zc = zo + 2.5                                            # Überwurf der Antenne liegt an der Mutter
    hinge_z = zc + 12.0
    l, d0, d1 = ANT_ROD
    rod = m3.Manifold.cylinder(l - d1 / 2, d0 / 2, d1 / 2, 48)
    rod = rod + m3.Manifold.sphere(d1 / 2, 32).translate((0, 0, l - d1 / 2))
    rod = rod.rotate((0, -90, 0)).translate((ANT[0], ANT[1], hinge_z))          # lokale z -> -X
    ant = (_zcyl(9.0, zc, zc + 7.0) + _zcyl(10.0, zc + 7.0, hinge_z)
           + m3.Manifold.cylinder(10.0, 5.0, 5.0, 48).rotate((-90, 0, 0)).translate((ANT[0], ANT[1] - 5.0, hinge_z))
           + rod)
    pts = pigtail_path()
    cable = None
    for a, b in zip(pts, pts[1:]):
        s = m3.Manifold.sphere(0.56, 12)
        c = m3.Manifold.batch_hull([s.translate(a), s.translate(b)])
        cable = c if cable is None else cable + c
    ufl = m3.Manifold.cube((3.2, 3.0, 1.4)).translate((UFL[0] - 1.6, UFL[1] - 1.5, UFL[2] - 0.7))
    out = {}
    for k, man in (("Antennenbuchse RP-SMA", jack), ("Antenne 2,4 GHz", ant), ("Pigtail RP-SMA U.FL", cable + ufl)):
        mm = man.to_mesh()
        out[k] = trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts)
    return out


def pigtail_length():
    p = np.asarray(pigtail_path())
    return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())


def build():
    cut, bosses, pilots, stop = pocket_shapes()
    left = load("obj_1_3") - cut + (stop ^ HALF_L)
    right_gun = (load("obj_3_6").transform(np.linalg.inv(np.vstack([TO_RIGHT, [0, 0, 0, 1]]))[:3].tolist())
                 - cut + bosses - pilots + (stop ^ HALF_R))
    right = right_gun.transform(TO_RIGHT)
    return left, right, right_gun, cut

