"""3D model for ESP32-S3-WROOM-1U (U4, variant with external antenna) on the WROOM-1 footprint.

KiCad ships ESP32-S3-WROOM-1 only. The 1U has the same pads, its body is 18 x 19.2 x 3.2 mm and ends
3.15 mm earlier on the antenna side (footprint y from -6.45 to 12.75). U.FL receptacle beside the shield
at footprint (6.0, -3.99).

    freecadcmd scripts/gen_3d_wroom1u.py

Writes ../3dmodels/<name>.step and <name>.wrl (same layout as gen_3d_wson8_8x6.py).
Used for the housing render of the antenna variant (gehaeuse/scripts/baugruppe.py), not in the board file.
Coordinates: footprint origin, model Y = -footprint y, Z up, mm.
"""
import os

import Part
from FreeCAD import Vector

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "3dmodels")
NAME = "ESP32-S3-WROOM-1U"
X0, X1, Y0, Y1 = -9.0, 9.0, -6.45, 12.75   # module outline (footprint coordinates)
T_PCB, H = 0.8, 3.2
UFL = (6.0, -3.99)
UFL_BODY = (2.6, 1.25)                     # receptacle edge, height

PCB = (0.1, 0.3, 0.15)
METAL = (0.8, 0.8, 0.78)
GOLD = (0.85, 0.7, 0.3)


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


pcb = box(X0, X1, Y0, Y1, 0.0, T_PCB)
shield = box(X0 + 0.7, X1 - 0.7, Y0 + 0.6, Y1 - 0.6, T_PCB, H)
shield = shield.cut(box(UFL[0] - 2.4, X1, Y0, UFL[1] + 2.0, T_PCB, H))   # corner for the U.FL
e, h = UFL_BODY
ufl = box(UFL[0] - e / 2, UFL[0] + e / 2, UFL[1] - e / 2, UFL[1] + e / 2, T_PCB, T_PCB + 0.25)
ufl = ufl.fuse(Part.makeCylinder(1.0, h - 0.25, Vector(UFL[0], -UFL[1], T_PCB + 0.25))).removeSplitter()

os.makedirs(OUT, exist_ok=True)
Part.makeCompound([pcb, shield, ufl]).exportStep(os.path.join(OUT, NAME + ".step"))
write_wrl(os.path.join(OUT, NAME + ".wrl"), [(pcb, PCB), (shield, METAL), (ufl, GOLD)])
print("wrote", NAME, "pcb", pcb.BoundBox, "shield", shield.BoundBox)
