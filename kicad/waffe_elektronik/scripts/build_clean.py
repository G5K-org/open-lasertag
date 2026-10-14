#!/usr/bin/env python3
"""Hand-laid-out schematic for the Lasertag-Waffe (single ESP32-S3).

Every block is drawn deliberately instead of auto-routed: parts sit on the
1.27/2.54mm grid, wires are short and straight, supply arrows point up, ground
symbols hang down, and signals that leave a block do so through a net label on
a short stub (standard practice - long wires across the sheet are what made
the previous auto-generated version look like spaghetti).

Connectivity is checked against a reference netlist by scripts/netcmp.py.
"""
import copy
import os
import re
import sys
import math
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_sch import Sheet, get_symbol, resolve_units, rotate_lib_pin, snap  # noqa: E402
from kiutils.items.common import ColorRGBA, Position, Property, Effects, Font, Justify, Stroke, TitleBlock  # noqa: E402
from kiutils.items.schitems import (GlobalLabel, HierarchicalSheet, HierarchicalSheetProjectInstance,  # noqa: E402
                                    HierarchicalSheetProjectPath, Text, Connection, Junction, NoConnect,
                                    Rectangle)
from kiutils.items.syitems import SyRect, Fill  # noqa: E402
from kiutils.symbol import Symbol, SymbolPin  # noqa: E402
from kiutils.schematic import SchematicSymbol, SymbolProjectInstance, SymbolProjectPath  # noqa: E402

LIB = "/usr/share/kicad/symbols"
FONT = 1.27


def tw(s):
    """Rough rendered width (mm) of a 1.27mm KiCad label/field."""
    return 1.05 * len(s)


_raw = {}


def _lib_flags(path, entry):
    """kiutils drops KiCad 10's '(pin_numbers (hide yes))' syntax, which made
    every resistor/cap/power symbol show its pin numbers. Read the flags from
    the raw library text instead (falling back to the base of a derived
    symbol, which is where KiCad keeps them)."""
    if path not in _raw:
        _raw[path] = open(path).read()
    t = _raw[path]
    i = t.find(f'(symbol "{entry}"')
    head = t[i:t.find("(property", i)]
    m = re.search(r'\(extends "([^"]+)"\)', head)
    if m and "pin_numbers" not in head and "pin_names" not in head:
        return _lib_flags(path, m.group(1))
    hide_nums = bool(re.search(r"\(pin_numbers\s*(\(hide yes\)|hide)", head))
    pn = re.search(r"\(pin_names(.*?)\)\s*\)", head, re.S) or re.search(r"\(pin_names[^\n]*", head)
    names_present = "pin_names" in head
    off = re.search(r"\(offset ([\d.]+)\)", head)
    hide_names = bool(re.search(r"\(pin_names[\s\S]*?\(hide yes\)", head)) or "(pin_names hide" in head
    return hide_nums, names_present, float(off.group(1)) if off else None, hide_names


def _hidden_pins(path, entry):
    """Pin numbers marked '(hide yes)' in the library (stacked VDD/GND and NC
    pins on ICs like the MAX98357A). kiutils loses this flag too, which put
    overlapping pin numbers on top of each other."""
    t = _raw[path]
    i = t.find(f'(symbol "{entry}"')
    end = t.find('\n\t(symbol "', i + 1)
    block = t[i:end if end > 0 else len(t)]
    m = re.search(r'\(extends "([^"]+)"\)', block[:block.find("(property")])
    if m:
        return _hidden_pins(path, m.group(1))
    return {mm.group(2) for mm in re.finditer(
        r'\(pin \w+ \w+\s*\(at [^)]*\)\s*\(length [\d.]+\)\s*(\(hide yes\))\s*\(name "[^"]*"[\s\S]*?\(number "([^"]+)"',
        block)}


# Symbols kept in the project library symbols/lasertag.kicad_sym (written from the generated schematic, so the
# embedded copy and the library always match): pin types adapted where the stock symbol trips ERC.
PROJECT_SYMS = {
    ("Memory_Flash", "W25Q32JVZP"): {"3": "passive", "7": "passive"},  # /WP, /HOLD tied to 3V3
    ("Audio", "MAX98357A"): {"17": "power_in"},                       # exposed pad = GND
    ("74xx", "74AHCT125"): {},
}
PROJECT_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "symbols", "lasertag.kicad_sym")


class Sch(Sheet):
    pwr_n = 0  # shared by all pages: #PWR references stay unique in the hierarchy

    def __init__(self, title="", path="/", paper="A3"):
        super().__init__()
        self.sch.paper.paperSize = paper
        self.sch.paper.portrait = False
        self.path = path  # instance path of this page ("/" root, "/<sheet uuid>" sub-sheet)
        self.sch.titleBlock = TitleBlock(
            title="Lasertag - Waffen-Elektronik" + (f": {title}" if title else ""), date="2026-10-14", revision="2",
            company="open-lasertag",
            comments={1: "Ein ESP32-S3 in der Waffe, Weste nur Sensoren",
                      2: "ERC-geprüft, KiCad 10"})

    # ---------------------------------------------------------------- symbols
    def _register(self, path, entry, nick):
        key = (nick, entry)
        if key in self.registered_libs:
            return
        self.ensure_lib(path, entry, nick)
        sym = self.sch.libSymbols[-1]
        hide_nums, names_present, off, hide_names = _lib_flags(path, entry)
        sym.hidePinNumbers = hide_nums
        sym.pinNames = names_present or hide_names
        sym.pinNamesOffset = off
        sym.pinNamesHide = hide_names
        hidden = _hidden_pins(path, entry)
        types = next((v for (lib, e), v in PROJECT_SYMS.items() if e == entry and nick == "lasertag"), {})
        for u in sym.units:
            for p in u.pins:
                p.hide = p.number in hidden
                p.electricalType = types.get(p.number, p.electricalType)

    def _field(self, key, value, pos, just, hide, sym_angle):
        if pos is None:
            pos, hide = (0, 0), True
        fa = 90 if sym_angle in (90, 270) else 0
        if fa:
            just = "center"  # justification flips with rotation; center is unambiguous
        j = Justify(horizontally=None if just == "center" else just)
        return Property(key=key, value=value,
                        position=Position(X=round(pos[0], 3), Y=round(pos[1], 3), angle=fa),
                        effects=Effects(font=Font(height=FONT, width=FONT), justify=j, hide=hide))

    def _instance(self, nick, entry, units, ref, value, x, y, angle, unit, ref_at, val_at, just,
                  hide_ref=False, hide_val=False, footprint=""):
        x, y = snap(x), snap(y)
        inst = SchematicSymbol(libraryNickname=nick, entryName=entry,
                               position=Position(X=x, Y=y, angle=angle), unit=unit,
                               inBom=True, onBoard=True, uuid=self.uid())
        inst.properties = [
            self._field("Reference", ref, ref_at, just, hide_ref, angle),
            self._field("Value", value, val_at, just, hide_val, angle),
            self._field("Footprint", footprint, None, just, True, angle),
        ]
        inst.pins = {}
        pins = {}
        for u in units:
            if u.unitId not in (0, unit):
                continue
            for p in u.pins:
                inst.pins[p.number] = self.uid()
                pins[p.number] = rotate_lib_pin(x, y, p.position.X, p.position.Y, angle)
        inst.instances = [SymbolProjectInstance(
            name="waffe_elektronik",
            paths=[SymbolProjectPath(sheetInstancePath=self.path, reference=ref, unit=unit)])]
        self.sch.schematicSymbols.append(inst)
        return pins

    def part(self, lib, entry, ref, value, x, y, angle=0, unit=1, ref_at=None, val_at=None,
             just="left", hide_ref=False, hide_val=False):
        path = f"{LIB}/{lib}.kicad_sym"
        nick = "lasertag" if (lib, entry) in PROJECT_SYMS else lib
        self._register(path, entry, nick)
        base = next(s for s in self.sch.libSymbols if s.libraryNickname == nick and s.entryName == entry)
        return self._instance(nick, entry, base.units, ref, value, x, y, angle, unit,
                              ref_at, val_at, just, hide_ref, hide_val)

    def box(self, entry, pins, half_w, half_h, ref, value, x, y, ref_at, val_at, just="center"):
        """Custom rectangular module symbol. pins: (name, number, side, offset)
        with side L/R/T/B and offset along that side in sheet coords."""
        L = 2.54
        spins = []
        for name, num, side, off in pins:
            if side == "L":
                pos, ang = (-half_w - L, -off), 0
            elif side == "R":
                pos, ang = (half_w + L, -off), 180
            elif side == "T":
                pos, ang = (off, half_h + L), 270
            else:
                pos, ang = (off, -half_h - L), 90
            spins.append(SymbolPin(electricalType="passive", position=Position(X=pos[0], Y=pos[1], angle=ang),
                                   length=L, name=name, number=num,
                                   nameEffects=Effects(font=Font(height=FONT, width=FONT)),
                                   numberEffects=Effects(font=Font(height=FONT, width=FONT))))
        u0 = Symbol(entryName=entry, unitId=0, styleId=1)
        u1 = Symbol(entryName=entry, unitId=1, styleId=1, pins=spins, graphicItems=[
            SyRect(start=Position(X=-half_w, Y=half_h), end=Position(X=half_w, Y=-half_h),
                   fill=Fill(type="background"))])
        if ("lasertag", entry) not in self.registered_libs:
            top = Symbol(libraryNickname="lasertag", entryName=entry)
            top.units = [u0, u1]
            top.hidePinNumbers = True
            top.pinNames = True
            top.pinNamesOffset = 0.762
            top.inBom = top.onBoard = True
            top.properties = [
                Property(key="Reference", value="U", position=Position(X=0, Y=0, angle=0),
                         effects=Effects(font=Font(height=FONT, width=FONT))),
                Property(key="Value", value=entry, position=Position(X=0, Y=0, angle=0),
                         effects=Effects(font=Font(height=FONT, width=FONT))),
                Property(key="Footprint", value="", position=Position(X=0, Y=0, angle=0),
                         effects=Effects(font=Font(height=FONT, width=FONT), hide=True)),
            ]
            self.sch.libSymbols.append(top)
            self.registered_libs.add(("lasertag", entry))
        return self._instance("lasertag", entry, [u0, u1], ref, value, x, y, 0, 1, ref_at, val_at, just)

    # ------------------------------------------------------------ primitives
    def w(self, *pts):
        pts = [(snap(a), snap(b)) for a, b in pts]
        for a, b in zip(pts, pts[1:]):
            assert a[0] == b[0] or a[1] == b[1], f"non-orthogonal wire {a}->{b}"
            if a != b:
                self.sch.graphicalItems.append(Connection(
                    type="wire", points=[Position(X=a[0], Y=a[1]), Position(X=b[0], Y=b[1])],
                    uuid=self.uid()))

    def j(self, p):
        self.sch.junctions.append(Junction(position=Position(X=snap(p[0]), Y=snap(p[1])), uuid=self.uid()))

    def nc(self, p):
        self.sch.noConnects.append(NoConnect(position=Position(X=snap(p[0]), Y=snap(p[1])), uuid=self.uid()))

    def lbl(self, p, name, side):
        """Global label (the schematic spans several pages); side 'L' = text runs to the left of p, 'R' = right."""
        ang, h = (180, "right") if side == "L" else (0, "left")
        self.sch.globalLabels.append(GlobalLabel(
            text=name, shape="passive", position=Position(X=snap(p[0]), Y=snap(p[1]), angle=ang),
            effects=Effects(font=Font(height=FONT, width=FONT), justify=Justify(horizontally=h)),
            uuid=self.uid()))

    def _pwr(self, entry, name, p, angle, val_at, hide_val):
        Sch.pwr_n += 1
        self.part("power", entry, f"#PWR{Sch.pwr_n:02d}", name, p[0], p[1], angle=angle,
                  ref_at=None, val_at=val_at, just="center", hide_ref=True, hide_val=hide_val)

    def vcc(self, p, name, side="up"):
        """Supply arrow with its pin at p. side='up' (default) or 'left'."""
        if side == "up":
            self._pwr("VCC", name, p, 0, (p[0], p[1] - 3.81), False)
        else:
            self._pwr("VCC", name, p, 90, (p[0] - 3.81 - tw(name) / 2, p[1]), False)

    def gnd(self, p, side="down"):
        self._pwr("GND", "GND", p, 0 if side == "down" else 270, None, True)

    def flag(self, ref, p):
        self.part("power", "PWR_FLAG", ref, "PWR_FLAG", p[0], p[1], hide_ref=True, hide_val=True)

    def note(self, p, s, size=FONT, just="left"):
        self.sch.texts.append(Text(text=s, position=Position(X=snap(p[0]), Y=snap(p[1]), angle=0),
                                   effects=Effects(font=Font(height=size, width=size),
                                                   justify=Justify(horizontally=None if just == "center" else just))))

    def frame(self, x1, y1, x2, y2, title):
        self.sch.shapes.append(Rectangle(
            start=Position(X=snap(x1), Y=snap(y1)), end=Position(X=snap(x2), Y=snap(y2)),
            stroke=Stroke(width=0, type="dash"), uuid=self.uid()))
        self.note((x1 + 2.54, y1 + 3.81), title, size=2.0)


