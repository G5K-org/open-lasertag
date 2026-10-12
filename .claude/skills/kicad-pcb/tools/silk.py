#!/usr/bin/env python3
"""Check board texts on F.SilkS: readable after assembly means no overlap with
pads, component bodies (F.Fab outline, else courtyard), footprint silk, the
board edge or other texts.

    python3 silk.py board.kicad_pcb [--suggest] [--gap=0.2]
    python3 silk.py board.kicad_pcb --place "AKKU=BT1" "USB=J3" ...

--suggest: for every bad text, print the nearest free spot (x, y, angle) in
the same orientation or rotated by 90 deg, searched on a 0.1 mm grid.
--place TEXT=REF: free spot (0 or 90 deg) closest to the courtyard of REF and
clearly closer to REF than to any other REF given, so the label is not
mistaken for a neighbour's. Labels are placed one after another and keep
clear of each other.
"""
import math
import sys

import pcbnew

MM = 1e6


def bbox(item):
    b = item.GetBoundingBox()
    return (b.GetLeft() / MM, b.GetTop() / MM, b.GetRight() / MM, b.GetBottom() / MM)


def body(f):
    """Component body seen from above: the F.Fab outline, else the courtyard."""
    boxes = [bbox(g) for g in f.GraphicalItems()
             if g.GetLayer() == pcbnew.F_Fab and not isinstance(g, pcbnew.PCB_TEXT)]
    if boxes:
        return (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))
    cy = f.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount():
        b = cy.BBox()
        return (b.GetLeft() / MM, b.GetTop() / MM, b.GetRight() / MM, b.GetBottom() / MM)
    return None


def hit(a, b, gap):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict((a[2:].split("=", 1) + [""])[:2] for a in sys.argv[1:] if a.startswith("--"))
    gap = float(opts.get("gap") or 0.2)
    board = pcbnew.LoadBoard(args[0])

    edge = bbox(board.GetBoardEdgesBoundingBox()) if False else None
    eb = board.GetBoardEdgesBoundingBox()
    edge = (eb.GetLeft() / MM, eb.GetTop() / MM, eb.GetRight() / MM, eb.GetBottom() / MM)

    obstacles = []  # (box, name)
    for f in board.GetFootprints():
        ref = f.GetReference()
        for pad in f.Pads():
            obstacles.append((bbox(pad), f"{ref}.{pad.GetNumber()}"))
        bd = body(f)
        if bd:
            obstacles.append((bd, f"{ref} body"))
        for g in f.GraphicalItems():  # footprint silk (outlines, pin-1 marks)
            if g.GetLayer() == pcbnew.F_SilkS:
                obstacles.append((bbox(g), f"{ref} silk"))

    texts = [d for d in board.GetDrawings()
             if isinstance(d, pcbnew.PCB_TEXT) and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS)]
    bad = 0
    boxes = {id(t): bbox(t) for t in texts}
    for t in texts:
        name = t.GetText()
        if t.GetLayer() == pcbnew.B_SilkS:
            print(f"note      {name!r} is on the back (BACK_LABELS)")
            continue
        b = boxes[id(t)]
        probs = [n for o, n in obstacles if hit(b, o, gap)]
        probs += [f"text {o.GetText()!r}" for o in texts if o is not t and o.GetLayer() == t.GetLayer()
                  and hit(b, boxes[id(o)], gap)]
        if b[0] < edge[0] + 0.3 or b[1] < edge[1] + 0.3 or b[2] > edge[2] - 0.3 or b[3] > edge[3] - 0.3:
            probs.append("board edge")
        if probs:
            bad += 1
            p = t.GetPosition()
            print(f"F.SilkS   {name!r} at ({p.x / MM:.2f}, {p.y / MM:.2f}) {t.GetTextAngleDegrees():.0f} deg: "
                  + ", ".join(sorted(set(probs))[:6]))
            if "suggest" in opts:
                s = suggest(t, b, obstacles, [boxes[id(o)] for o in texts if o is not t], edge, gap)
                print(f"          -> {s}")
    print(f"silk problems: {bad}")


