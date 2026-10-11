#!/usr/bin/env python3
"""Generates waffe_elektronik.kicad_sch for the Lasertag-Waffe (single ESP32-S3 board).
Built programmatically with kiutils + real symbols from the system KiCad libraries.
Signal nets are connected with real routed wires; the handful of global power/ground
rails (see POWER_RAILS below) stay net-label-only, matching normal schematic practice
where wiring every GND/3V3 pin together across the whole sheet would just be noise.
"""
import uuid
import math
from kiutils.schematic import Schematic, SchematicSymbol, SymbolProjectInstance, SymbolProjectPath
from kiutils.symbol import SymbolLib, Symbol, SymbolPin
from kiutils.items.common import Position, Property, Effects, Font
from kiutils.items.schitems import LocalLabel, Text, Connection, Junction
from kiutils.items.syitems import SyRect, SyPolyLine, Fill

GRID = 1.27
SYMDIR = "/usr/share/kicad/symbols"
POWER_RAILS = {"GND", "3V3_MCU", "5V_PERIPH", "BAT_P", "VBUS_NATIVE"}

def snap(v):
    return round(round(v / GRID) * GRID, 2)

def rotate_lib_pin(ox, oy, lib_x, lib_y, angle_deg):
    """World position of a library pin (lib_x,lib_y in library Y-up convention)
    placed at (ox,oy) with the instance rotated by angle_deg (KiCad clockwise,
    sheet Y-down convention)."""
    y_screen = -lib_y  # library Y-up -> sheet Y-down
    th = math.radians(angle_deg or 0)
    wx = lib_x * math.cos(th) - y_screen * math.sin(th)
    wy = lib_x * math.sin(th) + y_screen * math.cos(th)
    return (snap(ox + wx), snap(oy + wy))

_filecache = {}

def get_lib(path):
    if path not in _filecache:
        _filecache[path] = SymbolLib().from_file(path)
    return _filecache[path]

def get_symbol(path, entry):
    lib = get_lib(path)
    return next(s for s in lib.symbols if s.entryName == entry)

def resolve_units(sym, lib_path):
    """Returns the Symbol whose .units actually hold pins (follows 'extends')."""
    if not sym.extends:
        return sym
    lib = get_lib(lib_path)
    bare = sym.extends.split(':')[-1]
    return next(s for s in lib.symbols if s.entryName == bare)