sh = None  # current page, set in the page loop at the bottom
G = 2.54


def R(ref, val, x, y, horizontal=False, fields="right"):
    """Device:R. Vertical: pin1 top, pin2 bottom. Horizontal: pin1 left, pin2 right."""
    if horizontal:
        if fields == "above":
            return sh.part("Device", "R", ref, val, x, y, angle=90, ref_at=(x, y - 4.445), val_at=(x, y - 2.54))
        return sh.part("Device", "R", ref, val, x, y, angle=90, ref_at=(x, y - 2.54), val_at=(x, y + 2.54))
    if fields == "right":
        return sh.part("Device", "R", ref, val, x, y, ref_at=(x + 2.54, y - 1.27), val_at=(x + 2.54, y + 1.27))
    return sh.part("Device", "R", ref, val, x, y, ref_at=(x - 2.54, y - 1.27), val_at=(x - 2.54, y + 1.27),
                   just="right")


def C(ref, val, x, y, pol=False, fields="right"):
    entry = "C_Polarized" if pol else "C"
    dx = 3.175 if pol else 2.54
    if fields == "right":
        return sh.part("Device", entry, ref, val, x, y, ref_at=(x + dx, y - 1.27), val_at=(x + dx, y + 1.27))
    return sh.part("Device", entry, ref, val, x, y, ref_at=(x - dx, y - 1.27), val_at=(x - dx, y + 1.27),
                   just="right")


# =================================================================== BLOCKS
def block_power(ox, oy):
    rail = oy + 17.78
    gy = oy + 43.18
    # battery
    bt = sh.part("Device", "Battery_Cell", "BT1", "1S LiPo 3,7 V", ox + 10.16, oy + 27.94,
                 ref_at=(ox + 6.35, oy + 26.67), val_at=(ox + 6.35, oy + 29.21), just="right")
    sh.w(bt["1"], (ox + 10.16, rail), (ox + 10.16, oy + 12.7))
    sh.vcc((ox + 10.16, oy + 12.7), "BAT_P")
    sh.j((ox + 10.16, rail))
    sh.w(bt["2"], (ox + 10.16, gy), (ox + 7.62, gy)); sh.lbl((ox + 7.62, gy), "BAT_N", "L")
    sh.w((ox + 10.16, oy + 35.56), (ox + 5.08, oy + 35.56)); sh.j((ox + 10.16, oy + 35.56))
    sh.flag("#FLG1", (ox + 5.08, oy + 35.56))
    # MT3608 boost 3.7 V -> 5.1 V
    c19 = C("C19", "22u", ox + 15.24, oy + 21.59)
    sh.j((ox + 15.24, rail)); sh.w(c19["2"], (ox + 15.24, gy)); sh.gnd((ox + 15.24, gy))
    ux, uy = ox + 33.02, oy + 30.48
    u1 = sh.part("Regulator_Switching", "MT3608", "U1", "MT3608", ux, uy,
                 ref_at=(ux - 5.08, oy + 40.64), val_at=(ux - 5.08, oy + 43.18), just="right")
    sh.w((ox + 22.86, rail), (ox + 22.86, u1["5"][1]), u1["5"]); sh.j((ox + 22.86, rail))
    sh.w((ox + 22.86, u1["5"][1]), (ox + 22.86, u1["4"][1]), u1["4"]); sh.j((ox + 22.86, u1["5"][1]))
    sh.w(u1["2"], (ux, gy)); sh.gnd((ux, gy))
    l1 = sh.part("Device", "L", "L1", "10u", ox + 30.48, rail, angle=90,
                 ref_at=(ox + 30.48, rail - 4.445), val_at=(ox + 30.48, rail - 2.54))
    sh.w((ox + 10.16, rail), l1["1"])
    sw = ox + 43.18
    sh.w(l1["2"], (sw, rail), (sw, u1["1"][1]), u1["1"]); sh.j((sw, rail))
    d3 = sh.part("Diode", "SS34", "D3", "SS34", ox + 49.53, rail, angle=180,
                 ref_at=(ox + 49.53, rail - 4.445), val_at=(ox + 49.53, rail - 2.54))
    sh.w((sw, rail), d3["2"])
    k = ox + 53.34
    r24 = R("R24", "75k", k, oy + 24.13)
    r25 = R("R25", "10k", k, oy + 36.83)
    sh.j((k, rail)); sh.w((k, rail), r24["1"])
    sh.w(r24["2"], r25["1"]); sh.j((k, u1["3"][1])); sh.w((k, u1["3"][1]), u1["3"])
    sh.w(r25["2"], (k, gy)); sh.gnd((k, gy))
    # 5 V rail
    x5, xf, xc20, xc1, xc2 = ox + 58.42, ox + 63.5, ox + 68.58, ox + 78.74, ox + 88.9
    u2x = ox + 106.68
    u2 = sh.part("Regulator_Linear", "AMS1117-3.3", "U2", "AMS1117-3.3", u2x, rail,
                 ref_at=(u2x, oy + 8.89), val_at=(u2x, oy + 11.43), just="center")
    sh.w(d3["1"], u2["3"])
    sh.w((x5, rail), (x5, oy + 12.7)); sh.j((x5, rail)); sh.vcc((x5, oy + 12.7), "5V_PERIPH")
    sh.j((xf, rail)); sh.flag("#FLG2", (xf, rail))
    for ref, val, x, pol in (("C20", "22u", xc20, False), ("C1", "100u", xc1, False), ("C2", "10u", xc2, False)):
        c = C(ref, val, x, oy + 24.13, pol=pol)
        sh.w((x, rail), c["1"]); sh.j((x, rail))
        sh.w(c["2"], (x, gy)); sh.gnd((x, gy))
    sh.w(u2["1"], (u2x, gy)); sh.gnd((u2x, gy))
    # 3V3 (tantalum on the LDO output: the AMS1117 needs some ESR to stay stable)
    xc3, x3 = ox + 121.92, ox + 129.54
    sh.w(u2["2"], (x3, rail), (x3, oy + 12.7)); sh.vcc((x3, oy + 12.7), "3V3_MCU")
    c3 = C("C3", "10u", xc3, oy + 24.13, pol=True)
    sh.w((xc3, rail), c3["1"]); sh.j((xc3, rail))
    sh.w(c3["2"], (xc3, gy)); sh.gnd((xc3, gy))
    sh.frame(ox - 10.16, oy - 5.08, ox + 139.7, oy + 50.8, "Stromversorgung")


