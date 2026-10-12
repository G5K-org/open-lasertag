#!/usr/bin/env python3
"""Hand-placed, hand-routed PCB for the Lasertag-Waffe (run with system python3, needs pcbnew).

Stackup (4 layers, Espressif-recommended):
  F.Cu   components + short signal routes
  In1.Cu solid GND, no traces at all
  In2.Cu power distribution (5V_PERIPH / 3V3_MCU / BAT_P) + GND fill
  B.Cu   a few signals + GND fill, no components
Every GND pad gets its own via straight down to In1 - no GND traces.
"""
import json
import math
import os
import re
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
NETLIST = os.environ.get("NETLIST", "/tmp/board.net")
OUT = os.environ.get("OUT_PCB", os.path.join(PROJ, "waffe_elektronik.kicad_pcb"))
FPLIB = "/usr/share/kicad/footprints"
MM = pcbnew.FromMM

# ------------------------------------------------------------------ board size
W0, H = 54.0, 46.0  # main board; the strip top right carries the OLED and encoder connectors
W, Y1 = 59.6, 18.5   # L shape: width W for y < Y1, W0 below
MX, MY = W0 - 11.5, 6.75  # ESP32 module origin; board top edge = antenna keep-out line
SH_IN = 3.1     # JST-SH horizontal: body front this far from origin -> flush with board edge
PH_IN = 4.9     # JST-PH SM4 horizontal
USB_IN = 3.73   # GCT USB4105

# ------------------------------------------------------------------ placement
# ref: (x, y, rotation_deg)  - board coords, mm, origin top-left, y down.
# Connector rotation: 0 = opening faces down, 90 = right, 180 = up, 270 = left.
PLACE = {
    "U4": (MX, MY, 0),
    # --- power: battery in, MT3608 boost (tight SW loop), AMS1117
    "BT1": (PH_IN, 5.2, 270),
    "C19": (11.0, 3.2, 90), "U1": (14.3, 3.2, 180), "L1": (13.05, 8.8, 0),
    "D3": (19.9, 4.4, 180), "C20": (19.4, 7.2, 180), "R24": (21.2, 1.3, 180), "R25": (18.0, 1.3, 180),
    "U2": (26.3, 10.7, 90), "C2": (31.2, 11.8, 90), "C3": (25.2, 3.3, 90),
    # --- module: 100n + 10u right at pin 2, EN RC right at pin 3
    "C18": (30.1, 2.1, 90), "C17": (31.95, 2.1, 90), "R21": (28.25, 3.95, 270), "C16": (30.7, 5.3, 270),
    # --- left edge connectors
    "LED1": (SH_IN, 12.8, 270), "J6": (SH_IN, 20.6, 270),  # J6: TSOP 6 on the weapon
    "SW1": (SH_IN, 27.0, 270), "SW2": (SH_IN, 33.0, 270),
    # --- IR driver
    "R7": (9.5, 12.85, 180), "Q1": (8.6, 19.1, 180), "C7": (8.8, 15.65, 180),
    "R5": (12.3, 20.05, 180), "R6": (11.95, 17.7, 90),
    # --- trigger / reload debounce
    "C8": (8.6, 24.8, 0), "R9": (8.6, 26.5, 180), "C9": (8.6, 30.8, 0), "R10": (8.6, 32.5, 180),
    # --- bottom edge connectors: WS2812, USB-C, sensor cable, speaker
    "J1": (13.0, H - PH_IN, 0), "J3": (24.1, H - USB_IN, 0), "J2": (35.0, H - SH_IN, 0),
    "SP1": (48.6, H - PH_IN, 0),
    # --- right edge: motors
    "M1": (W0 - SH_IN, 24.8, 90),
    # --- right strip: OLED (I2C, Qwiic) above, rotary encoder below
    "J4": (W - SH_IN, 5.5, 90), "J5": (W - SH_IN, 13.5, 90),
    # --- WS2812 level shifter
    "U5": (16.0, 29.5, 0), "C21": (20.85, 27.2, 90), "R15": (11.0, 34.4, 270), "C10": (17.9, 34.0, 0),
    # --- USB: ESD (connector side down) + CC
    "U12": (24.1, 31.5, 90), "R23": (21.2, 35.2, 90), "R22": (27.0, 35.2, 90),
    # --- charger
    "U3": (22.5, 23.0, 0), "C4": (25.4, 23.6, 90), "C5": (19.6, 24.2, 90), "R1": (24.6, 20.1, 0), "R2": (19.6, 20.9, 270),
    # --- battery voltage divider
    "R3": (26.2, 17.6, 0), "R4": (27.3, 19.9, 270), "C6": (29.0, 18.6, 270),
    # --- EN (RESET) / BOOT buttons
    "SW3": (4.8, 42.5, 0), "SW4": (35.0, 22.1, 0), "C1": (32.2, 28.5, 90),
    # --- vibration drivers: top channel HIT (pad 24) -> M2, bottom channel RECOIL (pad 25) -> M1
    "R11": (46.13, 21.05, 180), "Q2": (45.55, 23.95, 0), "R12": (42.75, 23.5, 270), "D1": (45.3, 26.95, 0),
    # --- audio
    "U6": (41.8, 36.3, 270), "C22": (32.3, 34.5, 90), "C23": (38.75, 36.8, 90),
}


def parse_netlist(path):
    t = open(path).read()
    comps = {}
    for block in re.findall(r'\(comp\s+\(ref "[^"]+"\).*?\n\t\t\)', t, re.S):
        ref = re.search(r'\(ref "([^"]+)"\)', block).group(1)
        val = re.search(r'\(value "([^"]*)"\)', block).group(1)
        fp = re.search(r'\(footprint "([^"]*)"\)', block)
        ts = re.findall(r'\(tstamps "([^"]*)"\)', block)[-1]  # symbol UUID -> footprint path
        lcsc = re.search(r'\(name "LCSC"\) "([^"]*)"', block)
        if fp and fp.group(1):
            comps[ref] = (val, fp.group(1), ts, lcsc.group(1) if lcsc else "")
    nets = {}
    for m in re.finditer(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]*)"\)(.*?)\n\t\t\)', t, re.S):
        nodes = re.findall(r'\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', m.group(2))
        nets[m.group(1)] = [(r, p) for r, p in nodes if r in comps]  # full name, e.g. "/TRIGGER"
    return comps, nets


