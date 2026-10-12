#!/usr/bin/env python3
"""Routed length between two pads (shortest path over the net's tracks and vias).

    python3 pairlen.py board.kicad_pcb U4.14-U12.4 U4.13-U12.6 [U12.3-J3.B6 U12.1-J3.B7 ...] [--via=1.6]

Arguments come in pairs (P, N) of the same differential pair segment; prints
both lengths and the difference. Length is measured from pad centre to pad
centre along the copper; a via counts --via mm (default 1.6 = board
thickness) when the path changes layer through it.
"""
import heapq
import math
import sys
from collections import defaultdict

import pcbnew


def pad_of(board, ref_pad):
    ref, num = ref_pad.split(".")
    f = board.FindFootprintByReference(ref)
    for p in f.Pads():
        if p.GetNumber() == num:
            return p
    raise SystemExit(f"no pad {ref_pad}")


def key(p):
    return (round(p.x / 1e6, 4), round(p.y / 1e6, 4))


def length(board, a, b, via_len):
    pa, pb = pad_of(board, a), pad_of(board, b)
    net = pa.GetNetname()
    adj = defaultdict(list)  # node (layer, point) -> [(node, len)]
    points = defaultdict(set)  # layer -> track end points
    for t in board.GetTracks():
        if t.GetNetname() != net:
            continue
        if t.GetClass() == "PCB_VIA":
            p = key(t.GetPosition())
            layers = [l for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)]
            for i in layers:
                for j in layers:
                    if i != j:
                        adj[(i, p)].append(((j, p), via_len))
                points_v = p
            continue
        s, e, l = key(t.GetStart()), key(t.GetEnd()), t.GetLength() / 1e6
        adj[(t.GetLayer(), s)].append(((t.GetLayer(), e), l))
        adj[(t.GetLayer(), e)].append(((t.GetLayer(), s), l))
        points[t.GetLayer()] |= {s, e}

    def attach(pad, name):
        c = key(pad.GetPosition())
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            if not pad.IsOnLayer(layer):
                continue
            for q in points[layer]:
                if pad.HitTest(pcbnew.VECTOR2I(int(q[0] * 1e6), int(q[1] * 1e6))):
                    d = math.hypot(q[0] - c[0], q[1] - c[1])
                    adj[name].append(((layer, q), d))
                    adj[(layer, q)].append((name, d))

    attach(pa, "A")
    attach(pb, "B")
    dist = {"A": 0.0}
    heap = [(0.0, 0, "A")]
    n = 1
    while heap:
        d, _, u = heapq.heappop(heap)
        if u == "B":
            return net, d
        if d > dist.get(u, 1e9):
            continue
        for v, w in adj[u]:
            if d + w < dist.get(v, 1e9):
                dist[v] = d + w
                n += 1
                heapq.heappush(heap, (d + w, n, v))
    return net, None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    via = [float(a[6:]) for a in sys.argv if a.startswith("--via=")]
    via_len = via[0] if via else 1.6
    board = pcbnew.LoadBoard(args[0])
    segs = args[1:]
    worst = 0.0
    for i in range(0, len(segs) - 1, 2):
        res = []
        for s in segs[i:i + 2]:
            a, b = s.split("-")
            net, L = length(board, a, b, via_len)
            res.append((s, net, L))
            print(f"{s:16} {net:12} {'not connected' if L is None else f'{L:7.3f} mm'}")
        if res[0][2] is not None and res[1][2] is not None:
            diff = res[0][2] - res[1][2]
            worst = max(worst, abs(diff))
            print(f"  difference {diff:+.3f} mm")
    print(f"max difference {worst:.3f} mm")


if __name__ == "__main__":
    main()
