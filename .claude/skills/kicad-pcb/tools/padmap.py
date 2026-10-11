import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
nets = {}
for f in b.GetFootprints():
    for p in f.Pads():
        n = p.GetNetname()
        if not n or n.startswith("unconnected"): continue
        nets.setdefault(n, []).append(f"{f.GetReference()}.{p.GetNumber()}({p.GetPosition().x/1e6:.2f},{p.GetPosition().y/1e6:.2f})")
skip = set(sys.argv[2:])
for n in sorted(nets, key=lambda k: (len(nets[k]) > 8, k)):
    if n in skip: print(f"{n}: {len(nets[n])} pads"); continue
    print(f"{n}: " + " ".join(sorted(set(nets[n]))))
