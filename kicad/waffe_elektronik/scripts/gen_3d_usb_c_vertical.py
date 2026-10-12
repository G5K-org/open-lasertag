"""3D model for the vertical USB-C receptacle HRO TYPE-C-31-E-17 (LCSC C7424785).

Dimensions from the HRO drawing: body 9.70 x 4.20, sealing flange 10.38 x 4.59
(top 1.55 mm), opening 8.34 x 2.56, height 6.00 above the PCB.

    freecadcmd scripts/gen_3d_usb_c_vertical.py

Writes ../3dmodels/<name>.step and <name>.wrl (same scheme as gen_3d_jst_ph_sm4.py).
"""
import os

import Part
from FreeCAD import Vector

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "3dmodels")
NAME = "USB_C_Receptacle_HRO_TYPE-C-31-E-17_Vertical"
H, H_FLANGE = 6.0, 1.55

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


housing = box(-4.85, 4.85, -2.1, 2.1, 0.0, H - H_FLANGE)
housing = housing.fuse(obround(10.38, 4.59, H - H_FLANGE, H)).removeSplitter()
shell = obround(8.94, 3.16, 1.2, H).cut(obround(8.34, 2.56, 1.0, H + 0.1))   # mating shell
housing = housing.cut(obround(8.94, 3.16, 1.2, H + 0.1))
tongue = box(-3.3, 3.3, -0.35, 0.35, 1.2, H - 0.6)
legs = []
for x in (-2.75, -1.25, -0.75, -0.25, 0.25, 0.75, 1.25, 2.75):
    for y in (-0.81, 0.81):
        legs.append(box(x - 0.1, x + 0.1, y - 0.3, y + 0.3, 0.0, 0.15))
for x, y in ((-2.29, -2.08), (2.29, -2.08), (-2.29, 2.08), (2.29, 2.08)):
    legs.append(box(x - 0.25, x + 0.25, y - 0.45, y + 0.45, 0.0, 0.15))
metal = shell
for p in legs:
    metal = metal.fuse(p)
metal = metal.removeSplitter()

Part.makeCompound([housing, metal, tongue]).exportStep(os.path.join(OUT, NAME + ".step"))
write_wrl(os.path.join(OUT, NAME + ".wrl"), [(housing, BLACK), (metal, METAL), (tongue, BLACK)])
print("wrote", NAME, housing.BoundBox)
