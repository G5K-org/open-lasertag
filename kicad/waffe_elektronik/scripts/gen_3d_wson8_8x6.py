"""3D model for WSON-8 8x6 mm with exposed pad (U14, SPI-NAND GD5F1GQ5UEYIGR).

KiCad ships the footprint WSON-8-1EP_8x6mm_P1.27mm_EP3.4x4.3mm but no model.
Body 8 x 6 x 0.75 mm, leads 0.4 wide on 1.27 mm pitch at x = +-3.75 (footprint pads),
exposed pad 3.4 x 4.3, pin 1 top left.

    freecadcmd scripts/gen_3d_wson8_8x6.py

Writes ../3dmodels/<name>.step and <name>.wrl (same layout as gen_3d_jst_ph_sm4.py).
Coordinates: footprint origin, model Y = -footprint y, Z up, mm.
"""
import os

import Part
from FreeCAD import Vector

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "3dmodels")
NAME = "WSON-8-1EP_8x6mm_P1.27mm_EP3.4x4.3mm"
BX, BY, H = 4.0, 3.0, 0.75   # half body, height
PITCH = 1.27

BODY = (0.15, 0.15, 0.15)
METAL = (0.84, 0.84, 0.80)
MARK = (0.75, 0.75, 0.75)


def box(x0, x1, y0, y1, z0, z1):
    """Box from footprint coordinates (y flipped for the model)."""
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, Vector(x0, -y1, z0))


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


body = box(-BX, BX, -BY, BY, 0.02, H)
mark = Part.makeCylinder(0.3, 0.02, Vector(-BX + 0.9, BY - 0.9, H))  # pin 1: footprint (-x, -y)
metal = [box(-1.7, 1.7, -2.15, 2.15, 0.0, 0.02)]                    # exposed pad
for i in range(4):
    y = -1.5 * PITCH + i * PITCH
    for s in (-1, 1):
        metal.append(box(min(s * 3.5, s * BX), max(s * 3.5, s * BX), y - 0.2, y + 0.2, 0.0, 0.2))
pins = metal[0]
for m in metal[1:]:
    pins = pins.fuse(m)
pins = pins.removeSplitter()
body = body.cut(pins)

os.makedirs(OUT, exist_ok=True)
Part.makeCompound([body, pins, mark]).exportStep(os.path.join(OUT, NAME + ".step"))
write_wrl(os.path.join(OUT, NAME + ".wrl"), [(body, BODY), (pins, METAL), (mark, MARK)])
print("wrote", NAME, "body", body.BoundBox, "pins", pins.BoundBox)
