#!/usr/bin/env python3
"""Find detours: every unbranched track run between two stops on one layer is
compared with the shortest 0/45/90 deg path between its ends. Stops are run
ends, branch points, vias and pad centres of the same net (required waypoints).

    python3 detour.py board.kicad_pcb [--min=0.5] [--ratio=1.08] [--layers=F,2,B]

Shortest octilinear length for dx, dy: max - min + min * sqrt(2).
A run is reported when it is longer by more than --min mm AND by more than
--ratio. Typical hit: an L (dx + dy) where one 45 deg run would do.
"""
import math
import sys
from collections import defaultdict

import pcbnew

LAYERS = {"F": pcbnew.F_Cu, "1": pcbnew.In1_Cu, "2": pcbnew.In2_Cu, "B": pcbnew.B_Cu}


def octi(dx, dy):
    a, b = sorted((abs(dx), abs(dy)))
    return b - a + a * math.sqrt(2)


def key(p):
    return (round(p.x / 1e6, 3), round(p.y / 1e6, 3))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
    min_mm = float(opts.get("min", 0.5))
    ratio = float(opts.get("ratio", 1.08))
    layers = opts.get("layers", "F,2,B").split(",")
    board = pcbnew.LoadBoard(args[0])

    stops = set()  # (net, point)
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            stops.add((t.GetNetname(), key(t.GetPosition())))
    for f in board.GetFootprints():
        for pad in f.Pads():
            stops.add((pad.GetNetname(), key(pad.GetPosition())))

    found = 0

    def report(ln, net, p, cur, total, path):
        nonlocal found
        best = octi(cur[0] - p[0], cur[1] - p[1])
        extra = total - best
        if extra > min_mm and (best == 0 or total / best > ratio):
            found += 1
            print(f"{ln}.Cu {net:28} {p} -> {cur}: {total:6.2f} mm, shortest {best:6.2f} mm, "
                  f"+{extra:.2f} mm, {len(path) - 1} segments")

    for ln in layers:
        lid = LAYERS[ln]
        adj = defaultdict(list)  # (net, point) -> [(other point, length)]
        for t in board.GetTracks():
            if t.GetClass() != "PCB_TRACK" or t.GetLayer() != lid:
                continue
            a, b = key(t.GetStart()), key(t.GetEnd())
            L = t.GetLength() / 1e6
            net = t.GetNetname()
            adj[(net, a)].append((b, L))
            adj[(net, b)].append((a, L))
        def is_stop(net, q):
            return len(adj[(net, q)]) != 2 or (net, q) in stops

        done = set()  # walked segments
        for (net, p), nb in list(adj.items()):
            if not is_stop(net, p):
                continue
            for first, L0 in nb:
                if (net, p, first) in done:
                    continue
                # walk from a stop through plain bends to the next stop
                path, total, prev, cur = [p], L0, p, first
                path.append(cur)
                while not is_stop(net, cur):
                    q, L = [(q, L) for q, L in adj[(net, cur)] if q != prev][0]
                    total += L
                    prev, cur = cur, q
                    path.append(cur)
                done.add((net, p, first)); done.add((net, cur, prev))
                report(ln, net, p, cur, total, path)

    print(f"detours: {found}")




if __name__ == "__main__":
    main()
