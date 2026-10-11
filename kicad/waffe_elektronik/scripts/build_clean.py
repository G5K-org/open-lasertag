#!/usr/bin/env python3
"""Hand-laid-out schematic for the Lasertag-Waffe (single ESP32-S3).

Every block is drawn deliberately instead of auto-routed: parts sit on the
1.27/2.54mm grid, wires are short and straight, supply arrows point up, ground
symbols hang down, and signals that leave a block do so through a net label on
a short stub (standard practice - long wires across the sheet are what made
the previous auto-generated version look like spaghetti).

Connectivity is checked against a reference netlist by scripts/netcmp.py.
"""
import os
import re
import sys
import math
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_sch import Sheet, get_symbol, resolve_units, rotate_lib_pin, snap  # noqa: E402
from kiutils.items.common import Position, Property, Effects, Font, Justify, Stroke, TitleBlock  # noqa: E402
from kiutils.items.schitems import (LocalLabel, Text, Connection, Junction, NoConnect,  # noqa: E402
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


class Sch(Sheet):
    def __init__(self):
        super().__init__()
        self.sch.paper.paperSize = "A2"
        self.sch.paper.portrait = False
        self.sch.titleBlock = TitleBlock(
            title="Lasertag - Waffen-Elektronik", date="2026-10-11", revision="1",
            company="open-lasertag",
            comments={1: "Ein ESP32-S3 in der Waffe, Weste nur Sensoren",
                      2: "ERC-geprüft, KiCad 10"})
        self.pwr_n = 0

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
        for u in sym.units:
            for p in u.pins:
                p.hide = p.number in hidden

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
            paths=[SymbolProjectPath(sheetInstancePath="/", reference=ref, unit=unit)])]
        self.sch.schematicSymbols.append(inst)
        return pins

    def part(self, lib, entry, ref, value, x, y, angle=0, unit=1, ref_at=None, val_at=None,
             just="left", hide_ref=False, hide_val=False):
        path = f"{LIB}/{lib}.kicad_sym"
        self._register(path, entry, lib)
        base = resolve_units(get_symbol(path, entry), path)
        return self._instance(lib, entry, base.units, ref, value, x, y, angle, unit,
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
        if ("Module", entry) not in self.registered_libs:
            top = Symbol(libraryNickname="Module", entryName=entry)
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
            self.registered_libs.add(("Module", entry))
        return self._instance("Module", entry, [u0, u1], ref, value, x, y, 0, 1, ref_at, val_at, just)

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
        """Local label; side 'L' = text runs to the left of p, 'R' = to the right."""
        ang, h = (180, "right") if side == "L" else (0, "left")
        self.sch.labels.append(LocalLabel(
            text=name, position=Position(X=snap(p[0]), Y=snap(p[1]), angle=ang),
            effects=Effects(font=Font(height=FONT, width=FONT), justify=Justify(horizontally=h, vertically="bottom")),
            uuid=self.uid()))

    def _pwr(self, entry, name, p, angle, val_at, hide_val):
        self.pwr_n += 1
        self.part("power", entry, f"#PWR{self.pwr_n:02d}", name, p[0], p[1], angle=angle,
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


sh = Sch()
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
    sh.w(bt["2"], (ox + 10.16, gy)); sh.gnd((ox + 10.16, gy))
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
    l1 = sh.part("Device", "L", "L1", "22u", ox + 30.48, rail, angle=90,
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
    sh.w(u3["1"], (ox + 83.82, oy + 27.94)); sh.j((ox + 76.2, oy + 27.94))
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
    "24": "HIT_VIB", "25": "RECOIL_VIB", "31": "I2S_DOUT", "32": "I2S_BCLK", "33": "I2S_LRCLK",
}
# unused: IO1/IO2 (spare, ammo LEDs/I2C), IO7, IO9, IO15/16, IO3/IO45/IO46 (strapping),
# TXD0/RXD0, IO35-37 (octal PSRAM on N16R8), IO21 (reserved TSOP 6), IO41/42
MCU_UNUSED = ["39", "38", "15", "7", "8", "9", "17", "37", "36", "28", "29", "30", "23", "34", "35",
              "26", "16"]


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
    sh.note((mx - 50.8, my + 35.56), "frei: IO1/IO2 (Munitions-LED / I²C), IO7, IO9, IO15/16, IO41/42")
    sh.note((mx - 50.8, my + 38.1), "IO21 reserviert: TSOP 6 (Waffe vorne)")
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
    for x, rr, led in ((xa, "R7", "LED1"), (xb, "R8", "LED2")):
        r = R(rr, "10", x, oy + 20.32)
        d = sh.part("Device", "LED", led, "TSAL6100", x, oy + 31.75, angle=90,
                    ref_at=(x + 7.62, oy + 30.48), val_at=(x + 7.62, oy + 33.02))
        sh.w((x, rail), r["1"]); sh.j((x, rail))
        sh.w(r["2"], d["2"])
        sh.w(d["1"], (x, kline))
    c7 = C("C7", "100u", xc, oy + 26.67)
    sh.w(c7["2"], (xc, kline), (xa, kline)); sh.j((xb, kline)); sh.j((xa, kline))
    q = sh.part("Transistor_FET", "AO3400A", "Q1", "AO3400A", xa - 2.54, oy + 50.8,
                ref_at=(xa + 2.54, oy + 49.53), val_at=(xa + 2.54, oy + 52.07))
    sh.w((xa, kline), q["3"])
    sh.w(q["2"], (xa, gy)); sh.gnd((xa, gy))
    r5 = R("R5", "100", xa - 17.78, oy + 50.8, horizontal=True, fields="above")
    sh.w(r5["2"], q["1"])
    r6 = R("R6", "100k", xa - 10.16, oy + 54.61, fields="left")
    sh.j((xa - 10.16, oy + 50.8)); sh.w(r6["2"], (xa - 10.16, gy)); sh.gnd((xa - 10.16, gy))
    sh.w(r5["1"], (xa - 24.13, oy + 50.8)); sh.lbl((xa - 24.13, oy + 50.8), "IR_GATE", "L")
    sh.frame(ox + 2.54, oy - 5.08, ox + 86.36, oy + 68.58, "IR-Sender (2× TSAL6100 parallel)")


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
    ua = sh.part("74xx", "74AHCT125", "U5", "74AHCT125", ux, uy, unit=1,
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
    ue = sh.part("74xx", "74AHCT125", "U5", "74AHCT125", ux, py, unit=5,
                 ref_at=(ux + 6.35, py), val_at=None, hide_val=True)
    sh.w(ue["14"], (ux, py - 15.24)); sh.vcc((ux, py - 15.24), "5V_PERIPH")
    sh.w((ux, py - 15.24), (ux - 7.62, py - 15.24)); sh.j((ux, py - 15.24))
    c21 = C("C21", "100n", ux - 7.62, py - 11.43, fields="left")
    sh.w(c21["2"], (ux - 7.62, py - 5.08)); sh.gnd((ux - 7.62, py - 5.08))
    sh.w(ue["7"], (ux, py + 15.24)); sh.gnd((ux, py + 15.24))
    for k, (unit, a, y, oe) in enumerate(((2, "5", "6", "4"), (3, "9", "8", "10"), (4, "12", "11", "13"))):
        gx = ox + 45.72 + k * 20.32
        u = sh.part("74xx", "74AHCT125", "U5", "74AHCT125", gx, py, unit=unit,
                    ref_at=(gx, py - 6.35), val_at=None, just="center", hide_val=True)
        sh.w(u[a], (gx - 10.16, py), (gx - 10.16, py + 10.16)); sh.gnd((gx - 10.16, py + 10.16))
        sh.w(u[oe], (gx, py + 10.16)); sh.gnd((gx, py + 10.16))
        sh.nc(u[y])
    sh.note((ox + 22.86, oy + 69.85), "unbenutzte Gatter: Eingänge + /OE auf GND")
    sh.frame(ox - 5.08, oy - 5.08, ox + 96.52, oy + 73.66, "WS2812 (5 V) über Pegelwandler")


def block_vibration(ox, oy):
    for i, (net, q, rg, rp, m, d, mval) in enumerate((
            ("RECOIL_VIB", "Q2", "R11", "R12", "M1", "D1", "Vibromotor Rückstoss"),
            ("HIT_VIB", "Q3", "R13", "R14", "M2", "D2", "Vibromotor Treffer"))):
        dx, dy = ox + 12.7 + i * 52.07, oy + 22.86
        mm = sh.part("Motor", "Motor_DC", m, mval, dx + 25.4, dy,
                     ref_at=(dx + 21.59, dy - 1.27), val_at=(dx + 21.59, dy + 1.27), just="right")
        dd = sh.part("Diode", "SS14", d, "SS14", dx + 35.56, dy + 1.27, angle=270,
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
    sh.frame(ox - 2.54, oy - 5.08, ox + 111.76, oy + 63.5, "Rückstoss- / Treffer-Vibration")


def block_weste(ox, oy):
    jx, jy = ox + 20.32, oy + 25.4
    j2 = sh.part("Connector_Generic", "Conn_01x07", "J2", "GX16 7-polig", jx, jy,
                 ref_at=(jx + 2.54, jy - 1.27), val_at=(jx + 2.54, jy + 1.27))
    sh.w(j2["1"], (ox + 10.16, j2["1"][1]), (ox + 10.16, oy + 12.7)); sh.vcc((ox + 10.16, oy + 12.7), "3V3_MCU")
    sh.w(j2["2"], (ox + 12.7, j2["2"][1])); sh.gnd((ox + 12.7, j2["2"][1]), side="left")
    for k in range(5):
        p = j2[str(k + 3)]
        sh.w(p, (ox + 10.16, p[1])); sh.lbl((ox + 10.16, p[1]), f"TSOP{k + 1}_OUT", "L")
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


# ================================================================== LAYOUT


# ============================================================ FOOTPRINTS
# Everything SMD; THT only where unavoidable (USB-C shield pegs). Parts that live
# off the board (battery, speaker, motors, IR LEDs, trigger/reload switches) get
# the footprint of the board-side connector their cable plugs into.
SH2 = "Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal"
PH2 = "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal"
FOOTPRINTS = {
    "U1": "Package_TO_SOT_SMD:SOT-23-6", "U2": "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    "U3": "Package_TO_SOT_SMD:SOT-23-5", "U4": "RF_Module:ESP32-S3-WROOM-1",
    "U5": "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
    "U6": "Package_DFN_QFN:TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm",
    "U12": "Package_TO_SOT_SMD:SOT-23-6",
    "Q1": "Package_TO_SOT_SMD:SOT-23", "Q2": "Package_TO_SOT_SMD:SOT-23", "Q3": "Package_TO_SOT_SMD:SOT-23",
    "D1": "Diode_SMD:D_SOD-123F", "D2": "Diode_SMD:D_SOD-123F", "D3": "Diode_SMD:D_SMA",
    "L1": "Inductor_SMD:L_Sunlord_MWSA0503S",
    "R7": "Resistor_SMD:R_1206_3216Metric", "R8": "Resistor_SMD:R_1206_3216Metric",
    "C1": "Capacitor_SMD:C_1210_3225Metric", "C7": "Capacitor_SMD:C_1210_3225Metric",
    "C10": "Capacitor_SMD:C_1210_3225Metric", "C3": "Capacitor_Tantalum_SMD:CP_EIA-3528-21_Kemet-B",
    "C2": "Capacitor_SMD:C_0805_2012Metric", "C18": "Capacitor_SMD:C_0805_2012Metric",
    "C19": "Capacitor_SMD:C_0805_2012Metric", "C22": "Capacitor_SMD:C_0805_2012Metric", "C20": "Capacitor_SMD:C_0805_2012Metric",
    "J1": "Connector_JST:JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal",
    "J2": "Connector_JST:JST_SH_SM07B-SRSS-TB_1x07-1MP_P1.00mm_Horizontal",
    "J3": "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
    "BT1": PH2, "SP1": PH2,
    "M1": SH2, "M2": SH2, "LED1": SH2, "LED2": SH2, "SW1": SH2, "SW2": SH2,
    "SW3": "Button_Switch_SMD:SW_SPST_B3U-1000P", "SW4": "Button_Switch_SMD:SW_SPST_B3U-1000P",
}
VEST = {f"U{i}" for i in range(7, 12)} | {f"R{i}" for i in range(16, 21)} | {f"C{i}" for i in range(11, 16)}


def assign_footprints():
    for inst in sh.sch.schematicSymbols:
        ref = next(p.value for p in inst.properties if p.key == "Reference")
        if ref.startswith("#"):
            continue
        if ref in VEST:
            inst.onBoard = False  # lives on the vest, not on this PCB
            continue
        fp = FOOTPRINTS.get(ref)
        if fp is None and inst.entryName == "R":
            fp = "Resistor_SMD:R_0603_1608Metric"
        if fp is None and inst.entryName == "C":
            fp = "Capacitor_SMD:C_0603_1608Metric"
        assert fp, f"no footprint for {ref}"
        next(p for p in inst.properties if p.key == "Footprint").value = fp


# three rows, 27.94mm between blocks, ~38mm between rows
block_power(22.86, 38.1)
block_charger(175.26, 38.1)
block_adc(309.88, 38.1)
block_usb(381.0, 38.1)
block_audio(482.6, 38.1)
block_mcu(10.16, 147.32)
block_ir(132.08, 147.32)
block_buttons(248.92, 147.32)
block_ws2812(335.28, 147.32)
block_vibration(462.28, 147.32)
block_weste(22.86, 281.94)

assign_footprints()
out = os.environ.get("OUT_SCH", "waffe_clean.kicad_sch")
sh.save(out)
print("ok ->", out)