class Sheet:
    def __init__(self):
        self.sch = Schematic.create_new()
        self.registered_libs = set()  # (libraryNickname) already added as libSymbols
        self.ref_counts = {}
        self.netlist = {}  # net name -> list of (x, y) pin positions, for finalize_nets()

    def uid(self):
        return str(uuid.uuid4())

    def ensure_lib(self, path, entry, nickname):
        key = (nickname, entry)
        if key in self.registered_libs:
            return
        sym = get_symbol(path, entry)
        if sym.extends:
            # A schematic's lib_symbols cache must be self-contained: KiCad does
            # not resolve cross-references between two cached entries the way a
            # standalone .kicad_sym library does ('extends' only works there).
            # So flatten: keep the child's own properties, but copy the
            # resolved base's units (graphics + pins) into it, and drop extends.
            base = resolve_units(sym, path)
            # Nested unit names are derived from entryName_unitId_styleId; they
            # must match the PARENT's entryName, not the original base symbol's.
            import copy as _copy
            new_units = []
            for u in base.units:
                u2 = _copy.deepcopy(u)
                u2.entryName = entry
                u2.libraryNickname = None
                new_units.append(u2)
            sym.units = new_units
            sym.extends = None
        sym.libraryNickname = nickname
        sym.inBom = True
        sym.onBoard = True
        self.sch.libSymbols.append(sym)
        self.registered_libs.add(key)

    def mkprop(self, key, value, pos, hide=False, size=1.27):
        return Property(key=key, value=value, position=pos,
                         effects=Effects(font=Font(height=size, width=size), hide=hide))

    def place(self, path, entry, nickname, ref_prefix, value, x, y, unit=1, angle=0,
              footprint="", ref_override=None, hidden_value=False):
        """Places one symbol instance; registers its lib symbol once. Returns (instance, pins_fn)."""
        self.ensure_lib(path, entry, nickname)
        sym = get_symbol(path, entry)
        base = resolve_units(sym, path)
        x, y = snap(x), snap(y)

        if ref_override:
            ref = ref_override
        else:
            n = self.ref_counts.get(ref_prefix, 0) + 1
            self.ref_counts[ref_prefix] = n
            ref = f"{ref_prefix}{n}"

        inst = SchematicSymbol(
            libraryNickname=nickname, entryName=entry, position=Position(X=x, Y=y, angle=angle),
            unit=unit, inBom=True, onBoard=True, uuid=self.uid(),
        )
        inst.properties.append(self.mkprop("Reference", ref, Position(X=x + 5.08, Y=y - 2.54, angle=0)))
        inst.properties.append(self.mkprop("Value", value, Position(X=x + 5.08, Y=y, angle=0), hide=hidden_value))
        inst.properties.append(self.mkprop("Footprint", footprint, Position(X=x, Y=y, angle=0), hide=True))
        inst.pins = {}
        pin_positions = {}
        for u in base.units:
            if u.unitId not in (0, unit):
                continue
            for p in u.pins:
                inst.pins[p.number] = self.uid()
                pin_positions[p.number] = rotate_lib_pin(x, y, p.position.X, p.position.Y, angle)
                pin_positions[p.name] = pin_positions[p.number]
        inst.instances = [SymbolProjectInstance(
            name="waffe_elektronik",
            paths=[SymbolProjectPath(sheetInstancePath="/", reference=ref, unit=unit)])]
        self.sch.schematicSymbols.append(inst)
        return ref, pin_positions

    def net(self, pos, name, ref=None, pin=None):
        """Registers one pin on a net. Power/ground rails get an immediate label at
        every pin (standard practice, see POWER_RAILS); everything else is wired for
        real in finalize_nets() once every pin on the net is known."""
        self.netlist.setdefault(name, []).append((snap(pos[0]), snap(pos[1])))
        if name in POWER_RAILS:
            self.sch.labels.append(LocalLabel(text=name, position=Position(X=pos[0], Y=pos[1], angle=0)))

    def wire(self, p1, p2):
        """Draws a real wire between two pin positions (orthogonal dogleg if needed)."""
        x1, y1 = p1
        x2, y2 = p2
        if x1 == x2 or y1 == y2:
            self.sch.graphicalItems.append(Connection(
                type="wire", points=[Position(X=x1, Y=y1), Position(X=x2, Y=y2)], uuid=self.uid()))
            return
        mx, my = x2, y1
        self.sch.graphicalItems.append(Connection(
            type="wire", points=[Position(X=x1, Y=y1), Position(X=mx, Y=my)], uuid=self.uid()))
        self.sch.graphicalItems.append(Connection(
            type="wire", points=[Position(X=mx, Y=my), Position(X=x2, Y=y2)], uuid=self.uid()))
        self.sch.junctions.append(Junction(position=Position(X=mx, Y=my), uuid=self.uid()))

    def finalize_nets(self, max_span=35.0):
        """Converts every non-power net into real wires: picks the pin that minimizes
        total wire length as a local hub, wires every other pin on the net to it
        directly, and places one label at the hub (for net-name readability/netlist
        export). Power rails were already labeled per-pin in net() and are skipped.

        Two safety checks before a net is actually wired, falling back to the old
        per-pin label behaviour otherwise:
        - its pins must span no more than `max_span` mm (function blocks sit far
          apart on this one-page sheet; a long wire crossing that distance is liable
          to run right along another part's pin column, e.g. the MCU module's
          stacked pins, and short onto it - labels are the standard way to bridge
          that distance anyway)
        - none of its proposed wire segments may pass through a pin that belongs to
          a different net (dense multi-pin ICs like the MAX98357A or the dual-unit
          74AHCT125 place pins close enough together that this does happen)
        """
        all_points = [(p[0], p[1], name) for name, pts in self.netlist.items() for p in pts]

        def blocked(a, b, own_name):
            ax, ay = a
            bx, by = b
            for (px, py, nm) in all_points:
                if nm == own_name:
                    continue
                if ax == bx and px == ax and min(ay, by) <= py <= max(ay, by):
                    return True
                if ay == by and py == ay and min(ax, bx) <= px <= max(ax, bx):
                    return True
            return False

        for name, pts in self.netlist.items():
            if name in POWER_RAILS:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            local = len(pts) >= 2 and (max(xs) - min(xs)) <= max_span and (max(ys) - min(ys)) <= max_span
            wired = False
            if local:
                def total_dist(i):
                    px, py = pts[i]
                    return sum(abs(px - qx) + abs(py - qy) for j, (qx, qy) in enumerate(pts) if j != i)

                hub_idx = min(range(len(pts)), key=total_dist)
                hub = pts[hub_idx]
                others = [p for j, p in enumerate(pts) if j != hub_idx and p != hub]
                segments = []
                for p in others:
                    mid = p if (hub[0] == p[0] or hub[1] == p[1]) else (p[0], hub[1])
                    segments.append((hub, mid))
                    if mid != p:
                        segments.append((mid, p))
                if others and not any(blocked(a, b, name) for a, b in segments):
                    for p in others:
                        self.wire(hub, p)
                    if len(others) > 1:
                        self.sch.junctions.append(Junction(position=Position(X=hub[0], Y=hub[1]), uuid=self.uid()))
                    self.sch.labels.append(LocalLabel(text=name, position=Position(X=hub[0], Y=hub[1], angle=0)))
                    wired = True
            if not wired:
                for p in pts:
                    self.sch.labels.append(LocalLabel(text=name, position=Position(X=p[0], Y=p[1], angle=0)))

    def text(self, s, x, y, size=2.0):
        self.sch.texts.append(Text(text=s, position=Position(X=snap(x), Y=snap(y), angle=0),
                                    effects=Effects(font=Font(height=size, width=size))))

    def box(self, x1, y1, x2, y2):
        self.sch.graphicalItems.append(SyRect(
            start=Position(X=snap(x1), Y=snap(y1)), end=Position(X=snap(x2), Y=snap(y2))))

    def save(self, path):
        self.sch.to_file(path)