def block_charger(ox, oy):
    gy = oy + 40.64
    ux = ox + 38.1
    u3 = sh.part("Battery_Management", "MCP73831-2-OT", "U3", "MCP73831", ux, oy + 25.4,
                 ref_at=(ux + 2.54, oy + 15.24), val_at=(ux + 2.54, oy + 17.78))
    sh.w(u3["4"], (ux, oy + 12.7), (ox + 7.62, oy + 12.7))
    sh.vcc((ox + 7.62, oy + 12.7), "VBUS_NATIVE")
    c4 = C("C4", "1u", ox + 15.24, oy + 16.51)
    sh.j((ox + 15.24, oy + 12.7)); sh.w(c4["2"], (ox + 15.24, gy)); sh.gnd((ox + 15.24, gy))
    sh.j((ox + 22.86, oy + 12.7)); sh.flag("#FLG3", (ox + 22.86, oy + 12.7))
    r1 = R("R1", "2k", ox + 22.86, oy + 31.75)
    sh.w(u3["5"], r1["1"]); sh.w(r1["2"], (ox + 22.86, gy)); sh.gnd((ox + 22.86, gy))
    sh.w(u3["2"], (ux, gy)); sh.gnd((ux, gy))
    sh.w(u3["3"], (ox + 53.34, oy + 22.86), (ox + 53.34, oy + 12.7), (ox + 66.04, oy + 12.7))
    sh.vcc((ox + 66.04, oy + 12.7), "BAT_P")
    c5 = C("C5", "1u", ox + 60.96, oy + 16.51)
    sh.j((ox + 60.96, oy + 12.7)); sh.w(c5["2"], (ox + 60.96, oy + 22.86)); sh.gnd((ox + 60.96, oy + 22.86))
    r2 = R("R2", "10k", ox + 76.2, oy + 24.13)
    d5 = sh.part("Device", "D_Schottky", "D5", "1N5819WS", ox + 68.58, oy + 27.94,
                 ref_at=(ox + 68.58, oy + 31.75), val_at=(ox + 68.58, oy + 34.29), just="center")
    sh.w(u3["1"], d5["1"]); sh.w(d5["2"], (ox + 83.82, oy + 27.94)); sh.j((ox + 76.2, oy + 27.94))
    sh.lbl((ox + 83.82, oy + 27.94), "CHRG_STAT", "R")
    sh.w(r2["1"], (ox + 76.2, oy + 17.78)); sh.vcc((ox + 76.2, oy + 17.78), "3V3_MCU")
    sh.frame(ox - 2.54, oy - 5.08, ox + 99.06, oy + 48.26, "Laden (USB-C)")


def block_adc(ox, oy):
    gy = oy + 40.64
    x = ox + 10.16
    r3 = R("R3", "100k", x, oy + 20.32, fields="left")
    r4 = R("R4", "100k", x, oy + 31.75, fields="left")
    sh.w(r3["1"], (x, oy + 12.7)); sh.vcc((x, oy + 12.7), "BAT_P")
    sh.w(r3["2"], r4["1"])
    sh.w((x, oy + 25.4), (ox + 27.94, oy + 25.4)); sh.j((x, oy + 25.4))
    sh.lbl((ox + 27.94, oy + 25.4), "ADC_BATT", "R")
    c6 = C("C6", "100n", ox + 20.32, oy + 29.21)
    sh.j((ox + 20.32, oy + 25.4)); sh.w(c6["2"], (ox + 20.32, gy)); sh.gnd((ox + 20.32, gy))
    sh.w(r4["2"], (x, gy)); sh.gnd((x, gy))
    sh.frame(ox - 7.62, oy - 5.08, ox + 40.64, oy + 48.26, "Akku-Messung")


def block_audio(ox, oy):
    ax, ay = ox + 33.02, oy + 33.02
    u6 = sh.part("Audio", "MAX98357A", "U6", "MAX98357A", ax, ay,
                 ref_at=(ax - 2.54, ay - 15.24), val_at=(ax - 2.54, ay - 12.7), just="right")
    sh.w(u6["7"], (ax, ay - 25.4)); sh.vcc((ax, ay - 25.4), "5V_PERIPH")
    sh.w((ax, ay - 22.86), (ax + 17.78, ay - 22.86)); sh.j((ax, ay - 22.86))
    for ref, val, x in (("C22", "10u", ax + 12.7), ("C23", "100n", ax + 17.78)):
        c = C(ref, val, x, ay - 19.05)
        if x != ax + 17.78:
            sh.j((x, ay - 22.86))
        sh.w(c["2"], (x, ay - 12.7)); sh.gnd((x, ay - 12.7))
    for num, name in (("1", "I2S_DOUT"), ("16", "I2S_BCLK"), ("14", "I2S_LRCLK")):
        p = u6[num]
        sh.w(p, (p[0] - 2.54, p[1])); sh.lbl((p[0] - 2.54, p[1]), name, "L")
    sd = u6["4"]
    sh.w(sd, (sd[0] - 2.54, sd[1])); sh.vcc((sd[0] - 2.54, sd[1]), "5V_PERIPH", side="left")
    gs = u6["2"]
    sh.w(gs, (gs[0] - 2.54, gs[1]), (gs[0] - 2.54, ay + 15.24)); sh.gnd((gs[0] - 2.54, ay + 15.24))
    g, pad = u6["3"], u6["17"]
    sh.w(g, (g[0], ay + 15.24)); sh.w(pad, (pad[0], ay + 15.24), (g[0], ay + 15.24))
    sh.gnd((g[0], ay + 15.24)); sh.j((g[0], ay + 15.24))
    spx = ax + 25.4
    sp = sh.part("Device", "Speaker", "SP1", "Lautsprecher", spx, ay - 7.62,
                 ref_at=(spx + 3.81, ay - 8.89), val_at=(spx + 3.81, ay - 6.35))
    sh.w(u6["9"], sp["1"]); sh.w(u6["10"], sp["2"])
    sh.frame(ox - 2.54, oy - 5.08, ox + 78.74, oy + 53.34, "Sound (I²S)")


# ESP32-S3-WROOM-1 pin numbers (module pads) -> net
MCU_SIGNALS = {
    "4": "TRIGGER", "5": "RELOAD", "6": "IR_GATE", "12": "ADC_BATT",
    "10": "WS2812_DIN_3V3", "11": "CHRG_STAT", "13": "USB_D-", "14": "USB_D+",
    # layout-driven: pad order matches the order of the targets on the board (no crossings)
    "18": "TSOP1_OUT", "19": "TSOP2_OUT", "20": "TSOP3_OUT", "21": "TSOP4_OUT", "22": "TSOP5_OUT",
    "24": "VIB", "31": "I2S_DOUT", "32": "I2S_BCLK", "33": "I2S_LRCLK",
    # OLED (I2C) and rotary encoder: connectors J4/J5 at the right edge next to these pads
    "39": "I2C_SCL", "38": "I2C_SDA", "35": "ENC_A", "34": "ENC_B", "17": "ENC_SW",
    "9": "TSOP6_OUT",  # TSOP 6 on the weapon itself, connector J6 (former second IR LED)
    # SPI-NAND for audio files (SPI2 over the GPIO matrix): left pads 7/8 and bottom pads 15/16
    "7": "FLASH_CS", "8": "SPI_MISO", "15": "SPI_MOSI", "16": "SPI_CLK",
    "25": "SD_CS",  # microSD slot J7 on the same SPI bus
}
# unused: IO21, IO45 (strapping), TXD0/RXD0, IO35-37 (octal PSRAM on N16R8)
MCU_UNUSED = ["37", "36", "28", "29", "30", "23", "26"]


