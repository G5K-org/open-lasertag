"""3D models for JST PH side-entry SMD connectors (S2B/S3B-PH-SM4-TB).

KiCad ships the footprints but no models. Outline and pads follow the KiCad
footprints (F.Fab), the height follows the KiCad model of the through-hole
side-entry PH (S*B-PH-K, 4.85 mm).

    freecadcmd scripts/gen_3d_jst_ph_sm4.py

Writes ../3dmodels/<name>.step (geometry, for MCAD) and <name>.wrl (colours,
for renders; KiCad finds the .step next to it for STEP export).
Coordinates: footprint origin, model Y = -footprint y, Z up, mm.
"""
import os

import Part
from FreeCAD import Vector

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "3dmodels")
PITCH = 2.0
H = 4.85            # housing height
Y_BACK, Y_FRONT = -1.6, 4.4   # main body, footprint y; mating face at Y_FRONT
Y_EAR = -3.2        # side walls reach further back

NYLON = (0.93, 0.91, 0.82)
METAL = (0.84, 0.84, 0.80)


def box(x0, x1, y0, y1, z0, z1):
    """Box from footprint coordinates (y flipped for the model)."""
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, Vector(x0, -y1, z0))


def connector(n):
    half = PITCH * (n - 1) / 2
    xb = half + 2.15            # main body half width (fab: 3.15 for 2 pins)
    xe = half + 2.95            # side walls (fab: 3.95)

    housing = box(-xb, xb, Y_BACK, Y_FRONT, 0.0, H)
    for s in (-1, 1):
        housing = housing.fuse(box(min(s * xb, s * xe), max(s * xb, s * xe), Y_EAR, Y_FRONT, 0.0, H))
    # mating cavity from the front face, with the latch slot on top
    cav = box(-(half + 1.25), half + 1.25, Y_BACK + 1.0, Y_FRONT + 0.1, 0.8, H - 0.7)
    latch = box(-1.0, 1.0, Y_FRONT - 2.2, Y_FRONT + 0.1, H - 0.8, H + 0.1)
    housing = housing.cut(cav).cut(latch).removeSplitter()

    metal = []
    for i in range(n):
        x = -half + i * PITCH
        metal.append(box(x - 0.32, x + 0.32, Y_BACK + 1.0, Y_FRONT - 1.2, 2.0, 2.64))   # contact in cavity
        metal.append(box(x - 0.32, x + 0.32, Y_BACK - 0.25, Y_BACK + 1.0, 0.0, 2.64))   # through back wall
        metal.append(box(x - 0.32, x + 0.32, -4.3, Y_BACK - 0.25, 0.0, 0.2))            # foot on pad
    for s in (-1, 1):  # solder tabs on the MP pads
        xm = s * (half + 2.35)
        metal.append(box(xm - 0.6, xm + 0.6, 1.4, 4.3, 0.0, 0.2))
        metal.append(box(min(s * xe, s * (xe - 0.2)), max(s * xe, s * (xe - 0.2)), 1.4, 4.3, 0.0, 2.5))
    pins = metal[0]
    for m in metal[1:]:
        pins = pins.fuse(m)
    return housing, pins.removeSplitter()


def write_wrl(path, parts):
    """VRML 2.0 in KiCad units (1 unit = 2.54 mm)."""
    k = 1 / 2.54
    with open(path, "w") as f:
        f.write("#VRML V2.0 utf8\n")
        for shape, (r, g, b) in parts:
            verts, tris = shape.tessellate(0.02)
            f.write("Shape {\n  appearance Appearance { material Material {\n")
            f.write(f"    diffuseColor {r} {g} {b} specularColor 0.2 0.2 0.2 shininess 0.3 }} }}\n")
            f.write("  geometry IndexedFaceSet { creaseAngle 0.5\n    coord Coordinate { point [\n")
            f.write(",\n".join(f"      {v.x * k:.5f} {v.y * k:.5f} {v.z * k:.5f}" for v in verts))
            f.write(" ] }\n    coordIndex [\n")
            f.write(",\n".join(f"      {a},{b2},{c},-1" for a, b2, c in tris))
            f.write(" ] }\n}\n")


os.makedirs(OUT, exist_ok=True)
for n in (2, 3):
    name = f"JST_PH_S{n}B-PH-SM4-TB_1x{n:02d}-1MP_P2.00mm_Horizontal"
    housing, pins = connector(n)
    Part.makeCompound([housing, pins]).exportStep(os.path.join(OUT, name + ".step"))
    write_wrl(os.path.join(OUT, name + ".wrl"), [(housing, NYLON), (pins, METAL)])
    print("wrote", name, "housing", housing.BoundBox, "pins", pins.BoundBox)
