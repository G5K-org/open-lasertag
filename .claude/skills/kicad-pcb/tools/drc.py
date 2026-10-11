"""drc.py board.kicad_pcb [box x0 y0 x1 y1] - run kicad-cli DRC, summarize."""
import json, subprocess, sys, collections
pcb = sys.argv[1]; out = pcb[:-10] + "_drc.json"
subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--units", "mm", "--severity-all", "-o", out, pcb], capture_output=True)
d = json.load(open(out))
box = list(map(float, sys.argv[2:6])) if len(sys.argv) >= 6 else None
def inbox(v):
    if not box: return True
    return any(box[0] <= i["pos"]["x"] <= box[2] and box[1] <= i["pos"]["y"] <= box[3] for i in v["items"])
c = collections.Counter(v["type"] for v in d["violations"])
print("violations:", dict(c))
print("unconnected:", len(d["unconnected_items"]))
skip = {"silk_overlap", "silk_over_copper", "silk_edge_clearance", "text_height", "text_thickness", "lib_footprint_mismatch", "lib_footprint_issues"}
for v in d["violations"]:
    if v["type"] in skip or not inbox(v): continue
    its = "; ".join(f'{i["description"][:60]} @({i["pos"]["x"]:.2f},{i["pos"]["y"]:.2f})' for i in v["items"])
    print(f'  {v["type"]}: {v["description"][:50]} | {its}')
if "-u" in sys.argv:
    for v in d["unconnected_items"]:
        if inbox(v): print("  UNCONN:", "; ".join(f'{i["description"][:50]} @({i["pos"]["x"]:.2f},{i["pos"]["y"]:.2f})' for i in v["items"]))