def block_mcu(ox, oy):
    mx, my = ox + 55.88, oy + 50.8
    u4 = sh.part("RF_Module", "ESP32-S3-WROOM-1", "U4", "ESP32-S3-WROOM-1-N16R8", mx, my,
                 ref_at=(mx + 2.54, my + 29.21), val_at=(mx + 2.54, my + 31.75))
    # 3V3 with local decoupling
    sh.w(u4["2"], (mx, my - 38.1), (mx + 30.48, my - 38.1))
    sh.w((mx, my - 38.1), (mx, my - 40.64)); sh.vcc((mx, my - 40.64), "3V3_MCU"); sh.j((mx, my - 38.1))
    c17 = C("C17", "100n", mx + 22.86, my - 34.29, fields="left")
    sh.j((mx + 22.86, my - 38.1)); sh.w(c17["2"], (mx + 22.86, my - 27.94)); sh.gnd((mx + 22.86, my - 27.94))
    c18 = C("C18", "10u", mx + 30.48, my - 34.29)
    sh.w(c18["2"], (mx + 30.48, my - 27.94)); sh.gnd((mx + 30.48, my - 27.94))
    sh.w(u4["1"], (mx, my + 30.48)); sh.gnd((mx, my + 30.48))
    # EN: RC power-on reset + RESET button
    yn = my - 33.02
    sh.w(u4["3"], (mx - 17.78, my - 22.86), (mx - 17.78, yn), (mx - 38.1, yn))
    r21 = R("R21", "10k", mx - 22.86, yn - 3.81, fields="left")
    sh.j((mx - 22.86, yn)); sh.w(r21["1"], (mx - 22.86, yn - 10.16)); sh.vcc((mx - 22.86, yn - 10.16), "3V3_MCU")
    c16 = C("C16", "1u", mx - 27.94, yn + 3.81, fields="left")
    sh.j((mx - 27.94, yn)); sh.w(c16["2"], (mx - 27.94, yn + 10.16)); sh.gnd((mx - 27.94, yn + 10.16))
    s3 = sh.part("Switch", "SW_Push", "SW3", "RESET", mx - 43.18, yn,
                 ref_at=(mx - 43.18, yn - 5.08), val_at=(mx - 43.18, yn + 3.81), just="center")
    sh.w(s3["1"], (mx - 48.26, yn + 10.16)); sh.gnd((mx - 48.26, yn + 10.16))
    # IO0: BOOT button (download mode)
    s4 = sh.part("Switch", "SW_Push", "SW4", "BOOT", mx - 43.18, my - 17.78,
                 ref_at=(mx - 43.18, my - 22.86), val_at=(mx - 43.18, my - 13.97), just="center")
    sh.w(u4["27"], s4["2"])
    sh.w(s4["1"], (mx - 48.26, my - 12.7)); sh.gnd((mx - 48.26, my - 12.7))
    for num, net in MCU_SIGNALS.items():
        p = u4[num]
        if p[0] < mx:
            sh.w(p, (p[0] - 2.54, p[1])); sh.lbl((p[0] - 2.54, p[1]), net, "L")
        else:
            sh.w(p, (p[0] + 2.54, p[1])); sh.lbl((p[0] + 2.54, p[1]), net, "R")
    for num in MCU_UNUSED:
        sh.nc(u4[num])
    sh.note((mx - 50.8, my + 35.56), "frei: IO21")
    sh.frame(mx - 53.34, oy - 5.08, mx + 40.64, my + 43.18, "ESP32-S3-WROOM-1")


def block_usb(ox, oy):
    jx, jy = ox + 12.7, oy + 30.48
    x1 = jx + 17.78
    j3 = sh.part("Connector", "USB_C_Receptacle_USB2.0_16P", "J3", "USB-C (Flashen + Laden)", jx, jy,
                 ref_at=(jx, jy - 22.86), val_at=(jx, jy - 20.32), just="center")
    sh.w(j3["A4"], (x1, jy - 15.24), (x1, jy - 20.32)); sh.vcc((x1, jy - 20.32), "VBUS_NATIVE")
    # CC pull-downs: 5.1k each, so a USB-C charger actually switches VBUS on
    sh.w(j3["A5"], (jx + 50.8, jy - 10.16))
    r23 = R("R23", "5.1k", jx + 50.8, jy - 6.35)
    sh.w(r23["2"], (jx + 50.8, jy)); sh.gnd((jx + 50.8, jy))
    sh.w(j3["B5"], (jx + 43.18, jy - 7.62))
    r22 = R("R22", "5.1k", jx + 43.18, jy - 3.81)
    sh.w(r22["2"], (jx + 43.18, jy + 2.54)); sh.gnd((jx + 43.18, jy + 2.54))
    # D-/D+ (both connector rows), through the ESD array
    ex = jx + 30.48
    esd = sh.part("Power_Protection", "USBLC6-2SC6", "U12", "USBLC6-2SC6", ex, jy + 7.62,
                  ref_at=(ex + 2.54, jy + 15.24), val_at=(ex + 2.54, jy + 17.78))
    sh.w(j3["A7"], (x1, jy - 2.54), (x1, jy)); sh.w(j3["B7"], (x1, jy)); sh.j((x1, jy))
    sh.w((x1, jy), (jx + 22.86, jy), (jx + 22.86, jy + 7.62), esd["1"])
    sh.w(j3["A6"], (x1, jy + 2.54), (x1, jy + 5.08)); sh.w(j3["B6"], (x1, jy + 5.08)); sh.j((x1, jy + 5.08))
    sh.w((x1, jy + 5.08), (x1, jy + 10.16), esd["3"])
    sh.w(esd["6"], (ex + 7.62, jy + 7.62)); sh.lbl((ex + 7.62, jy + 7.62), "USB_D-", "R")
    sh.w(esd["4"], (ex + 7.62, jy + 10.16)); sh.lbl((ex + 7.62, jy + 10.16), "USB_D+", "R")
    sh.w(esd["5"], (ex, jy)); sh.vcc((ex, jy), "VBUS_NATIVE")
    sh.w(esd["2"], (ex, jy + 17.78)); sh.gnd((ex, jy + 17.78))
    # GND + shield
    sh.w(j3["SH"], (jx - 7.62, jy + 25.4), (jx, jy + 25.4)); sh.w(j3["A1"], (jx, jy + 25.4))
    sh.gnd((jx, jy + 25.4)); sh.j((jx, jy + 25.4))
    sh.nc(j3["A8"]); sh.nc(j3["B8"])
    sh.frame(ox - 2.54, oy - 5.08, ox + 71.12, oy + 63.5, "USB-C (nativer USB des ESP32-S3)")


def block_ir(ox, oy):
    xa, xb, xc = ox + 40.64, ox + 55.88, ox + 73.66
    rail, kline = oy + 12.7, oy + 40.64
    gy = oy + 60.96
    sh.w((xa - 7.62, rail), (xc, rail), (xc, oy + 22.86))
    sh.vcc((xa - 7.62, rail), "BAT_P")
    for x, rr, led in ((xa, "R7", "LED1"),):
        r = R(rr, "10", x, oy + 20.32)
        d = sh.part("Device", "LED", led, "TSAL6100", x, oy + 31.75, angle=90,
                    ref_at=(x + 7.62, oy + 30.48), val_at=(x + 7.62, oy + 33.02))
        sh.w((x, rail), r["1"]); sh.j((x, rail))
        sh.w(r["2"], d["2"])
        sh.w(d["1"], (x, kline))
    c7 = C("C7", "100u", xc, oy + 26.67)
    sh.w(c7["2"], (xc, oy + 33.02)); sh.gnd((xc, oy + 33.02))
    q = sh.part("Transistor_FET", "AO3400A", "Q1", "AO3400A", xa - 2.54, oy + 50.8,
                ref_at=(xa + 2.54, oy + 49.53), val_at=(xa + 2.54, oy + 52.07))
    sh.w((xa, kline), q["3"])
    sh.w(q["2"], (xa, gy)); sh.gnd((xa, gy))
    r5 = R("R5", "100", xa - 17.78, oy + 50.8, horizontal=True, fields="above")
    sh.w(r5["2"], q["1"])
    r6 = R("R6", "100k", xa - 10.16, oy + 54.61, fields="left")
    sh.j((xa - 10.16, oy + 50.8)); sh.w(r6["2"], (xa - 10.16, gy)); sh.gnd((xa - 10.16, gy))
    sh.w(r5["1"], (xa - 24.13, oy + 50.8)); sh.lbl((xa - 24.13, oy + 50.8), "IR_GATE", "L")
    sh.frame(ox + 2.54, oy - 5.08, ox + 86.36, oy + 68.58, "IR-Sender (TSAL6100)")


