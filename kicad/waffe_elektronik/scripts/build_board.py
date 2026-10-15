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
W, Y1 = 59.6, 18.5   # width W except the notch x > W0, Y1 < y < Y2 (M1 cable)
Y2 = 26.5            # below the notch the board is W wide again (J2 at the edge, TSOP resistors)
XT, YT = 18.6, 9.0   # tab top left (x < XT, -YT < y < 0): battery protection, on/off above it; ends left of the
                     # antenna keep-out of the module (x >= 18.5 for y < 0)
OUTLINE = [(0, -YT), (XT, -YT), (XT, 0), (W, 0), (W, Y1), (W0, Y1), (W0, Y2), (W, Y2), (W, H), (0, H)]


def on_board(x, y, m):
    """point at least m inside the outline (rectangles, ignoring the corner radii)"""
    if m <= x <= XT - m and -YT + m <= y <= H - m:
        return True
    if not (m <= y <= H - m and m <= x <= W - m):
        return False
    return not (x > W0 - m and Y1 - m < y < Y2 + m)
MX, MY = W0 - 11.5, 6.75  # ESP32 module origin; board top edge = antenna keep-out line
SH_IN = 3.1     # JST-SH horizontal: body front this far from origin -> flush with board edge
PH_IN = 4.9     # JST-PH SM4 horizontal

JX, JY = 28.2, 41.0   # USB-C, vertical (hanxia HX-TYPE-C 16P 180 LT H10.5): flush with the outer wall
PROJ_FPLIB = os.path.join(PROJ, "footprints")  # footprint libraries of this project (fp-lib-table)

# ------------------------------------------------------------------ placement
# ref: (x, y, rotation_deg)  - board coords, mm, origin top-left, y down.
# Connector rotation: 0 = opening faces down, 90 = right, 180 = up, 270 = left.
PLACE = {
    "U4": (MX, MY, 0),
    # --- power: battery in, IP5306 (charger + boost, SW loop U1.7 - L1 straight), AMS1117
    "BT1": (PH_IN, 5.2, 270),
    "U1": (19.6, 3.5, 180), "L1": (12.95, 6.185, 270), "C19": (13.9, 10.6, 0),
    "R2": (11.0, 1.4, 270), "C5": (13.4, 1.25, 0),                     # BAT sense filter (1R / 22u)
    "C20": (17.125, 8.1, 270), "U16": (20.3, 8.1, 0),                  # VOUT 22u, load switch right below U1
    "C30": (16.6, 11.35, 270), "C4": (21.6, 11.35, 270),               # VOUT 22u (0603), VIN 10u (0603)
    "R42": (19.0, 11.35, 270), "C33": (20.35, 11.0, 270),              # U16 EN pull-down (IRQ), CT 10n
    "C29": (20.2, 31.0, 180), "R1": (23.2, 31.0, 180),                 # VIN snubber 2R + 10u at the USB VBUS line
    "R40": (27.0, 1.3, 270),                                            # IP_SCL pull-up, 3V3 from R21.1
    "U2": (26.3, 10.7, 90), "C2": (31.2, 11.8, 90), "C3": (25.2, 3.488, 90),
    # --- module: 100n + 10u right at pin 2, EN RC right at pin 3
    "C18": (30.1, 2.1, 90), "C17": (31.95, 2.1, 90), "R21": (28.25, 3.95, 270), "C16": (30.7, 5.3, 270),
    # --- left edge connectors
    "J6": (SH_IN, 18.1, 270),  # J6: IR LED + TSOP 6 at the front of the weapon (1 A, 2 K, 3 GND, 4 3V3, 5 OUT)
    "R36": (12.0, 22.0, 180),    # 10R into the J6 3V3 line
    # --- left edge, lower part: WS2812 and speaker (cables run forward to the barrel)
    "J1": (PH_IN, 29.8, 270), "SP1": (PH_IN, 40.2, 270),
    # --- IR driver
    "R7": (8.6, 12.9, 270), "R8": (10.95, 12.9, 270), "Q1": (8.6, 19.1, 180), "C7": (4.0, 11.4375, 180),
    "R5": (12.3, 20.05, 180), "R6": (11.95, 17.7, 90),
    # --- bottom edge: trigger and reload (cables run along the bottom to the switch), USB-C upright
    "J8": (15.45, H - SH_IN, 0), "J3": (JX, JY, 0),  # J8: trigger + reload switch (1 TRIGGER, 2 GND, 3 RELOAD)
    "R9": (11.675, 37.0, 0), "C8": (13.9, 37.0, 90), "R10": (17.575, 37.0, 0), "C9": (19.8, 37.0, 90),
    # --- right edge: motor, sensor cable below it (both cables run back into the motor channel)
    "M1": (W0 - SH_IN, 23.2, 90), "J2": (W - SH_IN, 32.7, 90),
    # --- right strip: OLED (I2C, Qwiic) above, rotary encoder below
    "J4": (W - SH_IN, 5.5, 90), "J5": (W - SH_IN, 13.5, 90),
    # --- WS2812 level shifter
    "Q4": (13.6, 26.82, 180), "R25": (10.85, 29.025, 90), "R15": (10.85, 26.0, 90),  # Q4 common gate, R25 1k to 5 V
    "C10": (15.57, 33.9, 0), "C32": (15.57, 31.8, 0), "C31": (20.85, 27.2, 90),
    # --- USB: ESD (connector side down) + CC
    "U12": (JX, 31.5, 90), "R23": (JX - 2.325, JY - 3.7, 180), "R22": (JX + 2.325, JY + 3.85, 0),
    # --- battery voltage divider (fed from the IR battery line)
    "R3": (15.6, 16.75, 0), "R4": (18.0, 18.5, 270), "C6": (19.6, 18.5, 270),
    "R38": (38.05, 21.6, 90),                                           # IP_SDA pull-up below IO9
    # --- EN (RESET) / BOOT buttons
    "SW3": (13.8, -7.2, 0), "SW4": (35.0, 22.1, 0), "C1": (32.2, 28.5, 90),
    # --- vibration drivers: top channel HIT (pad 24) -> M2, bottom channel RECOIL (pad 25) -> M1
    "R11": (46.13, 21.05, 180), "Q2": (45.55, 23.95, 0), "R12": (42.75, 23.5, 270), "D1": (45.3, 26.95, 0),
    # --- audio
    "U6": (41.8, 36.0, 270), "C22": (32.3, 34.5, 90), "C23": (38.75, 36.5, 90),
    # --- SPI-NAND (audio files): below the module between C1 and the vibration driver
    "U14": (38.6, 28.7, 0), "C25": (40.3, 24.6, 180), "R27": (36.6, 24.6, 180),
    # --- microSD slot (push-pull): card enters on the contact side, contacts at the bottom edge; 100n above VDD
    "J7": (47.45, 42.1, 0), "C26": (48.0, 37.0, 90), "C28": (49.45, 36.6, 90), "R37": (50.95, 37.1, 90),
    # --- battery protection in the tab above BT1: FS8205A, DW01A (gates face each other), CS resistor between
    "Q3": (4.2, -2.4, 0), "U15": (10.8, -2.4, 0), "R29": (7.78, -2.4, 180), "C27": (13.8, -2.88, 90),
    "R28": (15.1, -1.92, 90),
    # --- on/off above the protection: D6 (button -> KEY / IO21), R24 to the IP5306 KEY
    "D6": (6.0, -6.7, 180), "R24": (9.5, -6.05, 180),
    # --- USB feed into 5 V (runs without a battery)
    "D4": (24.4, 27.0, 0),
    # --- series resistors in the sensor cable lines, right before J2
    "R35": (52.4, 37.1, 270),  # 10R into the vest 3V3 line
    "R30": (52.0, 33.7, 0), "R31": (52.0, 32.7, 0), "R32": (52.0, 31.7, 0), "R33": (52.0, 30.7, 0), "R34": (52.0, 29.7, 0),
}