# ------------------------------------------------------------------ design rules
RULES = {
    "min_clearance": 0.15, "min_track_width": 0.15, "min_via_diameter": 0.4, "min_through_hole_diameter": 0.2,
    "min_via_annular_width": 0.1, "min_hole_to_hole": 0.25, "min_hole_clearance": 0.19,
    "min_copper_edge_clearance": 0.3, "min_silk_clearance": 0.0, "min_text_height": 0.8,
    "min_text_thickness": 0.12, "min_connection": 0.15, "min_resolved_spokes": 1,
}
NETCLASSES = [
    # name, track, clearance, via dia, via drill, diff width, diff gap, patterns
    ("Default", 0.2, 0.15, 0.5, 0.3, 0.2, 0.2, []),
    ("Power", 0.5, 0.15, 0.6, 0.3, 0.2, 0.2, ["GND", "BAT_P", "5V_PERIPH", "VBUS_NATIVE", "Net-(D3-A)",
                                              "Net-(D1-A)", "Net-(D2-A)", "Net-(LED1-K)", "Net-(LED*-A)", "Net-(U6-OUT*)"]),
    ("3V3", 0.6, 0.15, 0.6, 0.3, 0.2, 0.2, ["3V3_MCU"]),
    ("USB", 0.2, 0.15, 0.5, 0.3, 0.2, 0.2, ["USB_D*", "Net-(J3-D*)"]),
]


def write_project(pcb_path):
    pro = os.path.splitext(pcb_path)[0] + ".kicad_pro"
    d = json.load(open(pro)) if os.path.exists(pro) else {}
    ds = d.setdefault("board", {}).setdefault("design_settings", {})
    ds.setdefault("rules", {}).update(RULES)
    ds["track_widths"] = [0.0, 0.2, 0.25, 0.4, 0.5, 0.6, 0.8, 1.0]
    # teardrops on pads and vias (same ratios as the generated ones)
    ds["teardrop_options"] = [{"td_onpadsmd": True, "td_onroundshapesonly": False, "td_ontrackend": False,
                               "td_onviapad": True}]
    ds["teardrop_parameters"] = [
        {"td_target_name": name, "td_allow_use_two_tracks": True, "td_curve_segcount": 0, "td_height_ratio": 0.9,
         "td_length_ratio": 0.5, "td_maxheight": 2.0, "td_maxlen": 1.0, "td_on_pad_in_zone": False,
         "td_width_to_size_filter_ratio": 0.9}
        for name in ("td_round_shape", "td_rect_shape", "td_track_end")]
    ds["via_dimensions"] = [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.5, "drill": 0.3},
                            {"diameter": 0.6, "drill": 0.3}, {"diameter": 0.4, "drill": 0.2}]
    ds.setdefault("defaults", {})
    classes = []
    for i, (name, tw, cl, vd, vh, dw, dg, _) in enumerate(NETCLASSES):
        classes.append({"name": name, "track_width": tw, "clearance": cl, "via_diameter": vd, "via_drill": vh,
                        "diff_pair_width": dw, "diff_pair_gap": dg, "diff_pair_via_gap": 0.25,
                        "microvia_diameter": 0.3, "microvia_drill": 0.1, "bus_width": 12, "wire_width": 6,
                        "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
                        "schematic_color": "rgba(0, 0, 0, 0.000)",
                        "priority": 2147483647 if name == "Default" else i})
    d["net_settings"] = {"classes": classes, "meta": {"version": 4}, "net_colors": None,
                         "netclass_assignments": None,
                         "netclass_patterns": [{"netclass": n, "pattern": p}
                                               for n, *_r, pats in NETCLASSES for p in pats]}
    d.setdefault("meta", {"filename": os.path.basename(pro), "version": 3})
    json.dump(d, open(pro, "w"), indent=2)


# ------------------------------------------------------------------ routing helpers
LAYER = {"F": pcbnew.F_Cu, "1": pcbnew.In1_Cu, "2": pcbnew.In2_Cu, "B": pcbnew.B_Cu}


class Router:
    def __init__(self, board, fps, netinfo):
        self.b, self.fps, self.ni = board, fps, netinfo

    def pad(self, ref):
        r, n = ref.split(".")
        for p in self.fps[r].Pads():
            if p.GetNumber() == n:
                return p
        raise KeyError(ref)

    def pt(self, q):
        if isinstance(q, str):
            q = (q, 0, 0)
        if isinstance(q[0], str):
            p = self.pad(q[0]).GetPosition()
            return p.x / 1e6 + q[1], p.y / 1e6 + q[2]
        return q

    def net_of(self, pts, net):
        if net:
            return self.ni[net]
        for q in pts:
            ref = q if isinstance(q, str) else q[0] if isinstance(q[0], str) else None
            if ref:
                return self.pad(ref).GetNet()
        if getattr(self, "last", None) is not None:
            return self.last  # continuation of the previous track / via
        raise ValueError(f"no net for {pts}")

    def t(self, layer, w, *pts, net=None):
        """track through the given points; strings / (ref, dx, dy) snap to pads.
        Drawn later by flush(): only 0/45/90 deg directions, every bend <= 45 deg."""
        ni = self.net_of(pts, net)
        self.last = ni
        xy = [self.pt(q) for q in pts]
        self.pending.append((layer, w, xy, ni))
        return xy[-1]

    pending = []

    def flush(self):
        import math
        # points where other tracks attach must stay where they are
        pinned = set()
        for _l, _w, xy, _n in self.pending:
            pinned.add((round(xy[0][0], 4), round(xy[0][1], 4))); pinned.add((round(xy[-1][0], 4), round(xy[-1][1], 4)))
        for layer, w, xy, ni in self.pending:
            o = split_at(octilinear(xy, w, pinned), pinned)
            for a, b in zip(o, o[1:]):
                if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6:
                    continue
                tr = pcbnew.PCB_TRACK(self.b)
                tr.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); tr.SetEnd(pcbnew.VECTOR2I(MM(b[0]), MM(b[1])))
                tr.SetWidth(MM(w)); tr.SetLayer(LAYER[layer]); tr.SetNet(ni)
                self.b.Add(tr)
        self.pending = []

    def v(self, q, net=None, d=0.5, h=0.3):
        x, y = self.pt(q)
        if net:
            ni = self.ni[net]
        elif isinstance(q, str) or isinstance(q[0], str):
            ni = self.net_of([q], None)
        else:
            ni = self.last  # via at the end of the previous track
        via = pcbnew.PCB_VIA(self.b)
        via.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); via.SetWidth(MM(d)); via.SetDrill(MM(h))
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNet(ni)
        self.b.Add(via)
        return x, y

    def gnd(self, padref, dx, dy, w=0.4, d=0.5):
        """GND pad -> short stub -> own via down to In1"""
        x, y = self.pt(padref)
        self.t("F", w, padref, (x + dx, y + dy))
        self.v((x + dx, y + dy), net="GND", d=d)

    def drop(self, padref, dx, dy, w=0.4, d=0.6):
        """power pad -> stub -> via (to the In2 power trace / other layers)"""
        x, y = self.pt(padref)
        n = self.pad(padref).GetNetname()
        self.t("F", w, padref, (x + dx, y + dy))
        self.v((x + dx, y + dy), net=n, d=d)
        return x + dx, y + dy


# ------------------------------------------------------------------ 45 degree geometry
def _ang(a, b):
    import math
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def _turn(d1, d2):
    return abs((d2 - d1 + 180) % 360 - 180)