# Custom "black box" symbol builder (for modules without a real library part).
# half_width and pin_len are always multiples of GRID so world pin coordinates
# derived as instance_origin + local_offset stay on-grid without extra snapping.
PIN_LEN = 5.08  # 4 * GRID

def _module_layout(left_pins, right_pins, half_width):
    def ys(count):
        top = (count - 1) / 2 * 2.54
        return [snap(top - i * 2.54) for i in range(count)]
    layout = {}
    for (name, num), y in zip(left_pins, ys(len(left_pins))):
        layout[num] = (-half_width - PIN_LEN, y, 0)
        layout[name] = layout[num]
    for (name, num), y in zip(right_pins, ys(len(right_pins))):
        layout[num] = (half_width + PIN_LEN, y, 180)
        layout[name] = layout[num]
    return layout

def _module_half_width(left_pins, right_pins):
    n = max(len(left_pins), len(right_pins), 1)
    return snap(max(10.16, (n) * 1.27))  # enough body width for the ref/value text

def make_module_symbol(nickname, entry, left_pins, right_pins):
    half_width = _module_half_width(left_pins, right_pins)
    n = max(len(left_pins), len(right_pins))
    half_h = snap((n - 1) / 2 * 2.54 + 2.54)
    body = SyRect(start=Position(X=-half_width, Y=half_h), end=Position(X=half_width, Y=-half_h),
                  fill=Fill(type="background"))
    layout = _module_layout(left_pins, right_pins, half_width)

    pins = []
    for (name, num) in left_pins + right_pins:
        lx, ly, angle = layout[num]
        pins.append(SymbolPin(electricalType="passive", position=Position(X=lx, Y=ly, angle=angle),
                               length=PIN_LEN, name=name, number=num))

    unit0 = Symbol(entryName=entry, unitId=0, styleId=1)
    unit1 = Symbol(entryName=entry, unitId=1, styleId=1, graphicItems=[body], pins=pins)
    top = Symbol(libraryNickname=nickname, entryName=entry)
    top.units = [unit0, unit1]
    top.properties = [
        Property(key="Reference", value="U", position=Position(X=0, Y=half_h + 2.54, angle=0),
                  effects=Effects(font=Font(height=1.27, width=1.27))),
        Property(key="Value", value=entry, position=Position(X=0, Y=half_h + 5.08, angle=0),
                  effects=Effects(font=Font(height=1.27, width=1.27))),
        Property(key="Footprint", value="", position=Position(X=0, Y=0, angle=0),
                  effects=Effects(font=Font(height=1.27, width=1.27), hide=True)),
    ]
    top.inBom = True
    top.onBoard = True
    return top


def place_module(sheet: Sheet, nickname, entry, left_pins, right_pins, ref_prefix, x, y):
    key = (nickname, entry)
    if key not in sheet.registered_libs:
        sheet.sch.libSymbols.append(make_module_symbol(nickname, entry, left_pins, right_pins))
        sheet.registered_libs.add(key)

    x, y = snap(x), snap(y)
    n = sheet.ref_counts.get(ref_prefix, 0) + 1
    sheet.ref_counts[ref_prefix] = n
    ref = f"{ref_prefix}{n}"
    inst = SchematicSymbol(libraryNickname=nickname, entryName=entry, position=Position(X=x, Y=y, angle=0),
                            unit=1, inBom=True, onBoard=True, uuid=sheet.uid())
    half_h = snap((max(len(left_pins), len(right_pins)) - 1) / 2 * 2.54 + 2.54)
    inst.properties.append(sheet.mkprop("Reference", ref, Position(X=x, Y=y - half_h - 2.54, angle=0)))
    inst.properties.append(sheet.mkprop("Value", entry, Position(X=x, Y=y - half_h - 5.08, angle=0)))
    inst.properties.append(sheet.mkprop("Footprint", "", Position(X=x, Y=y, angle=0), hide=True))
    inst.pins = {}
    pin_positions = {}

    half_width = _module_half_width(left_pins, right_pins)
    layout = _module_layout(left_pins, right_pins, half_width)
    for (name, num) in left_pins + right_pins:
        lx, ly, _angle = layout[num]
        inst.pins[num] = sheet.uid()
        pin_positions[num] = (snap(x + lx), snap(y - ly))
        pin_positions[name] = pin_positions[num]

    inst.instances = [SymbolProjectInstance(name="waffe_elektronik",
                       paths=[SymbolProjectPath(sheetInstancePath="/", reference=ref, unit=1)])]
    sheet.sch.schematicSymbols.append(inst)
    return ref, pin_positions