def block_buttons(ox, oy):
    tx = ox + 12.7
    for i, (net, sw, rr, cc) in enumerate((("TRIGGER", "SW1", "R9", "C8"), ("RELOAD", "SW2", "R10", "C9"))):
        ty = oy + 17.78 + i * 30.48
        r = R(rr, "10k", tx + 7.62, ty - 3.81)
        c = C(cc, "100n", tx + 15.24, ty + 3.81)
        s = sh.part("Switch", "SW_Push", sw, "Taster", tx + 27.94, ty,
                    ref_at=(tx + 27.94, ty - 5.08), val_at=(tx + 27.94, ty + 3.81), just="center")
        sh.lbl((tx, ty), net, "L")
        sh.w((tx, ty), s["1"]); sh.j((tx + 7.62, ty)); sh.j((tx + 15.24, ty))
        sh.w(r["1"], (tx + 7.62, ty - 10.16)); sh.vcc((tx + 7.62, ty - 10.16), "3V3_MCU")
        sh.w(c["2"], (tx + 15.24, ty + 10.16)); sh.gnd((tx + 15.24, ty + 10.16))
        sh.w(s["2"], (tx + 33.02, ty + 10.16)); sh.gnd((tx + 33.02, ty + 10.16))
    sh.frame(ox - 2.54, oy - 5.08, ox + 53.34, oy + 68.58, "Abzug / Nachladen")


def block_ws2812(ox, oy):
    ux, uy = ox + 20.32, oy + 12.7
    ua = sh.part("74xx", "74AHCT125", "U5", "74HCT125", ux, uy, unit=1,
                 ref_at=(ux, uy - 6.35), val_at=(ux - 7.62, uy - 3.81), just="center", hide_val=True)
    sh.w(ua["2"], (ux - 10.16, uy)); sh.lbl((ux - 10.16, uy), "WS2812_DIN_3V3", "L")
    sh.w(ua["1"], (ux, uy + 10.16)); sh.gnd((ux, uy + 10.16))
    r15 = R("R15", "330", ux + 17.78, uy, horizontal=True, fields="above")
    sh.w(ua["3"], r15["1"])
    jx = ox + 55.88
    j1 = sh.part("Connector_Generic", "Conn_01x03", "J1", "WS2812 HP-Streifen", jx, oy + 27.94,
                 ref_at=(jx + 2.54, oy + 26.67), val_at=(jx + 2.54, oy + 29.21))
    sh.w(r15["2"], (ox + 48.26, uy), (ox + 48.26, j1["1"][1]), j1["1"])
    sh.w(j1["2"], (ox + 40.64, j1["2"][1]), (ox + 40.64, oy + 22.86)); sh.vcc((ox + 40.64, oy + 22.86), "5V_PERIPH")
    c10 = C("C10", "100u", ox + 45.72, oy + 31.75, fields="left")
    sh.j((ox + 45.72, j1["2"][1])); sh.w(c10["2"], (ox + 45.72, oy + 38.1)); sh.gnd((ox + 45.72, oy + 38.1))
    sh.w(j1["3"], (ox + 49.53, j1["3"][1]), (ox + 49.53, oy + 38.1)); sh.gnd((ox + 49.53, oy + 38.1))
    py = oy + 50.8
    ue = sh.part("74xx", "74AHCT125", "U5", "74HCT125", ux, py, unit=5,
                 ref_at=(ux + 6.35, py), val_at=None, hide_val=True)
    sh.w(ue["14"], (ux, py - 15.24)); sh.vcc((ux, py - 15.24), "5V_PERIPH")
    sh.w((ux, py - 15.24), (ux - 7.62, py - 15.24)); sh.j((ux, py - 15.24))
    c21 = C("C21", "100n", ux - 7.62, py - 11.43, fields="left")
    sh.w(c21["2"], (ux - 7.62, py - 5.08)); sh.gnd((ux - 7.62, py - 5.08))
    sh.w(ue["7"], (ux, py + 15.24)); sh.gnd((ux, py + 15.24))
    for k, (unit, a, y, oe) in enumerate(((2, "5", "6", "4"), (3, "9", "8", "10"), (4, "12", "11", "13"))):
        gx = ox + 45.72 + k * 20.32
        u = sh.part("74xx", "74AHCT125", "U5", "74HCT125", gx, py, unit=unit,
                    ref_at=(gx, py - 6.35), val_at=None, just="center", hide_val=True)
        sh.w(u[a], (gx - 10.16, py), (gx - 10.16, py + 10.16)); sh.gnd((gx - 10.16, py + 10.16))
        sh.w(u[oe], (gx, py + 10.16)); sh.gnd((gx, py + 10.16))
        sh.nc(u[y])
    sh.note((ox + 22.86, oy + 69.85), "unbenutzte Gatter: Eingänge + /OE auf GND")
    sh.frame(ox - 5.08, oy - 5.08, ox + 96.52, oy + 73.66, "WS2812 (5 V) über Pegelwandler")


def block_vibration(ox, oy):
    for i, (net, q, rg, rp, m, d, mval) in enumerate((
            ("VIB", "Q2", "R11", "R12", "M1", "D1", "Vibromotor"),)):
        dx, dy = ox + 12.7 + i * 52.07, oy + 22.86
        mm = sh.part("Motor", "Motor_DC", m, mval, dx + 25.4, dy,
                     ref_at=(dx + 21.59, dy - 1.27), val_at=(dx + 21.59, dy + 1.27), just="right")
        dd = sh.part("Diode", "SS14", d, "B5819W", dx + 35.56, dy + 1.27, angle=270,
                     ref_at=(dx + 40.64, dy), val_at=(dx + 40.64, dy + 2.54))
        top, bot = dy - 10.16, dy + 12.7
        sh.w(mm["1"], (dx + 25.4, dy - 15.24)); sh.vcc((dx + 25.4, dy - 15.24), "5V_PERIPH")
        sh.w(dd["1"], (dx + 35.56, top), (dx + 25.4, top)); sh.j((dx + 25.4, top))
        sh.w(dd["2"], (dx + 35.56, bot), (dx + 25.4, bot)); sh.j((dx + 25.4, bot))
        qq = sh.part("Transistor_FET", "AO3400A", q, "AO3400A", dx + 22.86, dy + 22.86,
                     ref_at=(dx + 27.94, dy + 21.59), val_at=(dx + 27.94, dy + 24.13))
        sh.w(mm["2"], qq["3"])
        sh.w(qq["2"], (dx + 25.4, dy + 33.02)); sh.gnd((dx + 25.4, dy + 33.02))
        r1 = R(rg, "100", dx + 7.62, dy + 22.86, horizontal=True, fields="above")
        sh.w(r1["2"], qq["1"])
        r2 = R(rp, "100k", dx + 13.97, dy + 26.67, fields="left")
        sh.j((dx + 13.97, dy + 22.86)); sh.w(r2["2"], (dx + 13.97, dy + 33.02)); sh.gnd((dx + 13.97, dy + 33.02))
        sh.w(r1["1"], (dx + 1.27, dy + 22.86)); sh.lbl((dx + 1.27, dy + 22.86), net, "L")
    sh.frame(ox - 2.54, oy - 5.08, ox + 59.69, oy + 63.5, "Vibration (Rückstoss + Treffer)")


def block_ui(ox, oy):
    """OLED display on I2C (Qwiic pinout) and rotary encoder with push button,
    one JST-SH connector each. Pull-ups: on the OLED module / ESP32 internal."""
    for k, (ref, val, pins) in enumerate((
            ("J4", "OLED I²C (Qwiic)", ("GND", "3V3_MCU", "I2C_SDA", "I2C_SCL")),
            ("J5", "Drehgeber", ("GND", "ENC_SW", "ENC_B", "ENC_A")))):
        jx, jy = ox + 33.02 + k * 50.8, oy + 17.78
        j = sh.part("Connector_Generic", "Conn_01x04", ref, val, jx, jy,
                    ref_at=(jx + 2.54, jy - 6.35), val_at=(jx + 2.54, jy - 3.81))
        for n, net in enumerate(pins, 1):
            p = j[str(n)]
            if net == "GND":
                sh.w(p, (p[0] - 5.08, p[1])); sh.gnd((p[0] - 5.08, p[1]), side="left")
            elif net == "3V3_MCU":
                sh.w(p, (p[0] - 12.7, p[1]), (p[0] - 12.7, p[1] - 10.16)); sh.vcc((p[0] - 12.7, p[1] - 10.16), net)
            else:
                sh.w(p, (p[0] - 15.24, p[1])); sh.lbl((p[0] - 15.24, p[1]), net, "L")
    sh.note((ox + 2.54, oy + 38.1), "Pull-ups für I²C auf dem OLED-Modul, Drehgeber über interne Pull-ups")
    sh.frame(ox - 2.54, oy - 5.08, ox + 99.06, oy + 43.18, "Bedienung: OLED + Drehgeber")