def _is_oct(a, b):
    dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
    return min(dx, dy) < 0.02 or abs(dx - dy) < 0.02


def octilinear(xy, w, pinned=()):
    """1) split every off-angle segment into straight + 45 deg (knee side chosen for the smaller bends),
    2) chamfer every 90 deg corner into two 45 deg bends (pinned junction points stay)."""
    import math
    pts = [xy[0]]
    for i, (a, b) in enumerate(zip(xy, xy[1:])):
        if _is_oct(a, b) or (abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6):
            pts.append(b); continue
        dx, dy = b[0] - a[0], b[1] - a[1]
        sx, sy = math.copysign(1, dx), math.copysign(1, dy)
        m = min(abs(dx), abs(dy))
        k1 = (a[0] + sx * m, a[1] + sy * m)          # 45 deg first
        k2 = (b[0] - sx * m, b[1] - sy * m)          # straight first
        prev = _ang(pts[-2], a) if len(pts) >= 2 else None
        nxt = _ang(b, xy[i + 2]) if i + 2 < len(xy) else None
        def cost(k):
            c = 0
            if prev is not None: c = max(c, _turn(prev, _ang(a, k)))
            if nxt is not None: c = max(c, _turn(_ang(k, b), nxt))
            return c
        pts.append(k1 if cost(k1) <= cost(k2) else k2); pts.append(b)
    # drop zero-length / collinear points
    clean = [pts[0]]
    for q in pts[1:]:
        if math.hypot(q[0] - clean[-1][0], q[1] - clean[-1][1]) > 1e-6:
            clean.append(q)
    pts = clean
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, p, b = out[-1], pts[i], pts[i + 1]
        t = _turn(_ang(a, p), _ang(p, b))
        key = (round(p[0], 4), round(p[1], 4))
        if t > 45.5 and t < 90.5 and key not in pinned:
            lin, lout = math.hypot(p[0] - a[0], p[1] - a[1]), math.hypot(b[0] - p[0], b[1] - p[1])
            c = min(max(0.4, 1.2 * w), 0.45 * lin, 0.45 * lout)
            out.append((p[0] - (p[0] - a[0]) / lin * c, p[1] - (p[1] - a[1]) / lin * c))
            out.append((p[0] + (b[0] - p[0]) / lout * c, p[1] + (b[1] - p[1]) / lout * c))
        else:
            out.append(p)
    out.append(pts[-1])
    return out


def split_at(pts, pinned):
    """insert junction points that lie on a segment as vertices (T/Y-joins end on a vertex, not mid-track)"""
    import math
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        hits = []
        for q in pinned:
            if L < 1e-6:
                break
            t = ((q[0] - a[0]) * (b[0] - a[0]) + (q[1] - a[1]) * (b[1] - a[1])) / L ** 2
            if 1e-4 < t < 1 - 1e-4:
                px, py = a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
                if math.hypot(px - q[0], py - q[1]) < 0.003:
                    hits.append((t, q))
        out += [q for _t, q in sorted(hits)] + [b]
    return out


def zone(board, netinfo, layer, net, pts, prio=0, clearance=0.2, minw=0.2, thermal=True):
    z = pcbnew.ZONE(board)
    z.SetLayer(LAYER[layer]); z.SetNet(netinfo[net])
    ol = z.Outline(); ol.NewOutline()
    for x, y in pts:
        ol.Append(MM(x), MM(y))
    z.SetAssignedPriority(prio)
    z.SetLocalClearance(MM(clearance)); z.SetMinThickness(MM(minw))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL if thermal else pcbnew.ZONE_CONNECTION_FULL)
    z.SetThermalReliefGap(MM(0.25)); z.SetThermalReliefSpokeWidth(MM(0.4))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    board.Add(z)
    return z


HOLES = [(20.4, 14.8), (42.2, 42.5)]  # 2x M2 ISO 7380 (button head 3.5 mm), diagonal
HOLE_HEAD = 1.75     # courtyard radius = screw head
HOLE_KEEPOUT = 1.85  # radius without copper on all layers

USB_TUNE = 3.434  # mm added to D+ between module and U12 (D- runs around the outside)

OWN_MODELS = {"JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
              "JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal"}

LABELS = [  # front silk, horizontal, next to the connector, clear of pads and bodies (tools/silk.py): (x, y, text, height, angle)
    (11.2, 5.35, "AKKU", 0.8, 0), (4.2, 15.59, "LED1", 0.8, 0), (4.2, 17.04, "TSOP", 0.8, 0),
    (4.2, 24.24, "ABZUG", 0.8, 0), (4.2, 30.04, "NACHL.", 0.8, 0), (2.23, 40.15, "RESET", 0.8, 0),
    (5.28, 45.05, "WS2812", 0.8, 0), (24.1, 35.55, "USB", 0.8, 0), (35.0, 38.5, "SENSOR", 0.8, 0),
    (48.6, 35.8, "LAUTSPR.", 0.8, 0), (49.85, 21.78, "VIB", 0.8, 0),
    (31.1, 22.1, "BOOT", 0.8, 0), (56.95, 9.54, "OLED", 0.8, 0), (56.95, 17.54, "GEBER", 0.8, 0), (30.55, 40.1, "1", 0.8, 0), (19.5, 17.9, "open-lasertag v1", 0.8, 0),
]
BACK_LABELS = [  # no room on the front
    (41.5, 16.0, "github.com/G5K-org/open-lasertag", 0.8, 0),
]


def stitch(board, netinfo, pitch=2.0, d=0.5, cl=0.25):
    """GND stitching vias on a grid wherever there is room (checked against every other copper item)"""
    import math
    obst = []  # (kind, geometry, half width)
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition(); obst.append(("c", (p.x / 1e6, p.y / 1e6), t.GetWidth(pcbnew.F_Cu) / 2e6 + 0.15))
        else:
            a, b = t.GetStart(), t.GetEnd()
            obst.append(("s", (a.x / 1e6, a.y / 1e6, b.x / 1e6, b.y / 1e6), t.GetWidth() / 2e6))
    boxes = []
    for f in board.GetFootprints():
        for pad in f.Pads():
            bb = pad.GetBoundingBox()
            boxes.append((bb.GetLeft() / 1e6, bb.GetTop() / 1e6, bb.GetRight() / 1e6, bb.GetBottom() / 1e6))
        if f.GetReference() != "U4":
            cy = f.GetCourtyard(pcbnew.F_CrtYd).BBox()
            boxes.append((cy.GetLeft() / 1e6 + 0.3, cy.GetTop() / 1e6 + 0.3, cy.GetRight() / 1e6 - 0.3, cy.GetBottom() / 1e6 - 0.3))
    for t in board.GetDrawings():  # keep labels readable: no stitching via under silk text
        if isinstance(t, pcbnew.PCB_TEXT):
            bb = t.GetEffectiveTextShape().BBox()
            boxes.append((bb.GetLeft() / 1e6, bb.GetTop() / 1e6, bb.GetRight() / 1e6, bb.GetBottom() / 1e6))
    r0 = d / 2 + cl
    def segd(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        L = dx * dx + dy * dy
        u = 0 if L == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L))
        return math.hypot(px - x1 - u * dx, py - y1 - u * dy)
    n = 0
    y = 1.2
    while y < H - 1.0:
        x = 1.2
        while x < W - 1.0:
            ok = not (x > W0 - 1.0 and y > Y1 - 1.0) and all(not (bx0 - r0 < x < bx1 + r0 and by0 - r0 < y < by1 + r0) for bx0, by0, bx1, by1 in boxes)
            if ok:
                for kind, g, hw in obst:
                    dist = math.hypot(x - g[0], y - g[1]) if kind == "c" else segd(x, y, *g)
                    if dist < r0 + hw:
                        ok = False
                        break
            if ok:
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(d)); v.SetDrill(MM(0.3))
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(netinfo["GND"]); board.Add(v)
                obst.append(("c", (x, y), d / 2 + 0.15))
                n += 1
            x += pitch
        y += pitch
    return n


