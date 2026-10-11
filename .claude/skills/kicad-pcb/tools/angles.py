"""angles.py board - report non-octilinear segments and bends > 45 deg (incl. T-joins)."""
import sys, math, pcbnew, collections
b = pcbnew.LoadBoard(sys.argv[1])
segs = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
def P(v): return (round(v.x / 1e3), round(v.y / 1e3))  # um
bad_dir, bad_bend = [], []
ends = collections.defaultdict(list)
for t in segs:
    a, c = P(t.GetStart()), P(t.GetEnd())
    dx, dy = c[0] - a[0], c[1] - a[1]
    if dx == 0 and dy == 0: continue
    ang = math.degrees(math.atan2(dy, dx)) % 45
    if min(ang, 45 - ang) > 0.5:
        bad_dir.append((t.GetNetname(), t.GetLayerName(), a, c))
    for p, q in ((a, c), (c, a)):
        ends[(t.GetLayer(), t.GetNetCode(), p)].append(math.atan2(q[1] - p[1], q[0] - p[0]))
pads = [pd for f in b.GetFootprints() for pd in f.Pads()]
vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
def covered(L, p):
    v = pcbnew.VECTOR2I(p[0] * 1000, p[1] * 1000)
    if any(pd.IsOnLayer(L) and pd.HitTest(v) for pd in pads): return True
    return any((vv.GetPosition() - v).EuclideanNorm() < vv.GetWidth(pcbnew.F_Cu) / 2 for vv in vias)
for (L, n, p), dirs in ends.items():
    if covered(L, p): continue
    if len(dirs) == 2:
        turn = 180 - abs((math.degrees(dirs[0] - dirs[1]) + 180) % 360 - 180)
        if turn > 45.5:
            bad_bend.append((b.FindNet(n).GetNetname(), pcbnew.LayerName(L) if hasattr(pcbnew,'LayerName') else L, p, round(turn)))
    elif len(dirs) > 2:
        # junction: every pair must differ by >= 135 deg or be collinear... report angles < 135 between adjacent
        ds = sorted(math.degrees(d) % 360 for d in dirs)
        gaps = [(ds[(i + 1) % len(ds)] - ds[i]) % 360 for i in range(len(ds))]
        if len(ds) != 3 or sorted(round(g / 5) * 5 for g in gaps) != [45, 135, 180]:
            bad_bend.append((b.FindNet(n).GetNetname(), L, p, "T" + str([round(g) for g in gaps])))
print("segments", len(segs), "non-octilinear", len(bad_dir), "bends>45", len(bad_bend))
if "-v" in sys.argv:
    for x in bad_dir: print("DIR", x)
    for x in bad_bend: print("BEND", x)
# T-joins: a track end lying on the interior of another segment (same net/layer)
tj = []
for t in segs:
    for e, o in ((P(t.GetStart()), P(t.GetEnd())), (P(t.GetEnd()), P(t.GetStart()))):
        if covered(t.GetLayer(), e): continue
        for u in segs:
            if u is t or u.GetNetCode() != t.GetNetCode() or u.GetLayer() != t.GetLayer(): continue
            a, c = P(u.GetStart()), P(u.GetEnd())
            if e in (a, c): continue
            L2 = (c[0]-a[0])**2 + (c[1]-a[1])**2
            if L2 == 0: continue
            tt = ((e[0]-a[0])*(c[0]-a[0]) + (e[1]-a[1])*(c[1]-a[1])) / L2
            if not 0 < tt < 1: continue
            px, py = a[0] + tt*(c[0]-a[0]), a[1] + tt*(c[1]-a[1])
            if math.hypot(px - e[0], py - e[1]) > 5: continue
            ang = abs((math.degrees(math.atan2(o[1]-e[1], o[0]-e[0]) - math.atan2(c[1]-a[1], c[0]-a[0]) * 180 / math.pi) + 90) % 180 - 90)
            if abs(ang) > 46:
                tj.append((t.GetNetname(), t.GetLayerName(), e, round(abs(ang))))
print("T-joins >45:", len(tj))
for x in tj: print("TJ", x)
