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
POWER_LIB = f"{SYMDIR}/power.kicad_sym"
POWER_RAILS = {"GND", "3V3_MCU", "5V_PERIPH", "BAT_P", "VBUS_NATIVE"}

def snap(v):
    return round(round(v / GRID) * GRID, 2)

def rotate_lib_pin(ox, oy, lib_x, lib_y, angle_deg):
    """World position of a library pin (lib_x,lib_y in library Y-up convention)
    placed at (ox,oy) with the instance rotated by angle_deg. KiCad rotates
    counter-clockwise as seen on screen (verified against a netlist export: an
    LED at 90 deg ends up anode-on-top) - getting this backwards silently swaps
    the pins of any polarized part placed at 90/270."""
    sx, sy = lib_x, -lib_y  # library Y-up -> sheet Y-down
    th = math.radians(angle_deg or 0)
    wx = sx * math.cos(th) + sy * math.sin(th)
    wy = -sx * math.sin(th) + sy * math.cos(th)
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
        # The layout is taller than it is wide (~280 x 405mm) - way past A4
        # (297x210mm landscape), which let content spill past the page border
        # and overlap the title block. A2 portrait (420 x 594mm) comfortably
        # contains it with margin.
        self.sch.paper.paperSize = "A2"
        self.sch.paper.portrait = True
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
              footprint="", ref_override=None, hidden_value=False, hidden_ref=False):
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
        # Offset the reference/value text perpendicular to the pin axis (and rotate
        # that offset along with the symbol), so it lands above/beside the body
        # clear of both the symbol's own pins and whatever net label ends up at a
        # pin tip - instead of out along the pin axis, where it used to collide
        # with exactly those pin-tip labels.
        th = math.radians(angle or 0)
        def _rot(dx, dy):
            return (snap(x + dx * math.cos(th) - dy * math.sin(th)),
                    snap(y + dx * math.sin(th) + dy * math.cos(th)))
        rx, ry = _rot(0, -6.35)
        vx, vy = _rot(0, -8.89)
        inst.properties.append(self.mkprop("Reference", ref, Position(X=rx, Y=ry, angle=0), hide=hidden_ref))
        inst.properties.append(self.mkprop("Value", value, Position(X=vx, Y=vy, angle=0), hide=hidden_value))
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
        """Registers one pin on a net. Labels (power/ground rails at every pin,
        everything else at a wiring hub) are placed later in finalize_nets(), once
        every pin on every net is known and label placement can dodge pins/wires
        that are registered after this particular call."""
        self.netlist.setdefault(name, []).append((snap(pos[0]), snap(pos[1])))

    def _draw_segment(self, a, b):
        self.sch.graphicalItems.append(Connection(
            type="wire", points=[Position(X=a[0], Y=a[1]), Position(X=b[0], Y=b[1])], uuid=self.uid()))

    def finalize_nets(self):
        """Converts every non-power net into real wires: picks the pin that minimizes
        total wire length as a local hub, wires every other pin on the net to it,
        and places one label at the hub (for net-name readability/netlist export).
        Power rails were already labeled per-pin in net() and are skipped.

        For each hub->pin connection that isn't already axis-aligned, both possible
        L-bend directions (horizontal-first vs. vertical-first) are tried, and
        whichever one doesn't run through a pin/wire-point belonging to a different
        net is used. This matters a lot for the long runs out to the MCU module:
        its pins are stacked in one column, so a bend that happens to put its
        straight leg right along that column's X (or any other part's pin row)
        would silently short onto every other pin in between - that's exactly what
        happened on the first attempt. If neither direction is clear for every pin
        on the net, the whole net falls back to the old per-pin label behaviour
        rather than wiring only part of it."""
        occupied = [(p[0], p[1], name) for name, pts in self.netlist.items() for p in pts]
        drawn_segments = []  # (((ax,ay),(bx,by)), net_name) for every wire placed so far

        def point_on_seg(p, seg):
            (ax, ay), (bx, by) = seg
            px, py = p
            if ax == bx:
                return px == ax and min(ay, by) <= py <= max(ay, by)
            if ay == by:
                return py == ay and min(ax, bx) <= px <= max(ax, bx)
            return False

        def blocked(a, b, own_name, ignore_own=True, exclude=None):
            """A point/segment collision only matters away from `exclude` (normally
            the segment's own starting pin, which legitimately has other wires
            already touching it - that's just a junction, not a short)."""
            for (px, py, nm) in occupied:
                if ignore_own and nm == own_name:
                    continue
                if exclude is not None and (px, py) == exclude:
                    continue
                if point_on_seg((px, py), (a, b)):
                    return True
            for seg, nm in drawn_segments:
                if ignore_own and nm == own_name:
                    continue
                for p in (a, b):
                    if p != exclude and point_on_seg(p, seg):
                        return True
                for p in seg:
                    if p != exclude and point_on_seg(p, (a, b)):
                        return True
            return False

        def commit_segment(a, b, name):
            self._draw_segment(a, b)
            drawn_segments.append(((a, b), name))

        def route(hub, p, name):
            if hub[0] == p[0] or hub[1] == p[1]:
                return [(hub, p)]
            for mid in ((p[0], hub[1]), (hub[0], p[1])):
                segs = [(hub, mid), (mid, p)]
                if not any(blocked(a, b, name) for a, b in segs):
                    return segs
            return None

        def place_label(p, name, stub=3.81):
            """Labels placed exactly on a pin tend to land right on top of that pin's
            own number text (this is what made the MCU module's pin column
            unreadable). Nudge the label out along a short stub wire instead,
            trying a few directions until one doesn't run through a foreign pin
            or an already-placed wire belonging to a different net. Vertical
            directions are tried first: most parts here are 2-pin passives laid
            out horizontally, so their own pin-name text runs left/right from the
            tip - moving the label up/down clears that text too, not just other
            parts' pins, which a pure geometric check can't see."""
            for dx, dy in ((0, -stub), (0, stub), (-stub, 0), (stub, 0)):
                q = (p[0] + dx, p[1] + dy)
                if not blocked(p, q, name, ignore_own=False, exclude=p):
                    commit_segment(p, q, name)
                    occupied.append((q[0], q[1], name))
                    self.sch.labels.append(LocalLabel(text=name, position=Position(X=q[0], Y=q[1], angle=0)))
                    return
            self.sch.labels.append(LocalLabel(text=name, position=Position(X=p[0], Y=p[1], angle=0)))

        def place_power(p, name, stub=3.81):
            """Power/ground rails get a real power symbol (the little ground-tick
            or arrow glyph) instead of a text label - that's the normal schematic
            convention and reads a lot better than bare text at every pin. GND
            symbols hang below their connection point, rail symbols (reusing the
            generic VCC arrow, renamed via its Value) sit above - so that's the
            preferred stub direction, with the same foreign-pin/wire collision
            check as place_label() as a fallback."""
            is_gnd = (name == "GND")
            preferred = (0, stub) if is_gnd else (0, -stub)
            for dx, dy in (preferred, (-preferred[0], -preferred[1]), (stub, 0), (-stub, 0)):
                q = (p[0] + dx, p[1] + dy)
                if not blocked(p, q, name, ignore_own=False, exclude=p):
                    break
            else:
                q = p
            if q != p:
                commit_segment(p, q, name)
                occupied.append((q[0], q[1], name))
            self.place(POWER_LIB, "GND" if is_gnd else "VCC", "power", "#PWR", name,
                       q[0], q[1], hidden_value=is_gnd, hidden_ref=True)

        def cluster_points(pts, max_gap=15.0):
            """Groups points into local clusters (union-find by proximity): any two
            points within max_gap mm on both axes link up transitively. Used to
            give each local group of power/ground pins one shared symbol instead
            of one per pin - the "rail" look real schematics use, instead of a
            ground arrow stapled to every single pin."""
            n = len(pts)
            parent = list(range(n))

            def find(i):
                while parent[i] != i:
                    parent[i] = parent[parent[i]]
                    i = parent[i]
                return i

            for i in range(n):
                for j in range(i + 1, n):
                    if abs(pts[i][0] - pts[j][0]) <= max_gap and abs(pts[i][1] - pts[j][1]) <= max_gap:
                        ri, rj = find(i), find(j)
                        if ri != rj:
                            parent[ri] = rj
            groups = {}
            for i in range(n):
                groups.setdefault(find(i), []).append(pts[i])
            return list(groups.values())

        def wire_cluster(cluster, name):
            """Wires every point in a local cluster to one shared hub and gives
            that hub a single power symbol. Returns False (caller should fall back
            to one place_power() per point) if any connection within the cluster
            can't be routed cleanly."""
            if len(cluster) == 1:
                place_power(cluster[0], name)
                return True

            def total_dist(i):
                px, py = cluster[i]
                return sum(abs(px - qx) + abs(py - qy) for j, (qx, qy) in enumerate(cluster) if j != i)

            hub_idx = min(range(len(cluster)), key=total_dist)
            hub = cluster[hub_idx]
            others = [p for j, p in enumerate(cluster) if j != hub_idx]

            routes = []
            for p in others:
                segs = route(hub, p, name)
                if segs is None:
                    return False
                routes.append(segs)
            for segs in routes:
                for (a, b) in segs:
                    commit_segment(a, b, name)
                if len(segs) == 2:
                    mid = segs[0][1]
                    self.sch.junctions.append(Junction(position=Position(X=mid[0], Y=mid[1]), uuid=self.uid()))
                    occupied.append((mid[0], mid[1], name))
            if len(others) > 1:
                self.sch.junctions.append(Junction(position=Position(X=hub[0], Y=hub[1]), uuid=self.uid()))
            place_power(hub, name)
            return True

        # Pass 1: wire every net that can be wired. Labels are deferred to pass 2 -
        # otherwise a net processed early (like HIT_VIB, reached via the MCU loop)
        # could place its label before a later net (like HIT_VIB_FET, only reached
        # once the vibration-motor section runs) has drawn its own wires, so the
        # collision check below has nothing yet to avoid and the two merge.
        wired = {}  # name -> hub, for nets that got real wires
        for name, pts in self.netlist.items():
            if name in POWER_RAILS or len(pts) < 2:
                continue

            def total_dist(i):
                px, py = pts[i]
                return sum(abs(px - qx) + abs(py - qy) for j, (qx, qy) in enumerate(pts) if j != i)

            hub_idx = min(range(len(pts)), key=total_dist)
            hub = pts[hub_idx]
            others = [p for j, p in enumerate(pts) if j != hub_idx and p != hub]

            routes = []
            for p in others:
                segs = route(hub, p, name)
                if segs is None:
                    routes = None
                    break
                routes.append(segs)

            if routes is not None and others:
                for segs in routes:
                    for (a, b) in segs:
                        commit_segment(a, b, name)
                    if len(segs) == 2:
                        mid = segs[0][1]
                        self.sch.junctions.append(Junction(position=Position(X=mid[0], Y=mid[1]), uuid=self.uid()))
                        occupied.append((mid[0], mid[1], name))
                if len(others) > 1:
                    self.sch.junctions.append(Junction(position=Position(X=hub[0], Y=hub[1]), uuid=self.uid()))
                wired[name] = hub

        # Pass 2: one label per wired net (at its hub), per-pin labels for every
        # net that couldn't be wired - now with every net's wires already drawn.
        for name, pts in self.netlist.items():
            if name in POWER_RAILS:
                for cluster in cluster_points(pts):
                    if not wire_cluster(cluster, name):
                        for p in cluster:
                            place_power(p, name)
            elif name in wired:
                place_label(wired[name], name)
            else:
                for p in pts:
                    place_label(p, name)

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
# PIN_PITCH is wider than the KiCad-standard 2.54mm: with ~18 pins on one side
# and long net-name pin names, 2.54mm pitch puts each pin's number/name text
# close enough to its neighbours to visually collide. 3.81mm (3 * GRID) gives
# that text room to breathe while staying on-grid.
PIN_LEN = 5.08  # 4 * GRID
PIN_PITCH = 3.81  # 3 * GRID
PIN_TEXT = Effects(font=Font(height=1.27, width=1.27))

def _module_layout(left_pins, right_pins, half_width):
    def ys(count):
        top = (count - 1) / 2 * PIN_PITCH
        return [snap(top - i * PIN_PITCH) for i in range(count)]
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
    half_h = snap((n - 1) / 2 * PIN_PITCH + PIN_PITCH)
    body = SyRect(start=Position(X=-half_width, Y=half_h), end=Position(X=half_width, Y=-half_h),
                  fill=Fill(type="background"))
    layout = _module_layout(left_pins, right_pins, half_width)

    pins = []
    for (name, num) in left_pins + right_pins:
        lx, ly, angle = layout[num]
        pins.append(SymbolPin(electricalType="passive", position=Position(X=lx, Y=ly, angle=angle),
                               length=PIN_LEN, name=name, number=num,
                               nameEffects=PIN_TEXT, numberEffects=PIN_TEXT))

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
    half_h = snap((max(len(left_pins), len(right_pins)) - 1) / 2 * PIN_PITCH + PIN_PITCH)
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