def teardrops(board, len_ratio=0.5, width_ratio=0.9, max_len=1.0, max_w=2.0):
    """straight teardrops at every track end that sits on a pad or via (KiCad-style ratios)"""
    import math
    items = [(pd, pd.GetNetCode()) for f in board.GetFootprints() for pd in f.Pads()]
    vias = [v for v in board.GetTracks() if v.GetClass() == "PCB_VIA"]
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    n = 0
    for t in tracks:
        L = t.GetLayer()
        if t.GetNetname() == "GND" and L == pcbnew.F_Cu:
            continue  # GND stubs sit inside the GND pour, which already joins pad and track
        for e, o in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
            host = None
            for v in vias:
                if v.GetNetCode() == t.GetNetCode() and (v.GetPosition() - e).EuclideanNorm() < v.GetWidth(pcbnew.F_Cu) / 2:
                    host, size = v, v.GetWidth(pcbnew.F_Cu) / 1e6
            if host is None:
                for pd, nc in items:
                    if nc == t.GetNetCode() and pd.IsOnLayer(L) and pd.HitTest(e):
                        host, size = pd, min(pd.GetSize().x, pd.GetSize().y) / 1e6
                        break
            if host is None:
                continue
            w = t.GetWidth() / 1e6
            W = min(width_ratio * size, max_w)
            if w >= 0.9 * W:
                continue
            ex, ey, ox, oy = e.x / 1e6, e.y / 1e6, o.x / 1e6, o.y / 1e6
            seg = math.hypot(ox - ex, oy - ey)
            if seg < 1e-3:
                continue
            ux, uy = (ox - ex) / seg, (oy - ey) / seg
            nx, ny = -uy, ux
            # distance from the track end to the copper edge of the host along the track
            R = 0.0
            while R < seg and host.HitTest(pcbnew.VECTOR2I(MM(ex + ux * R), MM(ey + uy * R))):
                R += 0.02
            Ltd = min(len_ratio * size, max_len)
            if R + Ltd > seg - 0.05:
                Ltd = seg - 0.05 - R
            if Ltd < 0.15 or R >= seg:
                continue
            ax, ay = ex + ux * (R + Ltd), ey + uy * (R + Ltd)
            bx, by = ex + ux * R * 0.5, ey + uy * R * 0.5
            poly = [(ax + nx * w / 2, ay + ny * w / 2), (bx + nx * W / 2, by + ny * W / 2), (ex, ey),
                    (bx - nx * W / 2, by - ny * W / 2), (ax - nx * w / 2, ay - ny * w / 2)]
            z = pcbnew.ZONE(board)
            z.SetLayer(L); z.SetNetCode(t.GetNetCode())
            ol = z.Outline(); ol.NewOutline()
            for x, y in poly:
                ol.Append(MM(x), MM(y))
            z.SetZoneName("$teardrop_padvia$"); z.SetAssignedPriority(30000)
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL); z.SetMinThickness(MM(0.0254))
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
            board.Add(z)
            n += 1
    return n


def labels(board):
    for (x, y, txt, h, ang), back in [(l, False) for l in LABELS] + [(l, True) for l in BACK_LABELS]:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt); t.SetLayer(pcbnew.B_SilkS if back else pcbnew.F_SilkS); t.SetMirrored(back)
        t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); t.SetTextAngleDegrees(ang)
        t.SetTextSize(pcbnew.VECTOR2I(MM(h), MM(h))); t.SetTextThickness(MM(0.15 if h >= 1 else 0.12))
        board.Add(t)


def meander_v(x, y0, extra, n=3, c=0.2, t=0.2, gap=0.6, side=1):
    """Points of a length-tuning meander on a vertical run going down (+y) at x.
    n bumps to the side (+1 right, -1 left), only 45 deg bends: each bump is
    diagonal - straight out - diagonal - down - diagonal - straight back - diagonal.
    Bump height h gives the extra length 2h - 4c(2 - sqrt2) per bump."""
    import math
    h = (extra / n + 4 * c * (2 - math.sqrt(2))) / 2
    pts, y = [], y0
    for _ in range(n):
        pts += [(x, y), (x + side * c, y + c), (x + side * (h - c), y + c), (x + side * h, y + 2 * c),
                (x + side * h, y + 2 * c + t), (x + side * (h - c), y + 3 * c + t),
                (x + side * c, y + 3 * c + t), (x, y + 4 * c + t)]
        y += 4 * c + t + gap
    return pts


