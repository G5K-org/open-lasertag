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
BOARD = [(0, 0), (59.6, 0), (59.6, 18.5), (54.0, 18.5), (54.0, 46.0), (0, 46.0)]
HOLES = [(20.4, 14.8), (42.2, 42.5)]   # M2, ISO 7380
BOSS_D = 3.6             # innerhalb der Kupfer-Sperrfläche (Ø 3,7)
PILOT_D = 1.6            # M2 selbstformend in PLA/PETG
PILOT_DEPTH = 6.0        # unter der Platinenrückseite
# Freiräume für Stecker und Kabel (bx0, by0, bx1, by1)
ZONES = [
    (33.5 - 1, -6.0 - 1, 51.5 + 1, 0),   # Antenne des ESP32-S3
    (-6.4, -1.0, 0, 37.0),              # links: AKKU, LED1, TSOP, ABZUG, NACHL.
    (59.6, -1.0, 67.6, 19.5),           # rechts oben: OLED, GEBER
    (54.0, 20.5, 62.0, 29.0),           # rechts: VIB
    (6.0, 46.0, 55.0, 54.0),            # unten: WS2812, USB, SENSOR, LAUTSPR.
]
# USB-C steht senkrecht auf der Platine (HRO TYPE-C-31-E-17, 6,0 mm hoch): Öffnung in der linken
# Seitenwand für den Steckerkörper, von der Oberkante der Buchse bis nach außen
USB_B = (24.1, 41.0)     # Mitte der Buchse, Platinenkoordinaten
USB_H = 6.0              # Höhe über der Platine
USB_OPEN = (13.0, 7.5)   # Langloch Y x X (Steckerkörper bis 12,4 x 6,5)
# Der Kanal für den Steg zum Schaft (obj_8_8, Rundstab Ø 10) beginnt original bei Y = 141 und läuft
# jetzt in die Tasche. Ein Anschlag dahinter begrenzt ihn; der Steg wird dafür auf STEG_L gekürzt.
STOP = (76.5, 91.0, 160.5, 164.0, 6.0)   # X0, X1, Y0, Y1, halbe Dicke
STEG_L = 100.0 - (STOP[3] - 141.0)


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
    ly, lx = USB_OPEN
    r = lx / 2
    cx, cy = X0 + USB_B[1], Y0 + USB_B[0]
    slot = (m3.CrossSection.circle(r, 48).translate((cx, cy - (ly / 2 - r)))
            + m3.CrossSection.circle(r, 48).translate((cx, cy + (ly / 2 - r)))
            + rect(cx - r, cy - (ly / 2 - r), cx + r, cy + (ly / 2 - r)))
    cut = cut + slab(slot, USB_H - 0.01, 60.0)
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


def steg():
    """Gekürzter Steg Gehäuse <-> Schaft: einer der beiden Rundstäbe Ø 10 x 100 aus obj_8_8."""
    tm = trimesh.load(os.path.join(SRC, "obj_8_8.stl")).split(only_watertight=False)[0]
    bar = m3.Manifold(m3.Mesh(vert_properties=np.asarray(tm.vertices, np.float32),
                              tri_verts=np.asarray(tm.faces, np.uint32)))
    lo, hi = tm.bounds
    keep = m3.Manifold.cube((50.0, 50.0, STEG_L)).translate((lo[0] - 20, lo[1] - 20, lo[2]))
    return bar ^ keep


def build():
    cut, bosses, pilots, stop = pocket_shapes()
    left = load("obj_1_3") - cut + (stop ^ HALF_L)
    right_gun = (load("obj_3_6").transform(np.linalg.inv(np.vstack([TO_RIGHT, [0, 0, 0, 1]]))[:3].tolist())
                 - cut + bosses - pilots + (stop ^ HALF_R))
    right = right_gun.transform(TO_RIGHT)
    return left, right, right_gun, cut