def block_tsop6(ox, oy):
    """TSOP34838 mounted on the weapon (front), cable to J6 like the vest sensors:
    J6 = 1 VS (3V3), 2 GND, 3 OUT; supply filter 100R + 4.7u at the sensor."""
    jx, jy = ox + 20.32, oy + 25.4
    j6 = sh.part("Connector_Generic", "Conn_01x03", "J6", "TSOP 6 (Waffe)", jx, jy,
                 ref_at=(jx + 2.54, jy - 5.08), val_at=(jx + 2.54, jy - 2.54))
    sh.w(j6["1"], (ox + 10.16, j6["1"][1]), (ox + 10.16, oy + 12.7)); sh.vcc((ox + 10.16, oy + 12.7), "3V3_MCU")
    sh.w(j6["2"], (ox + 12.7, j6["2"][1])); sh.gnd((ox + 12.7, j6["2"][1]), side="left")
    sh.w(j6["3"], (ox + 10.16, j6["3"][1])); sh.lbl((ox + 10.16, j6["3"][1]), "TSOP6_OUT", "L")
    sh.note((ox + 2.54, oy + 40.64), "Kabel zum Sensor an der Waffe")
    cx, cy = ox + 40.64, oy + 30.48
    u = sh.part("Interface_Optical", "TSOP348xx", "U13", "TSOP34838", cx + 12.7, cy,
                ref_at=(cx + 11.43, cy + 8.89), val_at=(cx + 11.43, cy + 11.43), just="center")
    n = (cx + 25.4, cy - 12.7)
    sh.w(u["3"], (cx + 25.4, cy - 5.08), n)
    r = R("R26", "100", cx + 25.4, cy - 16.51)
    sh.w(r["1"], (cx + 25.4, cy - 22.86)); sh.vcc((cx + 25.4, cy - 22.86), "3V3_MCU")
    sh.j(n)
    c = C("C24", "4.7u", cx + 40.64, cy - 8.89, pol=True, fields="left")
    sh.w(n, c["1"])
    sh.j((cx + 35.56, cy - 12.7)); sh.flag("#FLG9", (cx + 35.56, cy - 12.7))
    sh.w(c["2"], (cx + 40.64, cy + 10.16)); sh.gnd((cx + 40.64, cy + 10.16))
    sh.w(u["1"], (cx + 27.94, cy)); sh.lbl((cx + 27.94, cy), "TSOP6_OUT", "R")
    sh.w(u["2"], (cx + 25.4, cy + 5.08), (cx + 25.4, cy + 10.16)); sh.gnd((cx + 25.4, cy + 10.16))
    sh.note((cx + 12.7, cy + 15.24), "Waffe vorne", just="center")
    sh.frame(ox - 10.16, oy - 5.08, ox + 88.9, oy + 50.8, "TSOP 6 (an der Waffe, jenseits des Steckers)")


def block_weste(ox, oy):
    jx, jy = ox + 20.32, oy + 25.4
    j2 = sh.part("Connector_Generic", "Conn_01x07", "J2", "GX16 7-polig", jx, jy,
                 ref_at=(jx + 2.54, jy - 1.27), val_at=(jx + 2.54, jy + 1.27))
    sh.w(j2["1"], (ox + 10.16, j2["1"][1]), (ox + 10.16, oy + 12.7)); sh.vcc((ox + 10.16, oy + 12.7), "3V3_MCU")
    sh.w(j2["2"], (ox + 12.7, j2["2"][1])); sh.gnd((ox + 12.7, j2["2"][1]), side="left")
    for k in range(5):
        p = j2[str(k + 3)]
        sh.w(p, (ox + 10.16, p[1])); sh.lbl((ox + 10.16, p[1]), f"TSOP{k + 1}_J", "L")
    sh.note((ox + 2.54, oy + 40.64), "Sensorkabel zur Weste")
    names = ["Stirnband vorn", "Stirnband hinten", "Brust", "Rücken", "Schultern"]
    for k in range(5):
        cx, cy = ox + 40.64 + k * 44.45, oy + 30.48
        u = sh.part("Interface_Optical", "TSOP348xx", f"U{7 + k}", "TSOP34838", cx + 12.7, cy,
                    ref_at=(cx + 11.43, cy + 8.89), val_at=(cx + 11.43, cy + 11.43), just="center")
        n = (cx + 25.4, cy - 12.7)
        sh.w(u["3"], (cx + 25.4, cy - 5.08), n)
        r = R(f"R{16 + k}", "100", cx + 25.4, cy - 16.51)
        sh.w(r["1"], (cx + 25.4, cy - 22.86)); sh.vcc((cx + 25.4, cy - 22.86), "3V3_MCU")
        sh.j(n)
        c = C(f"C{11 + k}", "4.7u", cx + 40.64, cy - 8.89, pol=True, fields="left")
        sh.w(n, c["1"])
        sh.j((cx + 35.56, cy - 12.7)); sh.flag(f"#FLG{4 + k}", (cx + 35.56, cy - 12.7))
        sh.w(c["2"], (cx + 40.64, cy + 10.16)); sh.gnd((cx + 40.64, cy + 10.16))
        sh.w(u["1"], (cx + 27.94, cy)); sh.lbl((cx + 27.94, cy), f"TSOP{k + 1}_OUT", "R")
        sh.w(u["2"], (cx + 25.4, cy + 5.08), (cx + 25.4, cy + 10.16)); sh.gnd((cx + 25.4, cy + 10.16))
        sh.note((cx + 12.7, cy + 15.24), names[k], just="center")
    sh.frame(ox - 10.16, oy - 5.08, ox + 264.16, oy + 50.8, "Weste (nur Sensoren, jenseits des Steckers)")


def block_flash(ox, oy):
    """SPI-NAND 1 Gbit (128 MB) for audio files, 1-bit SPI: /WP and /HOLD tied high, /CS pulled up."""
    ux, uy = ox + 30.48, oy + 30.48
    u = sh.part("Memory_Flash", "W25Q32JVZP", "U14", "ZD35Q1GC-IB", ux, uy,
                ref_at=(ux + 3.81, uy - 16.51), val_at=(ux + 6.35, uy + 16.51), just="left")
    sh.w(u["8"], (ux, uy - 20.32)); sh.vcc((ux, uy - 20.32), "3V3_MCU")
    sh.w((ux, uy - 17.78), (ux + 15.24, uy - 17.78)); sh.j((ux, uy - 17.78))
    c = C("C25", "100n", ux + 15.24, uy - 13.97)
    sh.w(c["2"], (ux + 15.24, uy - 7.62)); sh.gnd((ux + 15.24, uy - 7.62))
    sh.w(u["4"], (ux, uy + 15.24)); sh.gnd((ux, uy + 15.24))
    sh.w(u["9"], (ux + 2.54, uy + 15.24), (ux, uy + 15.24)); sh.j((ux, uy + 15.24))
    for num, net in (("1", "FLASH_CS"), ("6", "SPI_CLK"), ("5", "SPI_MOSI"), ("2", "SPI_MISO")):
        p = u[num]
        sh.w(p, (ux - 20.32, p[1])); sh.lbl((ux - 20.32, p[1]), net, "L")
    r = R("R27", "10k", ux - 15.24, uy - 11.43)
    sh.j((ux - 15.24, uy - 7.62)); sh.w(r["1"], (ux - 15.24, uy - 20.32)); sh.vcc((ux - 15.24, uy - 20.32), "3V3_MCU")
    wp, hold = u["3"], u["7"]
    sh.w(wp, (ux - 12.7, wp[1])); sh.w(hold, (ux - 12.7, hold[1]), (ux - 12.7, wp[1]))
    sh.j((ux - 12.7, wp[1])); sh.w((ux - 12.7, wp[1]), (ux - 15.24, wp[1])); sh.vcc((ux - 15.24, wp[1]), "3V3_MCU", side="left")
    sh.note((ox + 2.54, oy + 50.8), "Audio-Dateien, SPI2 über GPIO-Matrix")
    sh.frame(ox - 2.54, oy - 5.08, ox + 58.42, oy + 53.34, "Flash 128 MB (SPI-NAND)")