def route(r):
    """Hand routing. Coordinates in mm, board origin top-left."""
    F, B, I2 = "F", "B", "2"
    # ================= boost converter (MT3608): tight loops on F.Cu =================
    # input: BT1 -> C19 -> U1 IN/EN, L1
    r.t(F, 0.8, "BT1.1", "C19.1")
    r.t(F, 0.6, "C19.1", ("U1.5", -0.3, 0), "U1.5")
    r.t(F, 0.4, "U1.5", "U1.4")
    r.t(F, 0.8, "C19.1", (11.2, 4.9), ("L1.1", 0, -1.2))
    r.gnd("C19.2", -1.0, -0.6); r.gnd("BT1.2", -1.55, 0); r.v((5.4, 6.2), net="GND")
    # switch node: U1 SW -> D3 anode and L1 (short and wide)
    r.t(F, 1.0, "U1.1", ("D3.2", -0.6, 0))
    r.t(F, 1.0, "U1.1", (15.3, 4.9), ("L1.2", 0, -1.2))
    r.gnd("U1.2", 0.85, -0.3)
    # output: D3 -> C20, divider R24/R25 -> FB
    r.t(F, 0.8, ("D3.1", -0.6, 0.6), ("C20.1", 0, -0.5), "C20.1")
    r.gnd("C20.2", -0.95, 0)
    r.t(F, 0.4, "D3.1", "R24.1")
    r.t(F, 0.25, "U1.3", (18.1, 2.25), ("R25.1", -0.3, 0.45), "R25.1", "R24.2")
    r.gnd("R25.2", -0.7, -0.55)
    r.t(F, 0.6, "C20.1", (21.3, 5.95)); r.v((21.3, 5.95), net="5V_PERIPH", d=0.6)
    # ================= LDO + module supply =================
    r.t(F, 0.8, "U2.3", (29.9, 12.55), (29.9, 12.0)); r.v((29.9, 12.0), net="5V_PERIPH", d=0.6)
    r.t(F, 0.8, (29.9, 12.0), (30.65, 12.75), "C2.1", net="5V_PERIPH")
    r.gnd("C2.2", 0, -0.95); r.gnd("U2.1", -1.2, 0.3)
    # 3V3: LDO tab -> C3 -> R21 -> C18 (10u) -> C17 (100n) -> module pin 2
    r.t(F, 0.8, ("U2.2", 0, -0.8), (26.3, 4.84), (28.09, 3.05), "C18.1")
    r.t(F, 0.6, "C18.1", "C17.1", "U4.2")
    r.t(F, 0.6, "C3.1", (26.3, 4.84))
    r.gnd("C3.2", -1.0, -0.8)
    r.t(F, 0.5, "C18.2", "C17.2", "U4.1")
    r.v((28.8, 1.1), net="GND"); r.t(F, 0.5, (28.8, 1.1), "C18.2")
    r.v((32.85, 0.6), net="GND"); r.t(F, 0.4, (32.85, 0.6), "C17.2")
    # EN: R21 / C16 RC right at pin 3
    r.t(F, 0.25, "R21.2", "C16.1", (31.3, 4.03), "U4.3")
    r.gnd("C16.2", 0, 1.12)
    # 3V3 also leaves from the LDO's lower tab pin into the In2 3V3 tree
    r.v((26.3, 15.0), net="3V3_MCU", d=0.6)

    # ================= left-pin signals: vias next to the module, long runs on B.Cu =================
    # order top->bottom (EN, TRIGGER, RELOAD, IR_GATE, WS2812) = order of the targets, so no crossings
    r.v((29.4, 4.73), net="Net-(U4-EN)")
    r.t(B, 0.25, (29.4, 4.73), (29.4, 4.0), (25.35, 4.0), (7.0, 22.35), (7.0, 40.9), net="Net-(U4-EN)")
    r.v((7.0, 40.9), net="Net-(U4-EN)"); r.t(F, 0.25, (7.0, 40.9), ("SW3.2", 0, -0.5), "SW3.2")
    for pin, yy, xd, end in (("U4.4", 5.30, 7.8, (7.8, 25.65)), ("U4.5", 6.57, 8.6, None), ("U4.6", 7.84, 13.0, None)):
        r.t(F, 0.25, pin, (32.25, yy)); r.v((32.25, yy))
    r.t(B, 0.25, (32.25, 5.30), (24.95, 5.30), (7.8, 22.45), (7.8, 25.65), net="TRIGGER"); r.v((7.8, 25.65), net="TRIGGER")
    r.t(F, 0.25, "C8.1", (7.8, 25.65), "R9.2", "SW1.1")
    r.t(B, 0.25, (32.25, 6.57), (24.58, 6.57), (8.6, 22.55), (8.6, 30.85), (7.8, 31.65), net="RELOAD"); r.v((7.8, 31.65), net="RELOAD")
    r.t(F, 0.25, "C9.1", (7.8, 31.65), "R10.2", "SW2.1")
    r.t(B, 0.25, (32.25, 7.84), (24.21, 7.84), (13.1, 18.95), net="IR_GATE"); r.v((13.1, 18.95), net="IR_GATE")
    r.t(F, 0.25, (13.1, 18.95), "R5.1")
    r.t(F, 0.25, "U4.10", (32.4, 12.92)); r.v((32.4, 12.92))
    r.t(B, 0.25, (32.4, 12.92), (26.88, 12.92), (11.6, 28.2), net="WS2812_DIN_3V3")
    r.v((11.6, 28.2), net="WS2812_DIN_3V3"); r.t(F, 0.25, (11.6, 28.2), "U5.2")

    # ================= IR driver =================
    K = "Net-(LED1-K)"
    r.t(F, 0.6, "R7.2", "LED1.2")
    # LED1 cathode hops under its own anode trace on B.Cu
    r.t(F, 0.6, "LED1.1", (5.3, 12.3), (6.0, 11.6)); r.v((6.0, 11.6), net=K, d=0.6)
    r.t(B, 0.6, (6.0, 11.6), (6.0, 15.65), net=K); r.v((6.0, 15.65), net=K, d=0.6)
    r.t(F, 0.8, (6.0, 15.65), "C7.2")
    r.t(F, 0.8, "Q1.3", "C7.2")
    r.t(F, 0.3, "Q1.1", "R5.2"); r.t(F, 0.3, "R6.1", (11.95, 20.05))
    r.gnd("Q1.2", 0.65, -0.55); r.gnd("R6.2", 0, -0.85)
    # BAT: L1 -> R7 -> C7, bus on the right down to R8 and on to the charger
    r.t(F, 0.8, ("L1.1", 0, 1.0), "R7.1", (10.28, 14.4), "C7.1")
    r.t(F, 1.0, "R7.1", (14.3, 16.187), (14.3, 20.6))
    r.t(F, 0.8, (14.3, 20.6), (18.68, 24.98), "C5.1", (20.4, 24.98), ("U3.3", -0.3, 0.05), "U3.3")

    # ================= TSOP 6 on the weapon (J6: 1 VS, 2 GND, 3 OUT) =================
    r.t(F, 0.3, "J6.1", (6.0, 19.6), (6.4, 19.2)); r.v((6.4, 19.2), net="3V3_MCU")
    r.t(I2, 0.4, (17.18, 19.7), (6.9, 19.7), (6.4, 19.2), net="3V3_MCU")  # branch off the In2 3V3 diagonal
    r.gnd("J6.2", 1.5, 0)
    # OUT: IO16 -> B.Cu channel between the IR and WS2812 diagonals -> F.Cu into the bottom pin
    r.t(F, 0.2, "U4.9", (32.25, 11.65)); r.v((32.25, 11.65))
    # diagonal x + y = 38.0: between the H1 keep-out and the R2 3V3 via
    r.t(B, 0.2, (32.25, 11.65), (31.0, 10.4), (27.6, 10.4), (14.3, 23.7), net="TSOP6_OUT"); r.v((14.3, 23.7), net="TSOP6_OUT")
    r.t(F, 0.2, (14.3, 23.7), (7.2, 23.7), (5.3, 21.8), "J6.3")

    # ================= trigger / reload / reset =================
    r.gnd("C8.2", 0.85, 0); r.gnd("C9.2", 0.85, 0)
    r.gnd("SW1.2", 1.2, 0.4); r.gnd("SW2.2", 1.2, 0.4); r.gnd("SW3.1", 0, -1.2)
    r.drop("R9.1", 0, 0.95); r.drop("R10.1", 0, 0.95)

    # ================= WS2812 level shifter =================
    r.t(F, 0.25, "U5.3", (12.2, 28.85), (11.0, 30.05), "R15.1")
    r.t(F, 0.4, "R15.2", (11.0, 35.6), "J1.1")
    for pins, via in ((("U5.1",), (14.7, 27.55)), (("U5.4", "U5.5"), (14.7, 30.15)), (("U5.7",), (14.7, 31.45)),
                      (("U5.12", "U5.13"), (17.3, 28.2)), (("U5.9", "U5.10"), (17.3, 30.15))):
        r.t(F, 0.3, *pins, via, net="GND")
        r.v(via, net="GND")
    r.t(F, 0.5, "U5.14", (20.1, 27.55), "C21.1"); r.gnd("C21.2", 0.9, 0)
    r.drop("C21.1", 0.95, 0.5)
    r.t(F, 0.8, "J1.2", (13.0, 36.6), (15.6, 34.0), "C10.1")
    r.gnd("J1.3", 0, -2.3); r.gnd("C10.2", 0, 2.0)
    r.drop("C10.1", 0, -1.9)

    # ================= charger (MCP73831) + battery divider =================
    r.t(F, 0.25, "U4.11", (31.7, 14.19), (30.2, 15.69), (25.6, 15.69), (21.363, 19.927), "U3.1")
    r.t(F, 0.25, "R2.2", ("R2.2", 0.32, 0), ("R2.2", 0.645, 0.325), "U3.1")
    r.drop("R2.1", 0, -0.87)
    r.t(F, 0.25, "U3.5", "R1.1")
    r.t(F, 0.4, "R1.2", (26.35, 21.2), "R4.2"); r.v((26.35, 21.2), net="GND")
    r.t(F, 0.5, "U3.4", "C4.1"); r.gnd("C4.2", 0.95, 0)
    r.t(F, 0.5, "U3.2", (20.03, 23.0), "C5.2"); r.v((18.7, 22.8), net="GND"); r.t(F, 0.4, "C5.2", (18.7, 22.8))
    r.t(F, 0.25, "U4.12", (31.365, 15.46), "C6.1")
    r.t(F, 0.25, "C6.1", (28.25, 17.82), (27.3, 18.77), "R4.1")
    r.t(F, 0.25, "R4.1", ("R4.1", -0.28, -0.28), "R3.2")
    r.gnd("C6.2", -0.7, 1.0)
    r.drop("R3.1", 0, -0.85)

    # ================= USB: pair 0.2/0.2, 45 deg into the ESD chip =================
    r.t(F, 0.2, "U4.13", (31.3, 16.73), (30.85, 17.18), (30.85, 23.5), (25.6, 28.75), (23.6, 28.75), (23.15, 29.2), "U12.6")
    # D+ is the inner line of the pair: meander makes it as long as D- (tools/pairlen.py)
    r.t(F, 0.2, "U4.14", (31.25, 18.0), *meander_v(31.25, 18.9, USB_TUNE), (31.25, 23.66), (25.05, 29.86), "U12.4")
    r.t(F, 0.2, "U12.1", (23.35, 33.3), "J3.B7")
    r.t(F, 0.2, "U12.3", (24.85, 33.3), "J3.B6")
    # A6/A7 row: D+ jumps over A7 on top, D- goes through B.Cu
    r.t(F, 0.2, "J3.A6", (23.85, 36.75), (24.85, 35.75))
    r.t(F, 0.2, "J3.A7", (24.35, 37.45)); r.v((24.35, 37.45), d=0.4, h=0.2, net="Net-(J3-D--PadA7)")
    r.t(B, 0.2, (24.35, 37.45), (23.35, 36.4), net="Net-(J3-D--PadA7)"); r.v((23.35, 36.4), d=0.4, h=0.2, net="Net-(J3-D--PadA7)")
    r.gnd("U12.2", 0, 0.9)
    # CC pull-downs
    r.t(F, 0.25, "J3.A5", (22.85, 37.675), "R23.1"); r.gnd("R23.2", 0, -0.9)
    r.t(F, 0.25, "J3.B5", (25.85, 37.0), "R22.1"); r.gnd("R22.2", 0, -0.9)
    # VBUS: both connector pads -> B.Cu ring -> ESD VBUS pin and charger input
    V = "VBUS_NATIVE"
    for pp, x in (("J3.A4", 21.55), ("J3.A9", 26.65)):
        r.t(F, 0.4, pp, (x, 37.45)); r.v((x, 37.45), net=V)
    r.t(B, 0.4, (21.55, 37.45), (21.55, 35.3), (22.35, 34.5), (25.85, 34.5), (26.65, 35.3), (26.65, 37.45), net=V)
    r.t(B, 0.4, (25.1, 34.5), (25.6, 34.0), (25.6, 25.5), (25.4, 25.3), net=V); r.v((25.4, 25.3), net=V)
    r.t(F, 0.4, (25.4, 25.3), "C4.1")
    r.t(B, 0.4, (25.6, 30.1), (24.85, 29.35), (24.1, 29.35), net=V); r.v((24.1, 29.35), net=V)
    r.t(F, 0.3, (24.1, 29.35), "U12.5")
    for pp, x in (("J3.A1", 20.75), ("J3.A12", 27.45)):
        r.t(F, 0.4, pp, (x, 37.45)); r.v((x, 37.45), net="GND")

    # ================= BOOT button: IO0 runs under the module on B.Cu =================
    r.t(F, 0.25, "U4.27", (49.85, 17.6)); r.v((49.85, 17.6))
    r.t(B, 0.25, (49.85, 17.6), (39.85, 17.6), (36.7, 20.75)); r.v((36.7, 20.75))
    r.t(F, 0.25, (36.7, 20.75), "SW4.2")
    r.gnd("SW4.1", 0, 1.4)

    # ================= TSOP 1-5: via under each pad, 45 deg on B.Cu, straight down to J2 =================
    for k, (pin, X) in enumerate((("U4.18", 34.0), ("U4.19", 35.0), ("U4.20", 36.0), ("U4.21", 37.0), ("U4.22", 38.0))):
        x0 = r.pt(pin)[0]
        r.t(F, 0.2, pin, (x0, 20.75)); r.v((x0, 20.75))
        d = x0 - X
        r.t(B, 0.2, (x0, 20.75), (X, 20.75 + d), (X, 39.4)); r.v((X, 39.4))
        r.t(F, 0.2, (X, 39.4), f"J2.{k + 3}")
    r.t(F, 0.4, "J2.2", (33.0, 39.4)); r.v((33.0, 39.4), net="GND")
    # sensor 3V3: B.Cu from the LDO's lower pin straight down to J2 pin 1
    r.t(B, 0.4, (26.3, 15.0), (29.5, 18.2), (29.5, 36.9), (32.0, 39.4), net="3V3_MCU")
    r.v((32.0, 39.4), net="3V3_MCU", d=0.6); r.t(F, 0.4, (32.0, 39.4), "J2.1")

    # ================= vibration drivers =================
    # one motor for recoil and hit feedback (IO47)
    r.t(F, 0.25, "U4.24", "R11.1")
    r.t(F, 0.25, "R11.2", (44.61, 21.75), "Q2.1")
    r.t(F, 0.25, "R12.1", (44.0, 22.68), "Q2.1")
    r.t(F, 0.5, "Q2.3", "M1.2"); r.t(F, 0.5, "D1.2", (46.7, 24.25))
    r.t(F, 0.4, "Q2.2", (43.6, 25.4)); r.t(F, 0.4, "R12.2", (43.6, 25.4)); r.v((43.6, 25.4), net="GND")
    r.drop("D1.1", 0, 1.05); r.drop("M1.1", -1.3, 0.3)

    # ================= I2S: three lines beside the module, then diagonal to the amp =================
    # down the column beside the module, then one 45 deg run straight into the amp (x + y = const)
    for pin, col, c, ycol, d, tail in (("U4.31", 52.45, 71.85, 50.15, 76.55, [(42.55, 34.0), "U6.1"]),
                                       ("U4.32", 52.95, 72.45, 50.65, 79.45, [(43.9, 35.55), "U6.16"]),
                                       ("U4.33", 53.45, 73.05, 51.15, 80.45, [(43.9, 36.55), "U6.14"])):
        y0 = r.pt(pin)[1]
        r.t(F, 0.2, pin, (col, y0), (col, c - col), (ycol, c - ycol), (ycol, d - ycol), *tail)

    # ================= audio amp =================
    for pp, to in (("U6.3", (41.55, 35.7)), ("U6.2", (42.05, 35.7)), ("U6.15", (42.4, 36.05)), ("U6.11", (42.05, 36.9))):
        r.t(F, 0.25, pp, to)
    r.v("U6.17", net="GND")
    r.t(F, 0.4, "U6.7", "U6.8", "C23.1")
    r.t(F, 0.25, "U6.4", (41.05, 34.25), (39.6, 34.25), (39.6, 36.3), (39.95, 36.65))
    r.gnd("C23.2", 0, -0.82)
    r.drop("C23.1", 0, 0.92)
    r.t(F, 0.25, "U6.10", (41.55, 38.45)); r.t(F, 0.4, (41.55, 38.45), (41.85, 38.75), (46.4, 38.75)); r.v((46.4, 38.75))
    r.t(B, 0.4, (46.4, 38.75), (50.5, 38.75), net="Net-(U6-OUTN)"); r.v((50.5, 38.75), net="Net-(U6-OUTN)")
    r.t(F, 0.4, (50.5, 38.75), "SP1.2")
    r.t(F, 0.25, "U6.9", (41.05, 39.2)); r.t(F, 0.4, (41.05, 39.2), (41.45, 39.6), (47.35, 39.6), net="Net-(U6-OUTP)")
    r.gnd("C22.2", 1.0, 0); r.drop("C22.1", -1.0, 0)
    r.gnd("C1.2", 0, -1.42); r.drop("C1.1", 0, 1.42)

    # ================= module GND pad 40 =================
    r.gnd("U4.40", 1.45, 0)

    # ================= In2: 5V / 3V3 / BAT distribution =================
    P5 = "5V_PERIPH"
    r.t(I2, 0.8, (21.3, 5.95), (23.85, 5.95), (29.9, 12.0), (30.2, 12.3), (30.2, 29.39), (32.2, 31.39), net=P5)
    r.t(I2, 0.6, (30.2, 27.4), (29.6, 28.0), (22.28, 28.0), (21.8, 28.48), (20.05, 28.48), (16.43, 32.1), net=P5)
    r.t(I2, 0.6, (32.2, 31.39), (40.51, 31.39), (46.3, 25.6), (47.6, 25.6), net=P5)  # through the D1 via to the motor
    r.t(I2, 0.6, (34.0, 31.39), (34.51, 31.9), (34.51, 34.95), (38.06, 38.5), (38.9, 38.5), net=P5)
    r.t(I2, 0.6, (34.51, 34.6), (33.76, 35.35), (31.4, 35.35), (31.3, 35.45), net=P5)
    # ================= OLED (J4, Qwiic: GND 3V3 SDA SCL) and rotary encoder (J5: GND SW B A) =================
    r.t(F, 0.2, "U4.39", (52.15, 2.76), (53.39, 4.0), "J4.4")          # I2C_SCL
    r.t(F, 0.2, "U4.38", (52.3, 4.03), (53.27, 5.0), "J4.3")           # I2C_SDA
    r.t(F, 0.3, "J4.2", (56.2, 6.0)); r.v((56.2, 6.0), net="3V3_MCU")  # 3V3 from In2
    r.t(F, 0.4, "U4.2", (35.0, 2.76)); r.v((35.0, 2.76), net="3V3_MCU")  # module pin 2 -> In2
    r.t(I2, 0.5, (35.0, 2.76), (52.96, 2.76), (56.2, 6.0), net="3V3_MCU")
    r.gnd("J4.1", 1.7, 0)
    r.t(F, 0.2, "U4.35", (52.6, 7.84), (54.0, 9.24), ("J5.4", -0.5, 0))  # ENC_A from above
    r.t(F, 0.2, "U4.34", (52.4, 9.11)); r.v((52.4, 9.11))                # ENC_B over B.Cu
    r.t(B, 0.2, (52.4, 9.11), (52.4, 9.2), (56.2, 13.0), net="ENC_B"); r.v((56.2, 13.0), net="ENC_B")
    r.t(F, 0.2, (56.2, 13.0), "J5.3")
    x17 = r.pt("U4.17")[0]                                                 # ENC_SW from the bottom pad row
    r.t(F, 0.2, "U4.17", (x17, 18.0)); r.v((x17, 18.0))
    r.t(B, 0.2, (x17, 18.0), (x17 + 1.4, 16.6), (53.6, 16.6), (56.2, 14.0), net="ENC_SW"); r.v((56.2, 14.0), net="ENC_SW")
    r.t(F, 0.2, (56.2, 14.0), "J5.2")
    r.gnd("J5.1", 1.7, 0)

    P3 = "3V3_MCU"
    r.t(I2, 0.5, (26.3, 15.0), (19.6, 19.205), (9.425, 27.45), (9.425, 33.45), net=P3)
    r.t(I2, 0.6, ("R3.1", 0, -0.85), (25.38, 18.2), (18.6, 24.98), net="BAT_P"); r.v((18.6, 24.98), net="BAT_P", d=0.6)


