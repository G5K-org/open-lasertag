#!/usr/bin/env python3
import os, re, math, copy
import pcbnew

REPO_KICAD = "/home/gsk/Projekte/lasertag/kicad/waffe_elektronik"
SCH = f"{REPO_KICAD}/waffe_elektronik.kicad_sch"
NETLIST = os.environ.get("NETLIST", "/tmp/test_netlist.net")
OUT_PCB = os.environ.get("OUT_PCB", "/tmp/claude_pcb/waffe_elektronik.kicad_pcb")
FPDIR = "/usr/share/kicad/footprints"

os.makedirs(os.path.dirname(OUT_PCB), exist_ok=True)

# ---------- 1. ref -> (value, lib_id) from the schematic (regex, no kiutils
#               dependency needed under the system python that has pcbnew) ----------
sch_text = open(SCH, encoding="utf-8").read()
part_info = {}
for m in re.finditer(
    r'\(symbol \(lib_id "([^"]+)"\).*?\n(?P<body>(?:.*\n)*?)\s*\(instances',
    sch_text):
    lib_id = m.group(1)
    body = m.group("body")
    ref_m = re.search(r'\(property "Reference" "([^"]+)"', body)
    val_m = re.search(r'\(property "Value" "([^"]+)"', body)
    if not ref_m or not val_m:
        continue
    ref = ref_m.group(1)
    if ref.startswith("#"):
        continue
    part_info[ref] = (val_m.group(1), lib_id)

# ---------- 2. parse the official netlist export for net membership ----------
text = open(NETLIST, encoding="utf-8").read()
nets = {}  # name -> [(ref,pin), ...]
# split on "(net " top-level occurrences within the nets section
nets_section = text[text.index("(nets"):]
blocks = re.split(r'\n\t\t\(net\b', nets_section)[1:]
for b in blocks:
    name_m = re.search(r'\(name "([^"]*)"\)', b)
    name = name_m.group(1).lstrip("/")
    if not name:
        continue
    pins = re.findall(r'\(node\s*\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', b)
    nets.setdefault(name, []).extend(pins)

print("parsed parts:", len(part_info), "nets:", len(nets))

# ---------- 3. footprint mapping (same as build_pcb.py) ----------
FP_BY_LIBID = {
    "Transistor_FET:AO3400A": ("Package_TO_SOT_SMD", "SOT-23-3"),
    "Battery_Management:MCP73831-2-OT": ("Package_TO_SOT_SMD", "SOT-23-5"),
    "Regulator_Linear:AMS1117-3.3": ("Package_TO_SOT_SMD", "SOT-223-3_TabPin2"),
    "Audio:MAX98357A": ("Package_DFN_QFN", "TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm"),
    "Diode:SS14": ("Diode_SMD", "D_SMA"),
    "Interface_Optical:TSOP348xx": ("OptoDevice", "Vishay_MOLD-3Pin"),
    "74xx:74AHCT125": ("Package_SO", "SOIC-14_3.9x8.7mm_P1.27mm"),
    "Switch:SW_Push": ("Button_Switch_SMD", "SW_SPST_SKQG_WithStem"),
    # IR-LED bleibt THT 5mm: Linsenoptik in readme.md Abschnitt 4 ("Linse Ø 25mm,
    # LED knapp hinter dem Brennpunkt") setzt die 5mm-Bauform voraus, keine reine
    # SMD-Kostenfrage.
    "Device:LED": ("LED_THT", "LED_D5.0mm"),
    "Device:Battery_Cell": ("Connector_JST", "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal"),
    "Device:Speaker": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"),
    "Motor:Motor_DC": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"),
    "Module:Boost_5V_MT3608": ("Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical"),
    "Module:ESP32S3_DevKitC": ("Connector_PinHeader_2.54mm", "PinHeader_1x22_P2.54mm_Vertical"),
}

# Pad numbers on the single-row 22-pin placeholder header, in physical pad
# order 1..22, renamed to match the schematic's custom pin numbers (which are
# GPIO-name strings, not plain integers) - must mirror MCU_LEFT+MCU_RIGHT from
# build_sch.py/build_full.py exactly.
ESP32S3_PAD_RENAME = [
    "GPIO1", "GPIO2", "GPIO4", "GPIO5", "GPIO6", "GPIO7", "GPIO8", "GPIO11",
    "GPIO12", "GPIO13", "GPIO14", "GPIO15", "GPIO16", "GPIO17", "GPIO18",
    "GPIO21", "GPIO38", "GPIO39", "3V3", "GND1", "GND2", "VBUS",
]

def cap_fp(value, polarized):
    if not polarized:
        return ("Capacitor_SMD", "C_0603_1608Metric")
    small = value.strip().lower() in ("4.7u", "10u", "1u")
    return ("Capacitor_SMD", "CP_Elec_4x5.4" if small else "CP_Elec_8x10.5")

