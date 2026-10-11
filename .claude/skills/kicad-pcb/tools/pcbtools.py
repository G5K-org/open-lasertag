"""Helpers: courtyard overlap check + PNG plot of a .kicad_pcb."""
import subprocess, sys, os
import pcbnew

def overlaps(path, margin=0.0):
    b = pcbnew.LoadBoard(path)
    fps = [f for f in b.GetFootprints()]
    polys = {}
    for f in fps:
        cy = f.GetCourtyard(pcbnew.F_CrtYd)
        if cy.OutlineCount():
            polys[f.GetReference()] = cy
    refs = sorted(polys)
    out = []
    for i, a in enumerate(refs):
        for bref in refs[i+1:]:
            pa, pb = polys[a], polys[bref]
            if pa.BBox().Intersects(pb.BBox()):
                inter = pa.CloneDropTriangulation(); inter.BooleanIntersection(pb)
                if inter.OutlineCount() and inter.Area() > 0.0001e12 * 0 + 1000:  # >0.001 mm^2
                    out.append((a, bref, inter.Area() / 1e12))
    # outside board?
    ec = b.GetBoardEdgesBoundingBox()
    for f in fps:
        bb = f.GetCourtyard(pcbnew.F_CrtYd).BBox() if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else None
    return out

def plot(path, png, layers="F.Cu,F.Silkscreen,F.Courtyard,F.Fab,Edge.Cuts", dpi=400, extra=""):
    pdf = png[:-4] + ".pdf"
    subprocess.run(["kicad-cli", "pcb", "export", "pdf", "-l", layers, "--include-border-title" if False else "--exclude-value", "-o", pdf, path] + ([] if not extra else extra.split()), check=True, capture_output=True)
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-singlefile", pdf, png[:-4]], check=True)
    subprocess.run(["magick", png, "-trim", "+repage", "-bordercolor", "white", "-border", "20", png], check=True)

if __name__ == "__main__":
    for a, b, area in overlaps(sys.argv[1]):
        print(f"OVERLAP {a} / {b}: {area:.2f} mm2")