def parse_netlist(path):
    t = open(path).read()
    comps = {}
    for block in re.findall(r'\(comp\s+\(ref "[^"]+"\).*?\n\t\t\)', t, re.S):
        ref = re.search(r'\(ref "([^"]+)"\)', block).group(1)
        val = re.search(r'\(value "([^"]*)"\)', block).group(1)
        fp = re.search(r'\(footprint "([^"]*)"\)', block)
        ts = re.findall(r'\(tstamps "([^"]*)"\)', block)  # [sheet path, symbol UUID] -> footprint path
        ts = (ts[0].rstrip("/") + "/" + ts[-1]).lstrip("/") if len(ts) > 1 else ts[-1]
        lcsc = dict(re.findall(r'\(name "(LCSC(?: Hand| Option)?)"\) "([^"]*)"', block))
        if fp and fp.group(1):
            comps[ref] = (val, fp.group(1), ts, lcsc)
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
    ("Power", 0.5, 0.15, 0.6, 0.3, 0.2, 0.2, ["GND", "BAT_P", "5V_PERIPH", "VBUS_NATIVE", "Net-(U1-SW)", "Net-(U1-VOUT)",
                                              "Net-(D1-A)", "Net-(D2-A)", "IR_LED_A", "IR_LED_K", "Net-(U6-OUT*)"]),
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


HOLES = [(20.4, 14.8), (37.0, 42.5)]  # 2x M2 ISO 7380 (button head 3.5 mm), diagonal
HOLE_HEAD = 1.75     # courtyard radius = screw head
HOLE_KEEPOUT = 1.85  # radius without copper on all layers

USB_TUNE = 2.262  # mm added to D+ between module and U12 (D- runs around the outside)
USB_TUNE2 = 3.53  # mm added to D+ between U12 and J3 (D- bridge is longer than the D+ diagonal)

OWN_MODELS = {"JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
              "JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal",
              "WSON-8-1EP_8x6mm_P1.27mm_EP3.4x4.3mm"}  # scripts/gen_3d_wson8_8x6.py

LABELS = [  # front silk, horizontal, next to the connector, clear of pads and bodies (tools/silk.py): (x, y, text, height, angle)
    (7.0, 0.0, "AKKU", 0.8, 0), (4.2, 23.4, "LED/TSOP", 0.8, 0),
    (19.0, 40.43, "TASTER", 0.8, 0), (13.8, -4.95, "RESET", 0.8, 0),
    (10.65, 32.98, "WS2812", 0.8, 0), (30.2, 37.83, "USB", 0.8, 0), (56.5, 39.3, "SENSOR", 0.8, 0),
    (2.98, 44.98, "LAUTSPR.", 0.8, 0), (49.7, 26.03, "VIB", 0.8, 0), (54.1, 36.95, "1", 0.8, 0), (40.9, 40.13, "SD", 0.8, 0),
    (31.1, 22.7, "BOOT", 0.8, 0), (56.95, 9.54, "OLED", 0.8, 0), (56.95, 17.54, "GEBER", 0.8, 0),
    (26.6, 21.15, "lucas.giesecke.cc", 0.8, 0),  # maker mark below U2, under LOGO
]
STACKUP = "".join("\t\t" + l + "\n" for l in [
    "(stackup",
    '\t(layer "F.SilkS" (type "Top Silk Screen") (color "Black"))',
    '\t(layer "F.Paste" (type "Top Solder Paste"))',
    '\t(layer "F.Mask" (type "Top Solder Mask") (color "White") (thickness 0.01))',
    '\t(layer "F.Cu" (type "copper") (thickness 0.035))',
    '\t(layer "dielectric 1" (type "prepreg") (thickness 0.2104) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))',
    '\t(layer "In1.Cu" (type "copper") (thickness 0.0152))',
    '\t(layer "dielectric 2" (type "core") (thickness 1.065) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))',
    '\t(layer "In2.Cu" (type "copper") (thickness 0.0152))',
    '\t(layer "dielectric 3" (type "prepreg") (thickness 0.2104) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))',
    '\t(layer "B.Cu" (type "copper") (thickness 0.035))',
    '\t(layer "B.Mask" (type "Bottom Solder Mask") (color "White") (thickness 0.01))',
    '\t(layer "B.Paste" (type "Bottom Solder Paste"))',
    '\t(layer "B.SilkS" (type "Bottom Silk Screen") (color "Black"))',
    '\t(copper_finish "ENIG")',
    '\t(dielectric_constraints no)',
    ")"])