def footprint_for(lib_id, value):
    if lib_id == "Device:R":
        return ("Resistor_SMD", "R_0603_1608Metric")
    if lib_id == "Device:C":
        return cap_fp(value, False)
    if lib_id == "Device:C_Polarized":
        return cap_fp(value, True)
    # Steckverbinder (Sensorkabel, WS2812-Strip-Anschluss) bleiben als THT-
    # Pinheader: hier haengt ein echtes Kabel dran, das im Betrieb gezogen
    # wird - SMD-Pads halten dem Zugstress schlechter stand als durchgesteckte
    # Pins.
    if lib_id.startswith("Connector_Generic:Conn_01x"):
        n = int(lib_id.rsplit("x", 1)[1])
        return ("Connector_PinHeader_2.54mm", f"PinHeader_1x{n:02d}_P2.54mm_Vertical")
    if lib_id in FP_BY_LIBID:
        return FP_BY_LIBID[lib_id]
    raise ValueError(f"no footprint for {lib_id}")

# ---------- 4. build the board ----------
board = pcbnew.BOARD()

MM = pcbnew.FromMM
footprints = {}
for ref, (value, lib_id) in part_info.items():
    libname, entry = footprint_for(lib_id, value)
    fp = pcbnew.FootprintLoad(f"{FPDIR}/{libname}.pretty", entry)
    if fp is None:
        raise RuntimeError(f"failed to load footprint {libname}:{entry} for {ref}")
    fp.SetReference(ref)
    fp.SetValue(value)
    if lib_id == "Module:ESP32S3_DevKitC":
        for i, newnum in enumerate(ESP32S3_PAD_RENAME, start=1):
            pad = fp.FindPadByNumber(str(i))
            if pad is None:
                raise RuntimeError(f"ESP32S3_DevKitC placeholder: pad {i} not found")
            pad.SetNumber(newnum)
    board.Add(fp)
    footprints[ref] = fp

print("footprints placed on board object:", len(footprints))

# ---------- 5. connectivity-aware placement ----------
# Naive "schematic order" packing put components far from what they actually
# wire to (long diagonal traces straight across the board). Instead: anchor
# every part to U4's pin index it (directly or transitively) shares a net
# with, then pack in that order so physical proximity tracks netlist
# proximity to the hub (U4 is the only component almost everything connects
# through, directly or via one hop).
u4_pin_index = {num: i for i, num in enumerate(ESP32S3_PAD_RENAME, start=1)}
net_anchor = {}
for name, pins in nets.items():
    for ref, pin in pins:
        if ref == "U4" and pin in u4_pin_index:
            net_anchor[name] = min(net_anchor.get(name, 999), u4_pin_index[pin])

part_anchor = {}
for _ in range(6):  # fixed-point propagation across shared nets
    changed = False
    for name, pins in nets.items():
        anchor = net_anchor.get(name)
        for ref, _pin in pins:
            if anchor is not None:
                if part_anchor.get(ref, 999) > anchor:
                    part_anchor[ref] = anchor
                    changed = True
        local_min = min((part_anchor[r] for r, _p in pins if r in part_anchor), default=None)
        if local_min is not None and (anchor is None or local_min < anchor):
            net_anchor[name] = local_min
            changed = True
    if not changed:
        break

part_order = sorted(
    (r for r in part_info if r != "U4"),
    key=lambda r: (part_anchor.get(r, 999), list(part_info.keys()).index(r)),
)
print("unanchored parts (no net path to U4):",
      [r for r in part_order if r not in part_anchor])

# ---------- 6. place U4 as a fixed left-hand spine, pack everything else to
#               its right in anchor order (bbox anchored correctly: text
#               labels are NOT centered on the footprint anchor, so tiling
#               uses the bbox's true offset from the anchor) ----------
GAP = MM(1.0)
MARGIN = MM(4)

fp_u4 = footprints["U4"]
fp_u4.SetPosition(pcbnew.VECTOR2I(0, 0))
u4_bbox = fp_u4.GetBoundingBox()
u4_anchor_x = MARGIN - u4_bbox.GetX()
u4_anchor_y = MARGIN - u4_bbox.GetY()
fp_u4.SetPosition(pcbnew.VECTOR2I(int(u4_anchor_x), int(u4_anchor_y)))
satellite_x0 = MARGIN + u4_bbox.GetWidth() + MM(8)