def block_sd(ox, oy):
    """microSD slot on the flash SPI bus (SPI mode): /CS and DAT0 on the ESP32 internal pull-ups, the unused
    DAT1/DAT2 together on one 10k pull-up; card detect open."""
    sx, sy = ox + 50.8, oy + 25.4
    j = sh.part("Connector", "Micro_SD_Card_Det1", "J7", "TF-018", sx, sy,
                ref_at=(sx - 5.08, sy - 22.86), val_at=(sx - 5.08, sy - 20.32), just="left")
    for num, net in (("2", "SD_CS"), ("3", "SPI_MOSI"), ("5", "SPI_CLK"), ("7", "SPI_MISO")):
        p = j[num]
        sh.w(p, (ox + 7.62, p[1])); sh.lbl((ox + 7.62, p[1]), net, "L")
    sh.nc(j["9"])
    d2, d1 = j["1"], j["8"]
    sh.w(d2, (ox + 20.32, d2[1])); sh.lbl((ox + 20.32, d2[1]), "SD_DAT12", "L")
    sh.w(d1, (ox + 20.32, d1[1])); sh.lbl((ox + 20.32, d1[1]), "SD_DAT12", "L")
    r = R("R37", "10k", ox + 15.24, d1[1] + 6.35, fields="left")
    sh.w(r["1"], (ox + 15.24, d1[1] + 2.54), (ox + 20.32, d1[1] + 2.54), (ox + 20.32, d1[1])); sh.j((ox + 20.32, d1[1]))
    sh.w(r["2"], (ox + 15.24, d1[1] + 12.7)); sh.vcc((ox + 15.24, d1[1] + 12.7), "3V3_MCU", side="left")
    sh.vcc(j["4"], "3V3_MCU", side="left")
    sh.gnd(j["6"], side="left")
    sh_ = j["SH"]
    sh.w(sh_, (sh_[0], sh_[1] + 5.08)); sh.gnd((sh_[0], sh_[1] + 5.08))
    c = C("C26", "100n", ox + 91.44, oy + 10.16)
    sh.w(c["1"], (ox + 91.44, oy + 3.81)); sh.vcc((ox + 91.44, oy + 3.81), "3V3_MCU")
    sh.w(c["2"], (ox + 91.44, oy + 16.51)); sh.gnd((ox + 91.44, oy + 16.51))
    sh.note((ox + 2.54, oy + 50.8), "SPI-Modus am Flash-Bus, Karte vor dem Flash initialisieren (CMD0), Kartenerkennung offen")
    sh.frame(ox - 2.54, oy - 5.08, ox + 99.06, oy + 55.88, "microSD-Slot (SPI)")


def block_protect(ox, oy):
    """1S protection in the battery minus lead: DW01A + FS8205A (discharge FET at B-, charge FET at P- = GND).
    D4 feeds 5V_PERIPH from USB, so the board runs (and flashes) without a battery."""
    ux, uy = ox + 45.72, oy + 20.32
    u = sh.part("Battery_Management", "DW01A", "U15", "DW01A", ux, uy,
                ref_at=(ux, uy - 10.16), val_at=(ux, uy - 7.62), just="center")
    vcc, gnd, od, oc, cs, td = u["5"], u["6"], u["1"], u["3"], u["2"], u["4"]
    sh.nc(td)
    r = R("R28", "100", ux - 25.4, vcc[1], horizontal=True, fields="above")
    sh.w(vcc, r["2"]); sh.w(r["1"], (ux - 33.02, vcc[1]), (ux - 33.02, vcc[1] - 5.08)); sh.vcc((ux - 33.02, vcc[1] - 5.08), "BAT_P")
    c = C("C27", "100n", ux - 17.78, vcc[1] + 3.81, fields="left")
    sh.j((ux - 17.78, vcc[1])); sh.j((ux - 12.7, vcc[1])); sh.flag("#FLG11", (ux - 12.7, vcc[1]))
    yb = uy + 10.16
    sh.w(gnd, (ux - 12.7, gnd[1]), (ux - 12.7, yb), (ux - 33.02, yb)); sh.w(c["2"], (ux - 17.78, yb)); sh.j((ux - 17.78, yb))
    sh.lbl((ux - 33.02, yb), "BAT_N", "L")
    qx, qy = ux, uy + 33.02
    q = sh.box("FS8205A", [("G1", "6", "L", -2.54), ("S1", "1", "L", 2.54), ("G2", "4", "R", -2.54), ("S2", "3", "R", 2.54),
                           ("D", "2", "T", -2.54), ("D", "5", "T", 2.54)], 7.62, 7.62, "Q3", "FS8205A", qx, qy,
               ref_at=(qx + 10.16, qy + 10.16), val_at=(qx + 10.16, qy + 12.7), just="left")
    sh.w(od, (od[0], uy + 12.7), (ux - 12.7, uy + 12.7), (ux - 12.7, q["6"][1]), q["6"])
    sh.w(oc, (oc[0], uy + 12.7), (ux + 12.7, uy + 12.7), (ux + 12.7, q["4"][1]), q["4"])
    sh.w(q["2"], (q["2"][0], qy - 12.7), (q["5"][0], qy - 12.7), q["5"])
    sh.w(q["1"], (ux - 17.78, q["1"][1])); sh.lbl((ux - 17.78, q["1"][1]), "BAT_N", "L")
    s2 = q["3"]
    sh.w(s2, (ux + 17.78, s2[1]), (ux + 17.78, s2[1] + 5.08)); sh.gnd((ux + 17.78, s2[1] + 5.08))
    sh.j((ux + 15.24, s2[1])); sh.flag("#FLG10", (ux + 15.24, s2[1]))
    r = R("R29", "1k", ux + 15.24, cs[1], horizontal=True, fields="above")
    sh.w(cs, r["1"]); sh.w(r["2"], (ux + 22.86, cs[1]), (ux + 22.86, cs[1] + 5.08)); sh.gnd((ux + 22.86, cs[1] + 5.08))
    sh.note((ox + 2.54, oy + 71.12), "Trennt bei ca. 4,3 V (Überladung), 2,4 V (Tiefentladung) und Überstrom")
    # USB supply for the 5 V rail (D3 keeps it out of the battery, the boost wins when a battery is in)
    dx, dy = ox + 88.9, oy + 15.24
    d4 = sh.part("Diode", "SS14", "D4", "B5819W", dx, dy, angle=180,
                 ref_at=(dx, dy - 4.445), val_at=(dx, dy + 3.81), just="center")
    sh.w(d4["2"], (dx - 7.62, dy), (dx - 7.62, dy - 5.08)); sh.vcc((dx - 7.62, dy - 5.08), "VBUS_NATIVE")
    sh.w(d4["1"], (dx + 7.62, dy), (dx + 7.62, dy - 5.08)); sh.vcc((dx + 7.62, dy - 5.08), "5V_PERIPH")
    sh.note((dx - 7.62, dy + 10.16), "5 V aus USB (ohne Akku)")
    sh.frame(ox - 2.54, oy - 5.08, ox + 111.76, oy + 76.2, "Akkuschutz + USB-Versorgung")


def block_tsop_r(ox, oy):
    """Series resistors in the sensor cable lines (ESD/short protection of the GPIOs)."""
    for k in range(5):
        y = oy + 7.62 + k * 5.08
        r = R(f"R{30 + k}", "100", ox + 25.4, y, horizontal=True, fields="above" if k == 0 else "right")
        sh.w((ox + 10.16, y), r["1"]); sh.lbl((ox + 10.16, y), f"TSOP{k + 1}_OUT", "L")
        sh.w(r["2"], (ox + 40.64, y)); sh.lbl((ox + 40.64, y), f"TSOP{k + 1}_J", "R")
    sh.frame(ox - 12.7, oy - 5.08, ox + 58.42, oy + 35.56, "Sensorkabel: Serienwiderstände")


# ================================================================== LAYOUT