LOGO = (22.75, 18.2, 1.55)  # Borg cube (lucas.giesecke.cc) on the front silk: centre x, y, edge length
BACK_LABELS = [  # no room on the front
    (41.5, 16.0, "github.com/G5K-org/open-lasertag", 0.8, 0), (41.5, 14.6, "open-lasertag v1", 0.8, 0),
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
    y = -YT + 1.2
    while y < H - 1.0:
        x = 1.2
        while x < W - 1.0:
            ok = on_board(x, y, 1.0) and all(not (bx0 - r0 < x < bx1 + r0 and by0 - r0 < y < by1 + r0) for bx0, by0, bx1, by1 in boxes)
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


def logo(board, cx, cy, a, w=0.15):
    """Isometric Borg cube: hexagon outline, the three visible face edges and a 3 x 3 grid on every face."""
    import math
    c = a * math.cos(math.radians(30))
    top, ur, lr, bot, ll, ul, mid = ((cx, cy - a), (cx + c, cy - a / 2), (cx + c, cy + a / 2), (cx, cy + a),
                                     (cx - c, cy + a / 2), (cx - c, cy - a / 2), (cx, cy))
    def line(p, q):
        sg = pcbnew.PCB_SHAPE(board); sg.SetShape(pcbnew.SHAPE_T_SEGMENT); sg.SetLayer(pcbnew.F_SilkS)
        sg.SetStart(pcbnew.VECTOR2I(MM(p[0]), MM(p[1]))); sg.SetEnd(pcbnew.VECTOR2I(MM(q[0]), MM(q[1])))
        sg.SetWidth(MM(w)); board.Add(sg)
    ring = [top, ur, lr, bot, ll, ul]
    for i in range(6):
        line(ring[i], ring[(i + 1) % 6])
    for p in (ul, ur, bot):
        line(mid, p)
    for o, u, v in ((ul, (top[0] - ul[0], top[1] - ul[1]), (mid[0] - ul[0], mid[1] - ul[1])),   # top face
                    (mid, (ur[0] - mid[0], ur[1] - mid[1]), (bot[0] - mid[0], bot[1] - mid[1])),  # right face
                    (ul, (mid[0] - ul[0], mid[1] - ul[1]), (ll[0] - ul[0], ll[1] - ul[1]))):   # left face
        for k in (1, 2):
            t = k / 3
            line((o[0] + t * u[0], o[1] + t * u[1]), (o[0] + t * u[0] + v[0], o[1] + t * u[1] + v[1]))
            line((o[0] + t * v[0], o[1] + t * v[1]), (o[0] + t * v[0] + u[0], o[1] + t * v[1] + u[1]))


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
    # ================= IP5306: battery, SW loop, BAT sense, VOUT, VIN =================
    BP = "BAT_P"
    r.t(F, 0.8, "BT1.1", (8.6, 4.2), (8.6, 2.9)); r.v((8.6, 2.9), net=BP, d=0.8, h=0.4)    # cell -> In2 (DW01A VCC)
    r.t(F, 1.2, "BT1.1", (9.65, 4.2), (12.95, 7.5), "L1.2")                              # cell -> L1
    r.t(F, 1.2, "L1.2", "C19.1"); r.gnd("C19.2", 0, 0.95)
    r.t(F, 1.0, "C19.1", (12.95, 11.4375), "R8.1", "R7.1", "C7.1")                      # on to the IR LED, C7
    r.gnd("C7.2", -0.95, 0)
    r.t(F, 1.2, "BT1.2", (4.6, 6.2), net="BAT_N")                                    # cell minus: 3 vias, 1.2 mm on B.Cu
    r.v((6.2, 6.2), net="BAT_N", d=0.6); r.v((5.4, 6.2), net="BAT_N", d=0.6); r.v((4.6, 6.2), net="BAT_N", d=0.6)
    r.t(F, 1.0, "U1.7", "L1.1")                                                          # SW, straight
    # BAT sense: cell -> R2 -> C5 / U1.6
    r.t(F, 0.4, (8.6, 2.9), (10.275, 2.9), "R2.2", net=BP)
    r.t(F, 0.4, "R2.1", (11.625, 0.625), (12.25, 1.25), "C5.1")
    r.t(F, 0.4, "C5.1", (12.625, 2.45), (15.6, 2.45), (16.015, 2.865), "U1.6")
    r.gnd("C5.2", 0, -1.05)
    # VOUT -> C20 -> load switch U16 (enabled by IRQ) -> two vias into the In2 5 V trunk; C30 below over a corridor
    P5 = "5V_PERIPH"
    r.t(F, 0.8, "U1.8", "C20.1", "U16.1")
    r.t(F, 0.3, (17.725, 7.15), (18.175, 7.6), (18.175, 9.9), (17.5, 10.575), "C30.1")
    r.gnd("C20.2", -1.0, 0); r.gnd("C30.2", -0.9, 0)
    r.t(F, 0.4, "U16.2", (20.3, 8.1)); r.v((20.3, 8.1), net="GND", d=0.5)              # GND via under the body
    r.t(F, 0.6, "U16.6", (20.5, 6.2)); r.t(F, 0.6, "U16.6", (21.6, 6.2))
    r.v((20.5, 6.2), net=P5, d=0.6); r.v((21.6, 6.2), net=P5, d=0.6)
    r.t(F, 0.3, "U16.4", (20.35, 10.1375), "C33.1"); r.gnd("C33.2", 0, 1.1)
    # IRQ (U1.4) -> via under U1 -> In2 between the thermal vias -> via at EN, R42 to GND
    r.t(F, 0.2, "U1.4", (20.855, 1.595), (20.6, 1.85)); r.v((20.6, 1.85), net="IP_IRQ", d=0.4, h=0.2)
    r.t(I2, 0.2, (20.6, 1.85), (19.6, 1.85), (19.6, 9.9), net="IP_IRQ"); r.v((19.6, 9.9), net="IP_IRQ", d=0.4, h=0.2)
    r.t(F, 0.25, "U16.3", (19.6, 9.4875), (19.6, 9.9), "R42.1"); r.t(F, 0.3, "R42.2", (19.0, 12.58), (20.35, 12.58), net="GND")       # shares the C33 GND via (B bundle below R42)
    # VIN: pad 1 down the strip right of C4 (In2 vias), C4 on a 45 deg branch, snubber R1 -> C29
    V = "VBUS_NATIVE"
    # vias below the B.Cu bundle (x + y > 33)
    r.t(F, 0.8, "U1.1", (22.7, 6.03), (22.7, 11.4), (24.0, 11.4))
    r.t(F, 0.6, "C4.1", (22.0, 10.575), (22.7, 9.875)); r.gnd("C4.2", 0, 0.9)
    r.v((22.7, 11.4), net=V, d=0.8, h=0.4); r.v((24.0, 11.4), net=V, d=0.8, h=0.4)
    # I2C: SDA via right of pad 3, SCL via right of pad 2 with the pull-up R40 below (3V3 island)
    r.t(F, 0.2, "U1.3", (23.6, 2.865)); r.v((23.6, 2.865), net="IP_SDA")
    r.t(F, 0.2, "U1.2", (24.0, 4.135)); r.v((24.0, 4.135), net="IP_SCL")
    r.t(F, 0.2, "R40.2", (27.0, 2.6)); r.v((27.0, 2.6), net="IP_SCL")
    r.t(F, 0.25, "R40.1", (27.75, 0.82), (28.25, 1.32), "R21.1")
    # ================= LDO + module supply =================
    r.t(F, 0.8, "U2.3", (29.9, 12.55), (29.9, 12.0)); r.v((29.9, 12.0), net="5V_PERIPH", d=0.6)
    r.t(F, 0.8, (29.9, 12.0), (30.65, 12.75), "C2.1", net="5V_PERIPH")
    r.gnd("C2.2", 0, -0.95); r.gnd("U2.1", -1.2, 0.3)
    # 3V3: LDO tab -> C3 -> R21 -> C18 (10u) -> C17 (100n) -> module pin 2
    r.t(F, 0.8, ("U2.2", 0, -0.8), (26.3, 4.84), (28.09, 3.05), "C18.1")
    r.t(F, 0.6, "C18.1", "C17.1", "U4.2")
    r.t(F, 0.6, "C3.1", (25.6, 4.84), (26.3, 5.54))  # 45 deg into the straight part of the trunk
    r.gnd("C3.2", -1.0, 0)
    r.t(F, 0.5, "C18.2", "C17.2", "U4.1")
    # EN: R21 / C16 RC right at pin 3
    r.t(F, 0.25, "R21.2", "C16.1", (31.3, 4.03), "U4.3")
    r.gnd("C16.2", 0, 1.12)
    # 3V3 also leaves from the LDO's lower tab pin into the In2 3V3 tree
    r.v((26.3, 15.0), net="3V3_MCU", d=0.6)

    # ================= left-pin signals: vias next to the module, long runs on B.Cu =================
    # order top->bottom (EN, TRIGGER, RELOAD, IR_GATE, WS2812) = order of the targets, so no crossings
    # EN to the RESET button in the tab: In2 along the top edge, up the tab at x 16.9
    r.v((29.4, 4.73), net="Net-(U4-EN)")
    r.t(I2, 0.25, (29.4, 4.73), (29.4, 0.7), (16.9, 0.7), (16.9, -7.4), net="Net-(U4-EN)")
    r.v((16.9, -7.4), net="Net-(U4-EN)"); r.t(F, 0.25, (16.9, -7.4), "SW3.2")
    for pin, yy, xd, end in (("U4.4", 5.30, 7.8, (7.8, 25.65)), ("U4.5", 6.57, 8.6, None), ("U4.6", 7.84, 13.0, None)):
        r.t(F, 0.25, pin, (32.25, yy)); r.v((32.25, yy))
    r.t(B, 0.25, (32.25, 5.30), (24.95, 5.30), (7.8, 22.45), (7.8, 31.4), (12.5, 36.1), net="TRIGGER")
    r.v((12.5, 36.1), net="TRIGGER")
    r.t(F, 0.25, (12.5, 36.1), "R9.2", (12.5, 38.9), "J8.1")
    r.t(F, 0.25, "C8.1", (13.2, 37.77), (12.5, 38.47))
    r.t(B, 0.25, (32.25, 6.57), (24.58, 6.57), (8.6, 22.55), (8.6, 26.3), (18.4, 36.1), net="RELOAD")
    r.v((18.4, 36.1), net="RELOAD")
    r.t(F, 0.25, (18.4, 36.1), "R10.2", (18.4, 38.9), "J8.3")
    r.t(F, 0.25, "C9.1", (19.1, 37.77), (18.4, 38.47))
    r.t(B, 0.25, (32.25, 7.84), (24.21, 7.84), (13.1, 18.95), net="IR_GATE"); r.v((13.1, 18.95), net="IR_GATE")
    r.t(F, 0.25, (13.1, 18.95), "R5.1")
    r.t(F, 0.25, "U4.10", (32.4, 12.92)); r.v((32.4, 12.92))
    r.t(B, 0.25, (32.4, 12.92), (26.88, 12.92), (15.6, 24.2), net="WS2812_DIN_3V3")
    r.v((15.6, 24.2), net="WS2812_DIN_3V3"); r.t(F, 0.25, (15.6, 24.2), "Q4.2")

    # ================= IR driver =================
    # J6: 1 LED anode (R7 || R8), 2 GND, 3 3V3, 4 LED cathode (Q1), 5 TSOP 6 OUT
    r.t(F, 0.6, "R8.2", "R7.2", (6.86, 16.1), "J6.1")
    r.t(F, 0.6, "J6.2", (7.662, 17.1), "Q1.3")                                      # LED cathode next to the anode
    r.t(F, 0.3, "J6.3", (6.3, 18.1)); r.v((6.3, 18.1), net="GND")
    r.t(F, 0.3, "J6.4", (5.9, 19.1), (6.3, 19.5)); r.v((6.3, 19.5), net="3V3_J6")
    # 3V3_J6 over R36 (10R) from the In2 3V3 diagonal
    r.t(I2, 0.4, (6.3, 19.5), (7.8, 19.5), (10.3, 22.0), net="3V3_J6"); r.v((10.3, 22.0), net="3V3_J6")
    r.t(F, 0.3, (10.3, 22.0), "R36.2", net="3V3_J6"); r.t(F, 0.3, "R36.1", (13.7, 22.0)); r.v((13.7, 22.0), net="3V3_MCU")
    r.t(I2, 0.4, (14.875, 22.0), (13.7, 22.0), net="3V3_MCU")
    r.t(F, 0.3, "Q1.1", "R5.2"); r.t(F, 0.3, "R6.1", (11.95, 20.05))
    r.gnd("Q1.2", 0.65, -0.55); r.gnd("R6.2", 0, -0.85)
    # BAT: on to the battery divider R3, right of R8
    r.t(F, 0.4, "C19.1", (12.95, 15.5), (14.2, 16.75), "R3.1")

    # ================= TSOP 6 on the weapon (J6 pins 2/3/5) =================
    # OUT: IO16 -> B.Cu channel between the IR and WS2812 diagonals -> F.Cu into the bottom pin
    r.t(F, 0.2, "U4.9", (32.25, 11.65)); r.v((32.25, 11.65))
    # diagonal x + y = 38.0: between the H1 keep-out and the R2 3V3 via
    r.t(B, 0.2, (32.25, 11.65), (31.0, 10.4), (27.6, 10.4), (14.3, 23.7), net="TSOP6_OUT"); r.v((14.3, 23.7), net="TSOP6_OUT")
    r.t(F, 0.2, (14.3, 23.7), (7.2, 23.7), (5.6, 22.1), (5.6, 20.6), "J6.5")

    # ================= trigger / reload / reset =================
    r.gnd("C8.2", 0.95, 0); r.gnd("C9.2", 0.95, 0)
    r.t(F, 0.3, "J8.2", (15.45, 39.6)); r.v((15.45, 39.6), net="GND"); r.t(F, 0.3, "SW3.1", (11.0, -7.4)); r.v((11.0, -7.4), net="GND")
    r.drop("R9.1", 0, 0.95); r.drop("R10.1", 0, 0.95)

    # ================= WS2812 level shifter =================
    # Q4 drain -> R15 / R25 (1k to 5 V); gate on 3V3 over an In2 branch
    r.t(F, 0.25, "Q4.3", "R15.1", "R25.2")
    r.t(F, 0.4, "R15.2", (8.23, 27.8), "J1.1")
    r.t(F, 0.3, "Q4.1", (16.2, 28.075)); r.v((16.2, 28.075), net="3V3_MCU")
    r.t(I2, 0.4, (13.6, 23.275), (13.6, 26.0), (15.675, 28.075), (16.2, 28.075), net="3V3_MCU")
    # strip supply: J1.2 -> R25, C32, C10 (2 x 22u)
    r.t(F, 0.4, "J1.2", "R25.1")
    r.t(F, 0.8, "J1.2", (9.5, 29.8), (11.5, 31.8), "C32.1", "C10.1")
    r.gnd("J1.3", 2.55, 0); r.gnd("C10.2", 0.95, 0); r.gnd("C32.2", 0.95, 0.9)
    r.drop("C10.1", 0.2, 1.6)
    r.drop("C31.1", 0.95, 0.33); r.gnd("C31.2", 0, -0.95)

    # ================= battery divider R3/R4/C6 -> ADC (IO8) =================
    r.t(F, 0.25, "U4.12", (31.6, 15.46), (31.37, 15.69), (25.96, 15.69), (23.925, 17.725), "C6.1", "R4.1",
        (17.35, 17.725), "R3.2")
    r.t(F, 0.4, "R4.2", (17.025, 18.3), (16.6, 18.3)); r.v((16.6, 18.3), net="GND")   # clear of In2 3V3 / B.Cu diagonals
    r.t(F, 0.4, "C6.2", (20.6, 20.275)); r.v((20.6, 20.275), net="GND")
    # IP_SDA pull-up R38 right below IO9, 3V3 from the R27 via
    r.t(F, 0.2, "U4.17", "R38.2")
    r.t(F, 0.25, "R38.1", (38.05, 23.025), (37.375, 23.7))

    # ================= USB: pair 0.2/0.2, 45 deg into the ESD chip =================
    r.t(F, 0.2, "U4.13", (31.3, 16.73), (30.85, 17.18), (30.85, 23.5), (27.25, 27.1), "U12.6")
    # D+ is the inner line of the pair: meander makes it as long as D- (tools/pairlen.py)
    r.t(F, 0.2, "U4.14", (31.25, 18.0), *meander_v(31.25, 18.9, USB_TUNE), (31.25, 23.66), (29.15, 25.76), "U12.4")
    r.gnd("U12.2", 0, 0.9)
    # vertical USB-C, 1.0 mm pitch: row A on top, row B below; each line has one pad per row.
    # D+: A6 and B6 on one F.Cu diagonal through a via in the connector centre, fed on B.Cu from the right.
    # D-: A7 (via above) and B7 (via below) bridged on B.Cu left of the centre, fed at the middle of the bridge.
    # Both plug orientations see the same lengths (tools/pairlen.py: U12.3-J3.A6 = U12.3-J3.B6, A7 = B7).
    U = dict(d=0.4, h=0.2)
    DM, DP = "Net-(J3-D--PadA7)", "Net-(J3-D+-PadA6)"
    vc = (JX, JY)                                               # D+ centre via
    v3 = (JX + 0.95, 34.2)                                      # D+ F -> B
    v1, v2 = (JX + 0.5, JY - 2.9), (JX - 0.5, JY + 2.9)         # D-: above A7, below B7
    v5 = (JX - 2.0, 34.0)                                       # D- feed F -> B
    tap = (JX - 1.0, JY - 0.41)                                 # D- bridge: equal length to A7 and B7
    r.t(F, 0.2, "U12.3", *meander_v(v3[0], 33.15, USB_TUNE2, n=1, side=1), v3); r.v(v3, net=DP, **U)
    r.t(B, 0.2, v3, (v3[0], vc[1] - (v3[0] - vc[0])), vc, net=DP); r.v(vc, net=DP, **U)
    r.t(F, 0.2, "J3.A6", (JX - 0.5, JY - 0.5), vc, (JX + 0.5, JY + 0.5), "J3.B6")
    r.t(F, 0.2, "U12.1", ("U12.1", 0, 0.31), v5); r.v(v5, net=DM, **U)
    r.t(B, 0.2, v5, (v5[0], tap[1] - 1.0), tap, net=DM)
    r.t(B, 0.2, v1, (JX - 0.2, v1[1]), (JX - 1.0, v1[1] + 0.8), tap, (JX - 1.0, v2[1] - 0.5), v2, net=DM)
    r.v(v1, net=DM, **U); r.v(v2, net=DM, **U)
    r.t(F, 0.2, "J3.A7", v1)
    r.t(F, 0.2, "J3.B7", v2)
    # CC pull-downs right at the connector: CC1 straight up to R23, CC2 straight down to R22
    r.t(F, 0.25, "J3.A5", "R23.1"); r.gnd("R23.2", -0.9, 0)
    r.t(F, 0.25, "J3.B5", "R22.1"); r.gnd("R22.2", 0, -0.95)
    # VBUS: A4-B9 and A9-B4 straight through the row gap, a via in the gap on each side;
    # left one on B.Cu to the charger and the ESD centre via, right one on In2 to the ESD centre via
    V = "VBUS_NATIVE"
    vl, vr, ve = (JX - 2.5, JY), (JX + 2.5, JY), (JX, 31.5)
    r.t(F, 0.4, "J3.A4", vl, "J3.B9"); r.v(vl, net=V, d=0.6)
    r.t(F, 0.4, "J3.A9", vr, "J3.B4"); r.v(vr, net=V, d=0.6)
    r.t(F, 0.3, "U12.5", ve); r.v(ve, net=V, d=0.6)
    # left one up on B.Cu (1.0) to the In2 VIN line of the IP5306
    r.t(B, 0.4, vl, (vl[0] - 0.5, vl[1] - 0.5), (vl[0] - 0.5, 39.5), net=V)
    r.t(B, 1.0, (vl[0] - 0.5, 39.5), (vl[0] - 0.5, 20.6), (27.9, 17.9), (28.6, 17.2), net=V)
    r.v((28.6, 17.2), net=V, d=0.8, h=0.4); r.v((27.9, 17.9), net=V, d=0.8, h=0.4)
    r.t(I2, 1.6, (27.9, 17.9), (28.6, 17.2), (28.6, 14.3), (25.7, 11.4), (22.7, 11.4), net=V)
    r.t(B, 0.6, ve, (vl[0] - 0.5, ve[1] - (ve[0] - vl[0] + 0.5)), net=V)
    r.t(I2, 0.4, vr, (vr[0], 36.2), (vr[0] - 0.5, 35.7), (vr[0] - 0.5, 33.5), ve, net=V)
    # GND: outer pins (shell tabs overlap them) through the row gap, via in the gap
    for xg in (JX - 3.5, JX + 3.5):
        r.t(F, 0.4, ("J3.A1" if xg < JX else "J3.A12"), (xg, JY), ("J3.B12" if xg < JX else "J3.B1"), net="GND")
        r.v((xg, JY), net="GND")

    # ================= BOOT button: IO0 runs under the module on B.Cu =================
    r.t(F, 0.25, "U4.27", (49.85, 17.6)); r.v((49.85, 17.6))
    r.t(B, 0.25, (49.85, 17.6), (49.85, 18.7), (38.75, 18.7), (36.7, 20.75)); r.v((36.7, 20.75))
    r.t(F, 0.25, (36.7, 20.75), "SW4.2")
    r.gnd("SW4.1", 0, 1.4)

    # ================= TSOP 1-5: via under each pad, 45 deg on B.Cu, down a column, F.Cu into J2 =================
    for k, (pin, X) in enumerate((("U4.18", 45.0), ("U4.19", 45.6), ("U4.20", 46.2), ("U4.21", 46.8), ("U4.22", 47.4))):
        x0 = r.pt(pin)[0]
        yt = r.pt(f"J2.{k + 3}")[1]
        r.t(F, 0.2, pin, (x0, 20.75)); r.v((x0, 20.75))
        rs = f"R{30 + k}"
        if k < 3:
            r.t(B, 0.2, (x0, 20.75), (X, 20.75 + X - x0), (X, yt)); r.v((X, yt))
            r.t(F, 0.2, (X, yt), f"{rs}.1")
        else:  # left of the pad the I2S diagonals pass too close
            r.t(B, 0.2, (x0, 20.75), (X, 20.75 + X - x0), (X, yt - 0.6), (X + 0.6, yt), (50.4, yt)); r.v((50.4, yt))
            r.t(F, 0.2, (50.4, yt), f"{rs}.1")
        r.t(F, 0.2, f"{rs}.2", f"J2.{k + 3}")
    r.gnd("J2.2", -1.7, 0)
    # sensor 3V3 from In2 (branch of the module 3V3 line down the right edge)
    r.v((52.8, 35.7), net="3V3_MCU", d=0.6); r.t(F, 0.3, (52.8, 35.7), "R35.1")      # vest 3V3 over R35 (10R)
    r.t(F, 0.3, "R35.2", (52.85, 37.58), (54.5, 35.93), "J2.1")

    # ================= vibration drivers =================
    # one motor for recoil and hit feedback (IO47)
    r.t(F, 0.25, "U4.24", "R11.1")
    r.t(F, 0.25, "R11.2", (44.61, 21.75), "Q2.1")
    r.t(F, 0.25, "R12.1", (44.0, 22.68), "Q2.1")
    r.t(F, 0.5, "Q2.3", (47.74, 22.7), "M1.2"); r.t(F, 0.5, "D1.2", (46.7, 24.1))
    r.t(F, 0.4, "Q2.2", (44.21, 25.3), (42.75, 25.3)); r.t(F, 0.4, "R12.2", (42.75, 25.3)); r.v((42.75, 25.3), net="GND")
    r.drop("D1.1", 0, 1.05); r.drop("M1.1", -0.6, 1.5)

    # ================= I2S: three lines beside the module, then diagonal to the amp =================
    # down the column beside the module, then one 45 deg run straight into the amp (x + y = const)
    for pin, col, c, ycol, d, tail in (("U4.31", 52.45, 70.9, 50.15, 75.55, [(42.55, 33.0), "U6.1"]),
                                       ("U4.32", 52.95, 71.6, 50.65, 76.3, [(43.9, 32.4), (43.9, 35.25), "U6.16"]),
                                       ("U4.33", 53.45, 72.3, 51.15, 77.05, [(44.5, 32.55), (44.5, 36.25), "U6.14"])):
        y0 = r.pt(pin)[1]
        r.t(F, 0.2, pin, (col, y0), (col, c - col), (ycol, c - ycol), (ycol, d - ycol), *tail)

    # ================= audio amp =================
    for pp, to in (("U6.3", (41.55, 35.4)), ("U6.2", (42.05, 35.4)), ("U6.15", (42.4, 35.75)), ("U6.11", (42.05, 36.6))):
        r.t(F, 0.25, pp, to)
    r.v("U6.17", net="GND")
    r.t(F, 0.4, "U6.7", "U6.8", "C23.1")
    r.t(F, 0.25, "U6.4", (41.05, 33.95), (39.6, 33.95), (39.6, 36.0), (39.95, 36.35))
    r.gnd("C23.2", 0, -0.82)
    r.drop("C23.1", 0, 0.92)
    ON, OP = "Net-(U6-OUTN)", "Net-(U6-OUTP)"
    r.t(F, 0.25, "U6.9", (41.05, 37.7), (40.65, 38.1)); r.t(F, 0.4, (40.65, 38.1), (40.2, 38.55), (40.2, 39.1), net=OP)
    r.v((40.2, 39.1), net=OP, d=0.6)
    r.t(F, 0.25, "U6.10", (41.55, 37.9)); r.t(F, 0.4, (41.55, 37.9), (41.55, 38.2), (41.2, 38.55), (41.2, 39.1), net=ON); r.v((41.2, 39.1), net=ON, d=0.6)
    r.t(B, 0.4, (40.2, 39.1), (39.4, 39.9), (39.4, 44.95), (10.75, 44.95), (10.75, 40.0), (9.95, 39.2), net=OP)
    r.t(B, 0.4, (41.2, 39.1), (40.0, 40.3), (40.0, 45.5), (9.95, 45.5), (9.95, 41.2), net=ON)
    r.v((9.95, 39.2), net=OP, d=0.6); r.t(F, 0.4, (9.95, 39.2), "SP1.1")
    r.v((9.95, 41.2), net=ON, d=0.6); r.t(F, 0.4, (9.95, 41.2), "SP1.2")
    r.gnd("C22.2", 1.0, 0); r.drop("C22.1", 0, 0.95)
    r.gnd("C1.2", 0, -1.95); r.drop("C1.1", 0, 1.94)

    # ================= module GND pad 40 =================
    r.gnd("U4.40", 1.45, 0)

    # ================= In2: 5V / 3V3 / BAT distribution =================
    r.t(I2, 1.2, (20.5, 6.2), (21.6, 6.2), (22.55, 7.15), (25.05, 7.15), (29.9, 12.0), (30.2, 12.3), (30.2, 29.39), (32.2, 31.39), net=P5)
    r.t(I2, 1.0, (30.2, 27.4), (29.6, 28.0), (22.28, 28.0), (21.8, 28.48), (20.05, 28.48), (14.83, 33.7), net=P5)
    r.t(I2, 0.6, (14.83, 33.7), ("C10.1", 0.2, 1.6), net=P5)
    r.t(I2, 0.6, (32.2, 31.39), (40.51, 31.39), (46.7, 25.2), (48.3, 25.2), net=P5)  # through the D1 via to the motor
    r.t(I2, 0.6, (34.0, 31.39), (34.51, 31.9), (34.51, 34.95), (37.75, 38.19), (38.75, 38.19), net=P5)
    r.t(I2, 0.6, (34.51, 34.6), (32.71, 36.4), (32.3, 36.4), net=P5)
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
    x17 = r.pt("U4.17")[0]                                                 # IO9 (IP_SDA) from the bottom pad row
    r.t(F, 0.2, "U4.17", (x17, 18.0)); r.v((x17, 18.0))
    r.v((56.2, 14.0), net="PWR_KEY")
    r.t(F, 0.2, (56.2, 14.0), "J5.2")
    x23 = r.pt("U4.23")[0]                                                 # IO21 (ENC_SW) from the bottom pad row
    r.t(F, 0.2, "U4.23", (x23, 18.0)); r.v((x23, 18.0))
    r.t(F, 0.2, "U4.11", (35.6, 14.19)); r.v((35.6, 14.19))               # IO18 (IP_SCL) under the module
    r.gnd("J5.1", 1.7, 0)

    # ================= SPI-NAND U14: four lines over B.Cu down the left of SW4 =================
    # order left->right = CS (pad 7), MISO (pad 8), MOSI (pad 15), CLK (pad 16); CS/MISO surface left of
    # U14, MOSI/CLK run under it to vias right of pins 5/6
    for pin in ("U4.7", "U4.8"):
        r.t(F, 0.2, pin, (35.0, r.pt(pin)[1])); r.v((35.0, r.pt(pin)[1]))
    for pin in ("U4.15", "U4.16"):
        r.t(F, 0.2, pin, (r.pt(pin)[0], 18.0)); r.v((r.pt(pin)[0], 18.0))
    y1, y2, y5, y6 = (r.pt(f"U14.{n}")[1] for n in (1, 2, 5, 6))
    x7, x8 = r.pt("U4.7")[1], r.pt("U4.8")[1]
    x15, x16 = r.pt("U4.15")[0], r.pt("U4.16")[0]
    r.t(B, 0.2, (35.0, x7), (34.0, x7 + 1.0), (34.0, y1), net="FLASH_CS"); r.v((34.0, y1))
    r.t(F, 0.2, (34.0, y1), "U14.1", net="FLASH_CS")
    r.t(B, 0.2, (35.0, x8), (34.6, x8 + 0.4), (34.6, y2 - 0.6), (34.0, y2), net="SPI_MISO"); r.v((34.0, y2))
    r.t(F, 0.2, (34.0, y2), "U14.2", net="SPI_MISO")
    r.t(B, 0.2, (x15, 18.0), (35.2, 18.0 + x15 - 35.2), (35.2, 25.2), (35.2 + y5 - 25.2, y5), (43.65, y5), net="SPI_MOSI")
    r.v((43.65, y5)); r.t(F, 0.2, (43.65, y5), "U14.5", net="SPI_MOSI")
    r.t(B, 0.2, (x16, 18.0), (35.8, 18.0 + x16 - 35.8), (35.8, 24.9), (35.8 + y6 - 24.9, y6), (43.65, y6), net="SPI_CLK")
    r.v((43.65, y6)); r.t(F, 0.2, (43.65, y6), "U14.6", net="SPI_CLK")
    # /CS pull-up R27, 100n C25 at VCC; 3V3 for both from In2, /HOLD straight to VCC, /WP over In2
    r.t(F, 0.2, "R27.2", (35.825 - 0.975, 25.575), "U14.1")
    r.t(F, 0.4, "C25.1", (r.pt("U14.8")[0], 24.6 + r.pt("U14.8")[0] - r.pt("C25.1")[0]), "U14.8")
    r.t(F, 0.25, "U14.8", "U14.7")
    r.drop("C25.1", 0, -0.9); r.drop("R27.1", 0, -0.9)
    r.gnd("C25.2", 0, 0.9)
    r.t(F, 0.25, "U14.3", (34.0, r.pt("U14.3")[1])); r.v((34.0, r.pt("U14.3")[1]), net="3V3_MCU")
    r.t(F, 0.4, "U14.4", (37.2, r.pt("U14.4")[1]))
    r.v((37.4, 30.0), net="GND")
    # ================= microSD J7 on the same bus: contacts along the bottom edge, all lines run up on F.Cu under
    # the slot; CLK changes to F.Cu above the slot (it crosses MOSI), MOSI/MISO/CS drop through vias at y 39.2
    yv = 39.2
    xs = {n: r.pt(f"J7.{n}")[0] for n in "12345678"}
    r.t(B, 0.2, (43.65, y6), (44.3, y6 + 0.65), (44.3, 35.2), (xs["5"], 35.2 + xs["5"] - 44.3), net="SPI_CLK")
    r.v((xs["5"], 35.2 + xs["5"] - 44.3)); r.t(F, 0.2, (xs["5"], 35.2 + xs["5"] - 44.3), "J7.5", net="SPI_CLK")
    r.t(B, 0.2, (43.65, y5), (43.65, 36.5), (43.65 + yv - 36.5, yv), (xs["3"], yv), net="SPI_MOSI")
    r.t(B, 0.2, (34.0, y2), (34.665, y2), (42.4, y2 + 42.4 - 34.665), (42.4, yv - (xs["7"] - 42.4)), (xs["7"], yv),
        net="SPI_MISO")
    x25 = r.pt("U4.25")[0]
    r.t(F, 0.2, "U4.25", (x25, 20.6)); r.v((x25, 20.6))
    r.t(B, 0.2, (x25, 20.6), (51.0, 20.6 + 51.0 - x25), (51.0, yv - 51.0 + xs["2"]), (xs["2"], yv), net="SD_CS")
    for n in "372":
        r.v((xs[n], yv)); r.t(F, 0.2, (xs[n], yv), f"J7.{n}")
    # VDD straight up into C26, 3V3 from In2 into a via on that line
    r.t(F, 0.25, "J7.4", "C26.1")
    r.gnd("C26.2", 0, -0.9)
    r.t(F, 0.25, "C28.1", (48.45, 38.4), (xs["4"], 38.4), net="3V3_MCU"); r.gnd("C28.2", 0, -0.9)   # 10u for the card
    r.v((xs["4"], 38.4), net="3V3_MCU")
    r.t(I2, 0.4, (52.8, 35.7), (51.6, 35.7), (51.6 - 2.7, 38.4), (xs["4"], 38.4), net="3V3_MCU")
    r.t(F, 0.4, "J7.6", (xs["6"], 43.9)); r.v((xs["6"], 43.9), net="GND")
    # DAT1/DAT2 (unused in SPI mode): joined over In2 under the slot, pulled up by R37
    for n in "18":
        r.v((xs[n], 43.9), net="SD_DAT12")
    r.t(F, 0.2, "J7.8", (xs["8"], 43.9))
    r.t(I2, 0.2, (xs["8"], 43.9), (xs["8"] + 1.3, 42.6), (xs["1"] - 1.3, 42.6), (xs["1"], 43.9), net="SD_DAT12")
    r.t(F, 0.2, "J7.1", (xs["1"], 38.0), "R37.1")
    r.t(F, 0.25, "R37.2", (51.6, r.pt("R37.2")[1] - 0.65), (51.6, 35.7)); r.v((51.6, 35.7), net="3V3_MCU")
    # shell: GND vias outside the slot
    jx, jy = PLACE["J7"][:2]
    for pad, dx, dy in (((jx - 5.1, jy - 3.1), 0, 1.25), ((jx - 5.1, jy + 1.35), -0.95, 0),
                        ((jx + 5.1, jy - 3.1), 0.95, 0), ((jx + 5.1, jy + 1.35), 0.95, 0)):
        r.t(F, 0.4, pad, (pad[0] + dx, pad[1] + dy), net="GND"); r.v((pad[0] + dx, pad[1] + dy), net="GND")
    P3 = "3V3_MCU"

    # ================= battery protection (tab above BT1) =================
    BN = "BAT_N"
    r.t(F, 0.25, "U15.1", "Q3.6"); r.t(F, 0.25, "U15.3", "Q3.4")       # OD -> discharge FET, OC -> charge FET
    r.t(F, 0.25, "Q3.2", "Q3.5")                                          # common drain under the body
    r.t(F, 0.2, "R29.1", "U15.2"); r.gnd("R29.2", -0.7, 0)                 # CS -> 1k -> P- (GND)
    r.gnd("Q3.3", 0, 1.0, w=0.6, d=0.6); r.gnd("Q3.3", -1.15, 0, w=0.6, d=0.6)  # S2 = P- = GND, full battery current
    r.gnd("Q3.3", -1.0, 1.0, w=0.6, d=0.6)
    yb = -4.3
    r.t(F, 0.8, "Q3.1", (r.pt("Q3.1")[0], yb), net=BN)
    r.v((r.pt("Q3.1")[0], yb), net=BN, d=0.6); r.v((r.pt("Q3.1")[0] - 0.9, yb), net=BN, d=0.6)
    r.v((r.pt("Q3.1")[0] + 0.9, yb), net=BN, d=0.6)
    r.t(F, 0.8, (r.pt("Q3.1")[0] - 0.9, yb), (r.pt("Q3.1")[0] + 0.9, yb), net=BN)
    r.t(B, 1.2, (6.2, 6.2), (4.6, 6.2), net=BN)
    r.t(B, 1.2, (5.4, 6.2), (5.4, yb + 0.7), (4.7, yb), (r.pt("Q3.1")[0] - 0.9, yb), net=BN)
    # B- along the top: C27 (VSS side) -> DW01A VSS (45 deg branch) -> FET source S1
    xc = r.pt("C27.2")[0]; u6 = r.pt("U15.6")
    r.t(F, 0.3, "C27.2", (xc, yb + 0.7), (xc - 0.7, yb), (r.pt("Q3.1")[0], yb), net=BN)
    r.t(F, 0.3, "U15.6", (u6[0], yb + 0.55), (u6[0] - 0.55, yb), net=BN)
    r.t(F, 0.25, "U15.5", "C27.1"); r.t(F, 0.25, "C27.1", "R28.2")
    # DW01A supply from the cell side (BAT_P) over In2
    r.t(F, 0.3, "R28.1", (14.61, -1.41), (14.2, -1.0)); r.v((14.2, -1.0), net="BAT_P")

    # ================= on/off: D6 in the tab, KEY over R24 down the tab to U1.5 =================
    r.t(I2, 0.6, (14.2, -1.0), (13.4, -0.2), (9.4, -0.2), (8.6, 0.6), (8.6, 2.9), net=BP)   # DW01A VCC from the cell
    r.t(F, 0.25, "U1.5", (16.6, 1.07), (16.6, -4.6), (15.15, -6.05), "R24.1")
    r.t(F, 0.25, "R24.2", "D6.1")
    r.v((4.75, -5.45), net="PWR_KEY"); r.t(F, 0.2, (4.75, -5.45), (5.1125, -5.8125), "D6.3")
    r.v((6.0, -6.85), net="ENC_SW"); r.t(F, 0.2, (6.0, -6.85), (6.5, -7.35), "D6.2")
    # B.Cu lanes along the top edge (top -> bottom = right -> left of their risers): PWR_KEY (J5), ENC_SW (IO21) into
    # the tab; IP_SDA (IO9) and IP_SCL (IO18) drop to the vias right of U1
    r.t(B, 0.2, (56.2, 14.0), (53.6, 16.6), (50.6, 16.6), (50.0, 16.0), (50.0, 0.45), (18.05, 0.45), (18.05, -7.95), (4.75, -7.95), (4.75, -5.45), net="PWR_KEY")
    r.t(B, 0.2, (45.68, 18.0), (45.68, 0.9), (17.6, 0.9), (17.6, -6.85), (6.0, -6.85), net="ENC_SW")
    r.t(B, 0.2, (38.05, 18.0), (38.05, 1.35), (23.6, 1.35), (23.6, 2.865), net="IP_SDA")
    r.t(B, 0.2, (35.6, 14.19), (35.6, 1.8), (28.6, 1.8), (27.8, 2.6), (25.465, 2.6), (24.0, 4.065), (24.0, 4.135),
        net="IP_SCL")

    # ================= VIN snubber R1/C29 on the VBUS B.Cu line =================
    r.v((25.2, 31.0), net="VBUS_NATIVE", d=0.6); r.t(F, 0.4, (25.2, 31.0), "R1.1")
    r.t(F, 0.4, "R1.2", "C29.1"); r.gnd("C29.2", 0, 0.9)

    # ================= USB -> 5 V (D4) =================
    r.t(F, 0.5, "D4.2", (25.2, 26.0)); r.v((25.2, 26.0), net="VBUS_NATIVE", d=0.6)
    r.t(F, 0.5, "D4.1", "C31.1")
    r.t(I2, 0.5, (51.6, 23.0), (50.9, 23.7), (r.pt("R27.1")[0], 23.7), net=P3)
    w3 = r.pt("U14.3")[1]
    r.t(I2, 0.4, (34.0, w3), (r.pt("R27.1")[0], w3 + 34.0 - r.pt("R27.1")[0]), (r.pt("R27.1")[0], 23.7), net=P3)
    r.t(I2, 0.5, (26.3, 15.0), (19.6, 19.205), (9.425, 27.45), (9.425, 37.0), (10.375, 37.95), ("R10.1", 0, 0.95), net=P3)
    r.t(I2, 0.5, (51.0, 2.76), (51.6, 3.36), (51.6, 34.5), (52.8, 35.7), net=P3)


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
        libdir = PROJ_FPLIB if os.path.isdir(f"{PROJ_FPLIB}/{lib}.pretty") else FPLIB
        m = pcbnew.FootprintLoad(f"{libdir}/{lib}.pretty", name)
        assert m is not None, fpid
        m.SetFPID(pcbnew.LIB_ID(lib, name))
        if name in OWN_MODELS:  # KiCad has no model for these: own ones (scripts/gen_3d_*.py)
            models = m.Models()  # iterating yields copies, indexing edits in place
            for i in range(len(models)):
                models[i].m_Filename = f"${{KIPRJMOD}}/3dmodels/{name}.wrl"
        m.SetPath(pcbnew.KIID_PATH("/" + ts))
        m.SetReference(ref)
        m.SetValue(val)
        for key, part in lcsc.items():  # JLCPCB part number travels with the footprint (BOM/CPL, parity)
            m.SetField(key, part)
            m.GetField(key).SetVisible(False); m.GetField(key).SetLayer(pcbnew.F_Fab)
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
    # clockwise polygon; every corner rounded: tangent points P - a*r / P + b*r, centre P - a*r + b*r;
    # KiCad draws the arc clockwise from start to end -> swap the ends on concave corners
    n = len(OUTLINE)
    ends = []
    for i, p in enumerate(OUTLINE):
        q0, q1 = OUTLINE[i - 1], OUTLINE[(i + 1) % n]
        a = ((p[0] - q0[0]) / math.dist(p, q0), (p[1] - q0[1]) / math.dist(p, q0))
        b = ((q1[0] - p[0]) / math.dist(p, q1), (q1[1] - p[1]) / math.dist(p, q1))
        t1 = (p[0] - a[0] * r, p[1] - a[1] * r); t2 = (p[0] + b[0] * r, p[1] + b[1] * r)
        c = (t1[0] + b[0] * r, t1[1] + b[1] * r)
        arc(c, t1, t2) if a[0] * b[1] - a[1] * b[0] > 0 else arc(c, t2, t1)
        ends.append((t1, t2))
    for i in range(n):
        seg(ends[i][1], ends[(i + 1) % n][0])

    rt = Router(board, fps, netinfo)
    route(rt)
    rt.flush()
    labels(board); logo(board, *LOGO)
    print("stitching vias:", stitch(board, netinfo))
    for it in list(board.GetTracks()) + [pd for f in board.GetFootprints() for pd in f.Pads()]:
        if it.GetClass() in ("PCB_VIA", "PAD"):
            it.SetTeardropsEnabled(True)
    print("teardrops:", teardrops(board))
    # planes: In1 solid GND; GND fill on F/In2/B around the routing
    edge = OUTLINE
    zone(board, netinfo, "1", "GND", edge, thermal=False)
    for L in ("F", "2", "B"):
        zone(board, netinfo, L, "GND", edge)
    # copper island on the LDO tab as heat spreader (3V3)
    zone(board, netinfo, "F", "3V3_MCU", [(23.2, 4.9), (29.2, 4.9), (29.2, 9.3), (23.2, 9.3)], prio=1, thermal=False)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(OUT, board)
    # KiCad ships no STEP for the EP1.23 TQFN: same 3x3 body with the EP1.6 model
    t = open(OUT).read().replace("TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm.step", "TQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm.step")
    # same for the IP5306 (HSOP-8 EP2.3: same body as the EP2.41x3.1 model)
    t = t.replace("HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.3x2.3mm.step", "HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.1mm.step")
    # mark the generated teardrop zones as KiCad teardrops (enum not exposed to Python)
    t = t.replace('(name "$teardrop_padvia$")', '(name "$teardrop_padvia$")\n\t\t(attr\n\t\t\t(teardrop\n\t\t\t\t(type padvia)\n\t\t\t)\n\t\t)')
    # stackup JLC04161H-7628 with the board colours: white solder mask, black silkscreen
    # (renders need --use-board-stackup-colors)
    t = t.replace("\t(setup\n", "\t(setup\n" + STACKUP, 1)
    open(OUT, "w").write(t)
    write_project(OUT)
    unplaced = sorted(set(comps) - set(PLACE))
    print(f"saved {OUT}  ({len(comps)} parts, {len(unplaced)} unplaced)")
    return board, fps


if __name__ == "__main__":
    build()