def build():
    comps, nets = parse_netlist(NETLIST)
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(MM(1.6))

    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name.lstrip("/")] = ni  # routing code uses the short names
    pad_net = {(r, p): n.lstrip("/") for n, nodes in nets.items() for r, p in nodes}

    fps = {}
    stage_x = W + 10
    for ref, (val, fpid, ts, lcsc) in sorted(comps.items()):
        lib, name = fpid.split(":")
        m = pcbnew.FootprintLoad(f"{FPLIB}/{lib}.pretty", name)
        assert m is not None, fpid
        m.SetFPID(pcbnew.LIB_ID(lib, name))
        if name in OWN_MODELS:  # KiCad has no model for these: own ones (scripts/gen_3d_jst_ph_sm4.py)
            models = m.Models()  # iterating yields copies, indexing edits in place
            for i in range(len(models)):
                models[i].m_Filename = f"${{KIPRJMOD}}/3dmodels/{name}.wrl"
        m.SetPath(pcbnew.KIID_PATH("/" + ts))
        m.SetReference(ref)
        m.SetValue(val)
        if lcsc:  # JLCPCB part number travels with the footprint (BOM/CPL, schematic parity)
            m.SetField("LCSC", lcsc)
            m.GetField("LCSC").SetVisible(False); m.GetField("LCSC").SetLayer(pcbnew.F_Fab)
        # dense board: designators go to the assembly drawing (F.Fab), silk only gets connector labels
        m.Reference().SetLayer(pcbnew.F_Fab)
        m.Reference().SetTextSize(pcbnew.VECTOR2I(MM(0.5), MM(0.5))); m.Reference().SetTextThickness(MM(0.08))
        if ref == "U4":  # antenna overhangs the board edge: drop the module silk beyond it
            for g in list(m.GraphicalItems()):
                if g.GetLayer() == pcbnew.F_SilkS and g.GetBoundingBox().GetTop() < MM(MY - 6.0):
                    m.Remove(g)
        board.Add(m)
        if ref in PLACE:
            x, y, rot = PLACE[ref]
        else:  # not placed yet: park it next to the board
            x, y, rot = stage_x, 5 + 8 * (len(fps) % 10), 0
            if len(fps) % 10 == 9:
                stage_x += 14
        m.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        m.SetOrientationDegrees(rot)
        for pad in m.Pads():
            n = pad_net.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
        fps[ref] = m

    # mounting holes: not plated, no copper under the screw head on any layer
    for i, (x, y) in enumerate(HOLES, 1):
        h = pcbnew.FootprintLoad(f"{FPLIB}/MountingHole.pretty", "MountingHole_2.2mm_M2_ISO7380")
        h.SetFPID(pcbnew.LIB_ID("MountingHole", "MountingHole_2.2mm_M2_ISO7380"))
        h.SetReference(f"H{i}"); h.SetValue("M2")
        h.Reference().SetLayer(pcbnew.F_Fab)
        h.Reference().SetTextSize(pcbnew.VECTOR2I(MM(0.5), MM(0.5))); h.Reference().SetTextThickness(MM(0.08))
        h.SetAttributes(h.GetAttributes() | pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM
                        | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        for g in h.GraphicalItems():  # courtyard = screw head, not the library's extra margin
            if g.GetLayer() == pcbnew.F_CrtYd and g.GetShape() == pcbnew.SHAPE_T_CIRCLE:
                g.SetEnd(g.GetCenter() + pcbnew.VECTOR2I(MM(HOLE_HEAD), 0))
        h.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        board.Add(h)
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
        z.SetLayerSet(pcbnew.LSET.AllCuMask())
        o = z.Outline(); o.NewOutline()
        for k in range(32):
            a = 2 * math.pi * k / 32
            o.Append(MM(x + HOLE_KEEPOUT * math.cos(a)), MM(y + HOLE_KEEPOUT * math.sin(a)))
        z.SetZoneName(f"H{i} keep-out")
        board.Add(z)

    # board outline, 1 mm corner radius
    r = 1.0
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); s.SetEnd(pcbnew.VECTOR2I(MM(b[0]), MM(b[1])))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1)); board.Add(s)
    def arc(c, start, end):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetCenter(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
        s.SetStart(pcbnew.VECTOR2I(MM(start[0]), MM(start[1]))); s.SetEnd(pcbnew.VECTOR2I(MM(end[0]), MM(end[1])))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1)); board.Add(s)
    # L shape, clockwise; arcs run clockwise from start to end
    seg((r, 0), (W - r, 0)); arc((W - r, r), (W - r, 0), (W, r))
    seg((W, r), (W, Y1 - r)); arc((W - r, Y1 - r), (W, Y1 - r), (W - r, Y1))
    seg((W - r, Y1), (W0 + r, Y1)); arc((W0 + r, Y1 + r), (W0, Y1 + r), (W0 + r, Y1))  # inner corner
    seg((W0, Y1 + r), (W0, H - r)); arc((W0 - r, H - r), (W0, H - r), (W0 - r, H))
    seg((W0 - r, H), (r, H)); arc((r, H - r), (r, H), (0, H - r))
    seg((0, H - r), (0, r)); arc((r, r), (0, r), (r, 0))

    rt = Router(board, fps, netinfo)
    route(rt)
    rt.flush()
    labels(board)
    print("stitching vias:", stitch(board, netinfo))
    for it in list(board.GetTracks()) + [pd for f in board.GetFootprints() for pd in f.Pads()]:
        if it.GetClass() in ("PCB_VIA", "PAD"):
            it.SetTeardropsEnabled(True)
    print("teardrops:", teardrops(board))
    # planes: In1 solid GND; GND fill on F/In2/B around the routing
    edge = [(0, 0), (W, 0), (W, Y1), (W0, Y1), (W0, H), (0, H)]
    zone(board, netinfo, "1", "GND", edge, thermal=False)
    for L in ("F", "2", "B"):
        zone(board, netinfo, L, "GND", edge)
    # copper island on the LDO tab as heat spreader (3V3)
    zone(board, netinfo, "F", "3V3_MCU", [(23.2, 4.9), (29.2, 4.9), (29.2, 9.3), (23.2, 9.3)], prio=1, thermal=False)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(OUT, board)
    # KiCad ships no STEP for the EP1.23 TQFN: same 3x3 body with the EP1.6 model
    t = open(OUT).read().replace("TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm.step", "TQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm.step")
    # mark the generated teardrop zones as KiCad teardrops (enum not exposed to Python)
    t = t.replace('(name "$teardrop_padvia$")', '(name "$teardrop_padvia$")\n\t\t(attr\n\t\t\t(teardrop\n\t\t\t\t(type padvia)\n\t\t\t)\n\t\t)')
    open(OUT, "w").write(t)
    write_project(OUT)
    unplaced = sorted(set(comps) - set(PLACE))
    print(f"saved {OUT}  ({len(comps)} parts, {len(unplaced)} unplaced)")
    return board, fps


if __name__ == "__main__":
    build()
