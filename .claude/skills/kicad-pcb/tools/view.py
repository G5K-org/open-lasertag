"""view.py board.kicad_pcb out.png [x0 y0 x1 y1] [--layers F,B,1,2] - pads/tracks/vias with net labels + mm grid."""
import sys, pcbnew, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
args = [a for a in sys.argv[1:] if not a.startswith("--")]
opts = dict(a[2:].split("=") for a in sys.argv[1:] if a.startswith("--"))
b = pcbnew.LoadBoard(args[0]); out = args[1]
box = list(map(float, args[2:6])) if len(args) >= 6 else [-1, -1, 55, 45]
show = opts.get("layers", "F,B,1,2").split(",")
LC = {"F": (pcbnew.F_Cu, "#d02020"), "1": (pcbnew.In1_Cu, "#20a020"), "2": (pcbnew.In2_Cu, "#c08000"), "B": (pcbnew.B_Cu, "#2050e0")}
w = box[2] - box[0]; h = box[3] - box[1]
s = float(opts.get("scale", 0.42))
fig, ax = plt.subplots(figsize=(w * s, h * s), dpi=110)
ax.set_xlim(box[0], box[2]); ax.set_ylim(box[3], box[1]); ax.set_aspect("equal")
import numpy as np
ax.set_xticks(np.arange(int(box[0]), box[2] + 0.01, 1), minor=True); ax.set_yticks(np.arange(int(box[1]), box[3] + 0.01, 1), minor=True)
ax.set_xticks(np.arange(int(box[0] / 5) * 5, box[2] + 0.01, 5 if w > 20 else 1)); ax.set_yticks(np.arange(int(box[1] / 5) * 5, box[3] + 0.01, 5 if h > 20 else 1))
ax.grid(which="minor", lw=0.2, color="#ddd"); ax.grid(which="major", lw=0.5, color="#aaa")
def poly(sp, **kw):
    for i in range(sp.OutlineCount()):
        o = sp.Outline(i); pts = [(o.CPoint(j).x / 1e6, o.CPoint(j).y / 1e6) for j in range(o.PointCount())]
        if pts: ax.add_patch(Polygon(pts, closed=True, **kw))
# zones
for z in b.Zones():
    for k in show:
        L, c = LC[k]
        if z.IsOnLayer(L) and z.GetFilledPolysList(L).OutlineCount():
            poly(z.GetFilledPolysList(L), fc=c, alpha=0.75 if z.IsTeardropArea() else 0.08, ec="none", zorder=4 if z.IsTeardropArea() else 1)
for f in b.GetFootprints():
    cy = f.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount(): poly(cy, fill=False, ec="#c0c", lw=0.4)
    p = f.GetPosition()
    ax.text(p.x / 1e6, p.y / 1e6, f.GetReference(), fontsize=7, color="#808", ha="center", va="center", alpha=0.6, weight="bold")
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition(); ax.add_patch(Circle((p.x / 1e6, p.y / 1e6), t.GetWidth(pcbnew.F_Cu) / 2e6, fc="#888", ec="k", lw=0.3, zorder=5))
        ax.add_patch(Circle((p.x / 1e6, p.y / 1e6), t.GetDrillValue() / 2e6, fc="w", zorder=6))
        continue
    for k in show:
        L, c = LC[k]
        if t.GetLayer() == L:
            ax.plot([t.GetStart().x / 1e6, t.GetEnd().x / 1e6], [t.GetStart().y / 1e6, t.GetEnd().y / 1e6], color=c, lw=t.GetWidth() / 1e6 * 72 / 25.4 * s * 25.4 * 110 / 72 / 110 * 72 / 25.4 * 25.4 / 1, alpha=0.75, solid_capstyle="round", zorder=4)
for f in b.GetFootprints():
    for pad in f.Pads():
        if not (pad.IsOnLayer(pcbnew.F_Cu)): continue
        sp = pad.GetEffectivePolygon(pcbnew.F_Cu, pcbnew.ERROR_INSIDE) if hasattr(pad, "GetEffectivePolygon") else None
        net = pad.GetNetname()
        col = "#e8a0a0" if net == "GND" else "#f0d090" if net in ("5V_PERIPH", "BAT_P", "3V3_MCU", "VBUS_NATIVE") else "#f4c4c4" if net else "#ddd"
        try: poly(sp, fc=col, ec="#a33", lw=0.3, zorder=3)
        except Exception: pass
        p = pad.GetPosition()
        lab = net.replace("Net-(", "").replace(")", "").replace("_PERIPH", "").replace("_MCU", "").replace("_NATIVE", "")
        if pad.GetSize().x > 1e5 and lab and (len(args) >= 6 or net not in ("GND",)):
            ax.text(p.x / 1e6, p.y / 1e6, lab[:10], fontsize=4.2 if w > 20 else 6, ha="center", va="center", zorder=7, color="#222")
ax.tick_params(labelsize=6)
plt.tight_layout(); plt.savefig(out); print("ok", out)