MAX_ROW_W = MM(70)
cursor_x, cursor_y, row_h, max_x = satellite_x0, MARGIN, 0, satellite_x0
for ref in part_order:
    fp = footprints[ref]
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    bbox = fp.GetBoundingBox()
    bx, by, w, h = bbox.GetX(), bbox.GetY(), bbox.GetWidth(), bbox.GetHeight()
    if cursor_x + w > satellite_x0 + MAX_ROW_W and cursor_x > satellite_x0:
        cursor_x = satellite_x0
        cursor_y += row_h + GAP
        row_h = 0
    anchor_x = cursor_x - bx
    anchor_y = cursor_y - by
    fp.SetPosition(pcbnew.VECTOR2I(int(anchor_x), int(anchor_y)))
    cursor_x += w + GAP
    row_h = max(row_h, h)
    max_x = max(max_x, cursor_x)

board_w_mm = pcbnew.ToMM(max_x - GAP + MARGIN)
board_h_mm = pcbnew.ToMM(max(cursor_y + row_h, MARGIN + u4_bbox.GetHeight()) + MARGIN)
print("board extents (mm):", board_w_mm, board_h_mm)

# ---------- 6. rounded-rect Edge.Cuts outline, sized to fit everything ----------
CORNER_R = MM(4.0)
x1, y1 = 0, 0
x2, y2 = MM(board_w_mm), MM(board_h_mm)

def seg(p1, p2):
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(int(p1[0]), int(p1[1])))
    s.SetEnd(pcbnew.VECTOR2I(int(p2[0]), int(p2[1])))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.15))
    board.Add(s)

def arc(center, r, a1_deg, a2_deg):
    mid_deg = (a1_deg + a2_deg) / 2
    def pt(deg):
        rad = math.radians(deg)
        return (center[0] + r * math.cos(rad), center[1] + r * math.sin(rad))
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(pcbnew.VECTOR2I(*map(int, pt(a1_deg))),
                      pcbnew.VECTOR2I(*map(int, pt(mid_deg))),
                      pcbnew.VECTOR2I(*map(int, pt(a2_deg))))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.15))
    board.Add(s)

r = CORNER_R
seg((x1 + r, y1), (x2 - r, y1))
arc((x2 - r, y1 + r), r, -90, 0)
seg((x2, y1 + r), (x2, y2 - r))
arc((x2 - r, y2 - r), r, 0, 90)
seg((x2 - r, y2), (x1 + r, y2))
arc((x1 + r, y2 - r), r, 90, 180)
seg((x1, y2 - r), (x1, y1 + r))
arc((x1 + r, y1 + r), r, 180, 270)

# ---------- 7. net classes + trace widths ----------
ds = board.GetDesignSettings()
ns = ds.m_NetSettings

def make_class(name, track_w_mm, clearance_mm, via_dia_mm=0.8, via_drill_mm=0.4):
    nc = pcbnew.NETCLASS(name)
    nc.SetTrackWidth(MM(track_w_mm))
    nc.SetClearance(MM(clearance_mm))
    nc.SetViaDiameter(MM(via_dia_mm))
    nc.SetViaDrill(MM(via_drill_mm))
    return nc

ds.m_TrackMinWidth = MM(0.15)  # allow fine-pitch SMD fanout traces (6 mil, standard prototype-fab capable)
ns.SetNetclass("Default", make_class("Default", 0.25, 0.2))
ns.SetNetclass("Power", make_class("Power", 0.6, 0.2))
ns.SetNetclass("IR_Pulse", make_class("IR_Pulse", 1.0, 0.25))

POWER_NETS = {"BAT_P", "GND", "5V_PERIPH", "3V3_MCU", "VBUS_NATIVE"}
IR_PULSE_NETS = {"IR_K", "IR_LED_ANODE1", "IR_LED_ANODE2"}
for n in POWER_NETS:
    ns.SetNetclassPatternAssignment(n, "Power")
for n in IR_PULSE_NETS:
    ns.SetNetclassPatternAssignment(n, "IR_Pulse")
board.SetDesignSettings(ds)

# ---------- 8. create nets and assign pads ----------
missing_pads = []
for name, pins in nets.items():
    netinfo = pcbnew.NETINFO_ITEM(board, name)
    board.Add(netinfo)
    for ref, pinnum in pins:
        fp = footprints.get(ref)
        if fp is None:
            continue
        # Some SMD footprints (e.g. 4-leg tact switches) reuse one pad NUMBER
        # on multiple physical pads - assign the net to all of them, not just
        # the first FindPadByNumber() hit.
        matched = [p for p in fp.Pads() if p.GetNumber() == pinnum]
        if not matched:
            missing_pads.append((ref, pinnum, name))
            continue
        for pad in matched:
            pad.SetNet(netinfo)

if missing_pads:
    print("WARNING missing pads:", missing_pads)
print("nets created:", len(nets), "missing pad refs:", len(missing_pads))

board.BuildConnectivity()
board.Save(OUT_PCB)
print("saved:", OUT_PCB)

DSN_OUT = os.environ.get("DSN_OUT")
if DSN_OUT:
    ok = pcbnew.ExportSpecctraDSN(board, DSN_OUT)
    print("DSN export:", ok, DSN_OUT)