# ============================================================ FOOTPRINTS
# Everything SMD; THT only where unavoidable (USB-C shield pegs). Parts that live
# off the board (battery, speaker, motors, IR LEDs, trigger/reload switches) get
# the footprint of the board-side connector their cable plugs into.
SH2 = "Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal"
PH2 = "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal"
SH4 = "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal"
FOOTPRINTS = {
    "U1": "Package_TO_SOT_SMD:SOT-23-6", "U2": "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    "U3": "Package_TO_SOT_SMD:SOT-23-5", "U4": "RF_Module:ESP32-S3-WROOM-1",
    "U5": "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
    "U6": "Package_DFN_QFN:TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm",
    "U12": "Package_TO_SOT_SMD:SOT-23-6",
    "Q1": "Package_TO_SOT_SMD:SOT-23", "Q2": "Package_TO_SOT_SMD:SOT-23",
    "D1": "Diode_SMD:D_SOD-123", "D3": "Diode_SMD:D_SMA",
    "L1": "Inductor_SMD:L_Sunlord_MWSA0503S",
    "R7": "Resistor_SMD:R_1206_3216Metric",
    "C1": "Capacitor_SMD:C_1210_3225Metric", "C7": "Capacitor_SMD:C_1210_3225Metric",
    "C10": "Capacitor_SMD:C_1210_3225Metric", "C3": "Capacitor_Tantalum_SMD:CP_EIA-3216-18_Kemet-A",
    "C2": "Capacitor_SMD:C_0805_2012Metric", "C18": "Capacitor_SMD:C_0805_2012Metric",
    "C19": "Capacitor_SMD:C_0805_2012Metric", "C22": "Capacitor_SMD:C_0805_2012Metric", "C20": "Capacitor_SMD:C_0805_2012Metric",
    "J1": "Connector_JST:JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal",
    "J2": "Connector_JST:JST_SH_SM07B-SRSS-TB_1x07-1MP_P1.00mm_Horizontal",
    "J3": "lasertag:USB_C_Receptacle_HX_TYPE-C-16P-180-LT-H10.5_Vertical",  # project library, vertical
    "BT1": PH2, "SP1": PH2,
    "M1": SH2, "LED1": SH2, "SW1": SH2, "SW2": SH2,
    "SW3": "Button_Switch_SMD:SW_SPST_B3U-1000P", "SW4": "Button_Switch_SMD:SW_SPST_B3U-1000P",
    "J4": SH4, "J5": SH4, "J6": "Connector_JST:JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal",
    "U14": "Package_SON:WSON-8-1EP_8x6mm_P1.27mm_EP3.4x4.3mm",
    "J7": "lasertag:microSD_TF-018_PushPull",  # project library
    "U15": "Package_TO_SOT_SMD:SOT-23-6", "Q3": "Package_TO_SOT_SMD:SOT-23-6",
    "D4": "Diode_SMD:D_SOD-123", "D5": "Diode_SMD:D_SOD-323",
    "C26": "Capacitor_SMD:C_0402_1005Metric", "C27": "Capacitor_SMD:C_0402_1005Metric",
}
# JLCPCB/LCSC part numbers (checked for stock 2026-10-11); by reference, fallback by value for 0603 R/C
LCSC = {
    "U1": "C84817", "U2": "C6186", "U3": "C424093", "U4": "C2913202", "U5": "C131316", "U6": "C910544",
    "U12": "C7519", "Q1": "C20917", "Q2": "C20917",
    "D1": "C8598", "D3": "C8678", "L1": "C408412",
    "R7": "C17903",
    "C1": "C23742", "C10": "C23742", "C7": "C23742", "C3": "C7171",  # 100u 10V 1210 / 10u 16V tantalum case A
    "C2": "C15850", "C18": "C15850", "C22": "C15850", "C19": "C45783", "C20": "C45783",
    "J1": "C225234", "J2": "C160406", "J3": "C49261570", "BT1": "C225233", "SP1": "C225233",
    "M1": "C160402", "LED1": "C160402", "SW1": "C160402", "SW2": "C160402",
    "SW3": "C231329", "SW4": "C231329", "J4": "C160404", "J5": "C160404",
    "U14": "C2928927",  # Zetta ZD35Q1GC-IB, supported by espressif/spi_nand_flash
    "J6": "C7430445",
    "J7": "C961679",  # XKB TF-018, microSD push-pull
    "U15": "C351410", "Q3": "C2830320", "D4": "C8598", "D5": "C191023",
    "C26": "C1525", "C27": "C1525",  # 100n 0402  # ZX-SH1.0-3PWT, JST SM03B-compatible (C160403 out of stock)
}
LCSC_0603 = {("R", "10k"): "C25804", ("R", "100k"): "C25803", ("R", "5.1k"): "C23186", ("R", "2k"): "C22975",
             ("R", "330"): "C23138", ("R", "100"): "C22775", ("R", "75k"): "C23242",
             ("C", "100n"): "C14663", ("C", "1u"): "C15849", ("R", "1k"): "C21190"}
SMALL = {f"R{i}" for i in range(28, 35)} | {"R37"}  # 0402 where the board is tight
LCSC_0402 = {"100": "C25076", "10k": "C25744", "1k": "C11702"}
VEST = {f"U{i}" for i in range(7, 12)} | {f"R{i}" for i in range(16, 21)} | {f"C{i}" for i in range(11, 16)}
VEST |= {"U13", "R26", "C24"}  # TSOP 6 sits on the weapon, filter at the sensor


# Soldered by hand (connectors, fallback buttons): no LCSC field -> not in the JLC BOM/CPL; the LCSC numbers for
# the separate parts order are in fertigung/lcsc/waffe_lose_teile.csv
HAND = {"J1", "J2", "J4", "J5", "J6", "BT1", "SP1", "LED1", "M1", "SW1", "SW2", "SW3", "SW4"}


def assign_footprints():
    for inst in sh.sch.schematicSymbols:  # current page
        ref = next(p.value for p in inst.properties if p.key == "Reference")
        if ref.startswith("#"):
            continue
        if ref in VEST:
            inst.onBoard = False  # lives on the vest, not on this PCB
            continue
        fp = FOOTPRINTS.get(ref)
        if fp is None and inst.entryName == "R":
            fp = "Resistor_SMD:R_0402_1005Metric" if ref in SMALL else "Resistor_SMD:R_0603_1608Metric"
        if fp is None and inst.entryName == "C":
            fp = "Capacitor_SMD:C_0603_1608Metric"
        assert fp, f"no footprint for {ref}"
        fprop = next(p for p in inst.properties if p.key == "Footprint")
        fprop.value = fp
        val = next(p.value for p in inst.properties if p.key == "Value")
        if ref in HAND:
            continue
        part = LCSC.get(ref) or (LCSC_0402.get(val) if ref in SMALL else LCSC_0603.get((inst.entryName, val)))
        assert part, f"no LCSC part for {ref} ({val})"
        if not any(p.key == "LCSC" for p in inst.properties):
            lp = copy.deepcopy(fprop)
            lp.key, lp.value = "LCSC", part
            inst.properties.append(lp)


# three rows, 27.94mm between blocks, ~38mm between rows
# one A3 page per function, root page with the sheet symbols; blocks keep their frames
PAGES = [
    ("Stromversorgung", "stromversorgung.kicad_sch",
     [(block_power, 22.86, 38.1), (block_charger, 175.26, 38.1), (block_adc, 309.88, 38.1), (block_protect, 30.48, 124.46)]),
    ("ESP32-S3 und USB", "mcu_usb.kicad_sch", [(block_mcu, 10.16, 38.1), (block_usb, 132.08, 38.1)]),
    ("Bedienung und Aktoren", "bedienung_aktoren.kicad_sch",
     [(block_ir, 10.16, 38.1), (block_buttons, 109.22, 38.1), (block_ws2812, 177.8, 38.1),
      (block_vibration, 289.56, 38.1), (block_ui, 15.24, 129.54)]),
    ("Audio und Speicher", "audio_speicher.kicad_sch",
     [(block_audio, 15.24, 38.1), (block_flash, 109.22, 38.1), (block_sd, 182.88, 38.1)]),
    ("Sensoren", "sensoren.kicad_sch", [(block_weste, 22.86, 38.1), (block_tsop6, 22.86, 116.84), (block_tsop_r, 137.16, 116.84)]),
]
out = os.environ.get("OUT_SCH", "waffe_clean.kicad_sch")
outdir = os.path.dirname(os.path.abspath(out))
root = Sch("Übersicht", paper="A4")
page_files = []
for n, (title, fname, blocks) in enumerate(PAGES):
    sid = root.uid()
    sh = Sch(title, path="/" + sid)
    for fn, ox, oy in blocks:
        fn(ox, oy)
    assign_footprints()
    sh.save(os.path.join(outdir, fname))
    page_files.append(os.path.join(outdir, fname))
    x, y = 25.4, 48.26 + n * 27.94  # one column: KiCad numbers the pages top to bottom
    font = Effects(font=Font(height=FONT, width=FONT), justify=Justify(horizontally="left", vertically="bottom"))
    root.sch.sheets.append(HierarchicalSheet(
        position=Position(X=x, Y=y), width=76.2, height=17.78, fieldsAutoplaced=True,
        stroke=Stroke(width=0.1524, type="solid"), fill=ColorRGBA(R=255, G=255, B=194, A=1), uuid=sid,
        sheetName=Property(key="Sheetname", value=title, position=Position(X=x, Y=y - 0.7116, angle=0), effects=font),
        fileName=Property(key="Sheetfile", value=fname, position=Position(X=x, Y=y + 18.3, angle=0),
                          effects=Effects(font=Font(height=FONT, width=FONT), justify=Justify(horizontally="left", vertically="top"))),
        instances=[HierarchicalSheetProjectInstance(name="waffe_elektronik", paths=[
            HierarchicalSheetProjectPath(sheetInstancePath="/", page=str(n + 2))])]))
sh = root
sh.note((25.4, 35.56), "Signale zwischen den Seiten über globale Labels, Versorgung über Power-Symbole", size=2.0)
root.save(out)


def write_project_lib(paths):
    """Copy the embedded lasertag:* symbols into the project library (identical text -> no lib_symbol_mismatch)."""
    blocks, seen = [], set()
    for path in paths:
        _extract(open(path).read(), blocks, seen)
    os.makedirs(os.path.dirname(PROJECT_LIB), exist_ok=True)
    with open(PROJECT_LIB, "w") as f:
        f.write('(kicad_symbol_lib\n\t(version 20241209)\n\t(generator "lasertag")\n')
        for b in blocks:
            f.write("\t" + b + "\n")
        f.write(")\n")


def _extract(t, blocks, seen):
    i = t.find('(symbol "lasertag:')
    while i >= 0:
        depth, j = 0, i
        while True:
            c = t[j]
            depth += c == "("
            depth -= c == ")"
            j += 1
            if depth == 0:
                break
        name = t[i:t.find('"', i + 9)]
        if name not in seen:
            seen.add(name)
            blocks.append(t[i:j].replace('(symbol "lasertag:', '(symbol "', 1))
        i = t.find('(symbol "lasertag:', j)


write_project_lib(page_files)
print("ok ->", out)