def suggest(t, b, obstacles, others, edge, gap):
    p = t.GetPosition()
    x0, y0 = p.x / MM, p.y / MM
    w, h = b[2] - b[0], b[3] - b[1]
    best = None
    for rot, (ww, hh) in ((0, (w, h)), (90, (h, w))):
        for r in range(0, 200):  # spiral by rings of 0.1 mm
            ring = []
            for i in range(-r, r + 1):
                for dx, dy in ((i, -r), (i, r), (-r, i), (r, i)):
                    ring.append((x0 + dx * 0.1, y0 + dy * 0.1))
            for cx, cy in ring:
                c = (cx - ww / 2, cy - hh / 2, cx + ww / 2, cy + hh / 2)
                if c[0] < edge[0] + 0.3 or c[1] < edge[1] + 0.3 or c[2] > edge[2] - 0.3 or c[3] > edge[3] - 0.3:
                    continue
                if any(hit(c, o, gap) for o, _ in obstacles) or any(hit(c, o, gap) for o in others):
                    continue
                d = math.hypot(cx - x0, cy - y0)
                cand = (d, round(cx, 2), round(cy, 2), (t.GetTextAngleDegrees() + rot) % 180)
                if best is None or cand < best:
                    best = cand
                break
            else:
                continue
            break
    return "no free spot" if best is None else f"({best[1]}, {best[2]}) angle {best[3]:.0f}, {best[0]:.1f} mm away"


def place(board, pairs, gap):
    import numpy as np
    S = 0.05  # grid
    eb = board.GetBoardEdgesBoundingBox()
    W, H = eb.GetRight() / MM, eb.GetBottom() / MM
    nx, ny = int(W / S) + 1, int(H / S) + 1
    occ = np.zeros((ny, nx), bool)
    def block(r, g):
        x0, y0 = max(0, int((r[0] - g) / S)), max(0, int((r[1] - g) / S))
        x1, y1 = min(nx, int(math.ceil((r[2] + g) / S)) + 1), min(ny, int(math.ceil((r[3] + g) / S)) + 1)
        occ[y0:y1, x0:x1] = True
    cyd = {}
    for f in board.GetFootprints():
        for pad in f.Pads():
            block(bbox(pad), gap)
        r = body(f)
        if r:
            block(r, gap); cyd[f.GetReference()] = r
        for g in f.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS:
                block(bbox(g), gap)
    m = int(round(0.3 / S))  # board edge clearance
    occ[:m, :] = occ[-m:, :] = True; occ[:, :m] = occ[:, -m:] = True
    texts = {d.GetText(): d for d in board.GetDrawings() if isinstance(d, pcbnew.PCB_TEXT)}
    refs = [r for _, r in pairs]
    ys, xs = np.mgrid[0:ny, 0:nx]
    X, Y = xs * S, ys * S
    def rdist(cx, cy, w, h, r):  # gap between window and rect r
        dx = np.maximum(np.maximum(r[0] - (cx + w / 2), (cx - w / 2) - r[2]), 0)
        dy = np.maximum(np.maximum(r[1] - (cy + h / 2), (cy - h / 2) - r[3]), 0)
        return np.hypot(dx, dy)
    for name, ref in pairs:
        t = texts[name]
        b = bbox(t); w0, h0 = b[2] - b[0], b[3] - b[1]
        a0 = t.GetTextAngleDegrees() % 180
        if a0:
            w0, h0 = h0, w0
        I = np.pad(occ.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        best = None
        for ang, (w, h) in ((0, (w0, h0)), (90, (h0, w0))):
            kw, kh = int(math.ceil(w / S)), int(math.ceil(h / S))
            # free[y, x]: window with top-left cell (y, x) is empty
            win = I[kh:, kw:] - I[:-kh, kw:] - I[kh:, :-kw] + I[:-kh, :-kw]
            free = win == 0
            cx = X[:free.shape[0], :free.shape[1]] + kw * S / 2
            cy = Y[:free.shape[0], :free.shape[1]] + kh * S / 2
            d = rdist(cx, cy, w, h, cyd[ref])
            other = np.full(d.shape, 1e9)
            for o in refs:
                if o != ref:
                    other = np.minimum(other, rdist(cx, cy, w, h, cyd[o]))
            ok = free & (d < other - 0.3)
            if not ok.any():
                continue
            score = np.where(ok, d + (0.3 if ang != a0 else 0), 1e9)
            j = np.unravel_index(np.argmin(score), score.shape)
            cand = (float(score[j]), round(float(cx[j]), 2), round(float(cy[j]), 2), ang, kw, kh, j)
            if best is None or cand[0] < best[0]:
                best = cand
        if best is None:
            print(f"{name!r:12} {ref:5} no free spot")
            continue
        _, x, y, ang, kw, kh, (jy, jx) = best
        occ[max(0, jy - int(0.3 / S)):jy + kh + int(0.3 / S), max(0, jx - int(0.3 / S)):jx + kw + int(0.3 / S)] = True
        print(f"{name!r:12} {ref:5} -> ({x}, {y}) angle {ang}, {best[0]:.2f} mm from {ref}")


if __name__ == "__main__":
    if "--place" in sys.argv:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        g = [a for a in sys.argv if a.startswith("--gap=")]
        place(pcbnew.LoadBoard(args[0]), [tuple(a.split("=", 1)) for a in args[1:]],
              float(g[0][6:]) if g else 0.15)
    else:
        main()
