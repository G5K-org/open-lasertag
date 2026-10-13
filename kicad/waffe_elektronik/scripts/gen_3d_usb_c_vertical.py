"""3D model for the vertical USB-C receptacle hanxia HX-TYPE-C 16P 180 LT H10.5 (LCSC C49261570).

Dimensions from the hanxia drawing: base 12.00 x 5.00 x 2.10 (flanges), shell 8.94 x 3.16 with the
opening 8.34 x 2.56, height L = 10.50 above the PCB. Pads rotated 180 deg like the footprint (A row on top).

    freecadcmd scripts/gen_3d_usb_c_vertical.py

Writes ../3dmodels/<name>.step and <name>.wrl (same scheme as gen_3d_jst_ph_sm4.py).
"""
import os

import Part
from FreeCAD import Vector

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "3dmodels")
NAME = "USB_C_Receptacle_HX_TYPE-C-16P-180-LT-H10.5_Vertical"
H, H_BASE = 10.5, 2.1

BLACK = (0.12, 0.12, 0.12)
METAL = (0.80, 0.80, 0.78)


def obround(w, h, z0, z1):
    """Stadium shape w x h (x, y), extruded from z0 to z1."""
    r = h / 2
    body = Part.makeBox(w - h, h, z1 - z0, Vector(-(w - h) / 2, -r, z0))
    for s in (-1, 1):
        body = body.fuse(Part.makeCylinder(r, z1 - z0, Vector(s * (w - h) / 2, 0, z0)))
    return body.removeSplitter()


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, Vector(x0, y0, z0))


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


base = box(-5.37, 5.37, -1.8, 1.8, 0.0, H_BASE)
for s in (-1, 1):                                                            # side flanges with the pegs
    base = base.fuse(box(s * 4.6, s * 6.0, -2.5, 2.5, 0.0, H_BASE) if s > 0 else box(-6.0, -4.6, -2.5, 2.5, 0.0, H_BASE))
housing = base.removeSplitter()
shell = obround(8.94, 3.16, H_BASE, H).cut(obround(8.34, 2.56, H_BASE - 0.1, H + 0.1))   # mating shell
tongue = box(-3.3, 3.3, -0.35, 0.35, H_BASE, H - 0.6)
legs = []
for i in range(8):
    for y in (-1.365, 1.365):
        legs.append(box(-3.5 + i - 0.15, -3.5 + i + 0.15, y - 0.6, y + 0.6, 0.0, 0.15))
for x, y in ((-4.16, -1.4), (4.16, -1.4), (-4.16, 1.4), (4.16, 1.4)):
    legs.append(box(x - 0.45, x + 0.45, y - 0.15, y + 0.15, 0.0, 0.25))
pegs = [Part.makeCylinder(0.35, 1.0, Vector(x, y, -1.0)) for x, y in ((-5.41, -1.48), (5.41, 1.48))]
metal = shell
for p in legs:
    metal = metal.fuse(p)
metal = metal.removeSplitter()
for p in pegs:
    housing = housing.fuse(p)

Part.makeCompound([housing, metal, tongue]).exportStep(os.path.join(OUT, NAME + ".step"))
write_wrl(os.path.join(OUT, NAME + ".wrl"), [(housing, BLACK), (metal, METAL), (tongue, BLACK)])
print("wrote", NAME, housing.BoundBox, metal.BoundBox)
