"""Umbau des MP5-Gehäuses für die Lasertag-Elektronik.

Alle Maße im Gun-Rahmen (siehe platine_einbau.py): X nach unten, Y nach hinten (Mündung bei kleinem Y),
Z zur linken Außenseite, Teilungsebene der Gehäusehälften Z = 0, mm.

Einbauten:
  - Platinentasche, Dome, USB-C-Öffnung, Anschlag für den Schaft-Steg (platine_einbau.py)
  - Abzug: freigeschnitten, gelagert auf Stahlstift Ø 3, Druckfeder Ø 5 x 10–15, Mikroschalter D2F
  - Schalldämpfer: Innengewinde M24 x 1,5 für die Linsenhülse (Linse Ø 20 x 7), IR-LED 5 mm 21 mm
    hinter der Linse, Ringlicht 12 x WS2812 (Ø 36,8/23,3) in einer Frontkappe mit 12 Fenstern
  - Kabelschacht von der Mündung bis in die Platinentasche, Abzweig in den Magazinschacht
  - Magazin: Halter für 1 x 18650, abnehmbarer Boden, Öffnung oben für Kabel und JST-PH-Stecker
  - OLED 0,96" 128 x 64 angewinkelt in der Schrägfläche vorn oben am Schaft, Kabelschacht zur Platine
    (Kimme und Korn bleiben)
  - Drehgeber EC11 unten im Griff (Welle nach unten), Vibrationsmotor 10 x 20 über dem Griff,
    Kabelschacht Drehgeber -> Motor -> Platine

Ausgabe nach mp5_umbau/: geänderte Originalteile in ihrer Drucklage, neue Teile in Drucklage,
lage.json mit der Matrix Drucklage -> Gun-Rahmen für die neuen Teile (für baugruppe.py).

Aufruf: python umbau.py   (braucht numpy, trimesh, manifold3d, scipy, shapely)
"""
import json
import os
import sys

import manifold3d as m3
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import platine_einbau as P  # noqa: E402
import baugruppe as B  # noqa: E402

OUT = os.path.join(HERE, "..", "mp5_umbau")
SEG = 48

# ---------------------------------------------------------------- Abzug
PIVOT = (136.0, 129.0)        # Achse (X, Y), Stahlstift Ø 3 entlang Z
PIN_HOLE = 3.05               # in den Gehäusehälften (leichter Presssitz)
PIN_HOLE_TRIGGER = 3.35       # im Abzug (dreht frei)
TRIG_T = 3.3                  # halbe Dicke des Abzugs (wie im Original)
TRIG_CLR = 0.4                # Spiel seitlich und um Nabe/Hebel
HUB_R = 4.2
ARM = (133.6, 137.6, 164.5)   # Hebel nach hinten: X oben, X unten, Y Ende
TRAVEL = 5.0                  # Schwenkwinkel bis Anschlag (Grad); Schalter löst bei ca. 4,5° aus
SPRING = (162.5, 5.6, 120.0)  # Feder: Y-Lage, Bohrung Ø, X oberes Ende (Feder Ø 5 x 10–15, vorgespannt)
SWITCH = (126.15, 131.25, 146.4, 159.4, 3.05)  # D2F-Tasche: X Grundfläche, X Gehäuseunterseite, Y0, Y1, halbe Breite
# D2F-01: Stößel ab Grundfläche frei 6,0, schaltet bei 5,5, Ende 5,25 -> Hebel am Anschlag 0,05 vor Ende

# ---------------------------------------------------------------- Optik im Schalldämpfer
AX = (B.X_AXIS, 0.0)          # Laufachse (X, Z)
Y_MUZZLE = -238.5             # Stirnfläche Schalldämpfer
THREAD = (24.0, 1.5, 0.35)    # M24 x 1,5, radiales Spiel im Innengewinde
SLEEVE_FRONT_R = 11.2         # glatter Teil vorn um die Linse: passt durch das Ringlicht (Ø 23,3)
THREAD_LEN = 26.5             # Innengewinde ab Stirnfläche
LENS = (20.0, 7.0)            # Linse Ø, Dicke
LENS_LED = 21.0               # Linse (Rückseite) -> LED-Spitze
SLEEVE = (18.5, 10.0, 1.5)    # Hülse: Länge, Gewindelänge, Linse zurückgesetzt
LED = (5.0, 8.6, 5.8)         # IR-LED Ø, Länge Kragen -> Spitze, Kragen Ø
RING = (36.8, 23.3, 3.4, 15.0)   # Ringlicht außen, innen, Dicke, Radius der LEDs
CAP = (1.2, 5.0, 18.2)        # Frontkappe: Frontwand, Hülsenlänge über dem Schalldämpfer, Zapfenradius
WIRE_R = 15.5                 # Kanal für die Ringlicht-Kabel (Radius, unten)

# ---------------------------------------------------------------- Kabelschächte
TRUNK = (81.0, 2.5)           # Hauptschacht X, Radius (Mündung -> Platinentasche)
DROP_R = 3.0                  # Abzweig in den Magazinschacht

# ---------------------------------------------------------------- Magazin, Akku
CELL = (18.8, 66.2)           # 18650 mit Spiel
CELL_TOP = (134.0, 58.9)      # oberes Ende der Zelle (X, Y), Mitte in Z
CELL_PHI = 20.5               # Neigung der Zelle gegen X (Grad); Lage aus einer Suche: Zelle frei im Innenraum
SPIGOT = (5.0, 0.45)          # Zapfen des Unterteils: Länge, Spiel; Trennstelle quer zur Zelle, 1 mm unter dem Zapfen
# Der starre 18650 passt nicht durch den gebogenen unteren Teil: das Magazin wird direkt unter der Zelle
# geteilt, die Zelle von dort gerade eingeschoben, der Zapfen des Unterteils stützt sie.

# ---------------------------------------------------------------- OLED, Drehgeber, Motor
# OLED liegt angewinkelt in der Schrägfläche vorn oben am Schaft (Kimme bleibt), in einem Sockel,
# der die Schrägfläche auf Modulbreite verlängert
OLED_FACE_C = (55.15, 248.0)  # Mitte der Schrägfläche (X, Y)
OLED_S = (0.806, 0.592)       # Richtung der Fläche nach unten hinten (X, Y)
OLED_SHIFT = -4.0             # Modulmitte entlang der Fläche gegen die Flächenmitte (nach oben)
OLED_FRAME = (1.6, 1.8)       # Rahmen: Dicke, Überstand über das Modul; Modul wird eingeklebt, Rahmen darüber
OLED_PCB = (27.3, 27.8, 1.6)  # Breite (Z), Höhe (X), Dicke
OLED_GLASS = (26.7, 19.3, 1.4, 4.27)   # Breite, Höhe, Dicke, Abstand Oberkante Platine -> Glas
OLED_WINDOW = (24.0, 14.0)    # sichtbarer Ausschnitt (aktive Fläche 21,7 x 10,9)
OLED_BACK = 3.5               # Platz hinter der Platine (Bauteile, Kabel; Stiftleiste nicht bestücken)
WALL = 1.5

ENC_FACE = (212.9, 204.0)     # Mitte der Buchse auf der schrägen Griffunterseite (X, Y), Achse entlang des Griffs
ENC_NORMAL = (0.867, 0.498)   # nach außen
ENC = (7.3, 7.0, 13.6, 13.0, 6.8, 6.0)   # Buchse Ø, Buchsenlänge, Körper (entlang Fläche, Z), Körperhöhe, Platz hinten

MOTOR = (149.0, 158.0, 179.5, 10.6, 187.5, 12.6)   # X, Y0, Y1 (Körper), Ø, Y Ende Unwucht, Ø Unwucht


def cyl(p0, p1, r, seg=SEG):
    """Zylinder zwischen zwei Punkten."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    h = np.linalg.norm(d)
    c = m3.Manifold.cylinder(h, r, r, seg)
    return c.transform(frame(d / h, p0))


def capsule(p0, p1, r):
    s = m3.Manifold.sphere(r, 24)
    return m3.Manifold.batch_hull([s.translate(tuple(p0)), s.translate(tuple(p1))])


def path(points, r):
    out = None
    for a, b in zip(points, points[1:]):
        c = capsule(a, b, r)
        out = c if out is None else out + c
    return out


def frame(z_dir, origin, x_hint=(1, 0, 0)):
    """3x4-Matrix: lokale z-Achse -> z_dir, Ursprung -> origin."""
    z = np.asarray(z_dir, float)
    z /= np.linalg.norm(z)
    x = np.asarray(x_hint, float)
    if abs(x @ z) > 0.9:
        x = np.array([0, 0, 1.0]) if abs(z[2]) < 0.9 else np.array([0, 1.0, 0])
    x = x - (x @ z) * z
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    m = np.column_stack([x, y, z, origin])
    return m.tolist()


def box(x0, x1, y0, y1, z0, z1):
    return m3.Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def rot_z(man, deg, about):
    return man.translate((-about[0], -about[1], 0)).rotate((0, 0, deg)).translate((about[0], about[1], 0))


def to_man(tm):
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(tm.vertices, np.float32),
                               tri_verts=np.asarray(tm.faces, np.uint32)))


def to_tm(man):
    mm = man.to_mesh()
    return trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts)


def load_gun(name, mat):
    tm = B.load(os.path.join(P.SRC, name + ".stl"))
    tm.apply_transform(mat)
    return to_man(tm)


def save_orig(man, mat, path):
    """Teil aus dem Gun-Rahmen zurück in die Original-Drucklage."""
    tm = to_tm(man)
    tm.apply_transform(np.linalg.inv(mat))
    tm.export(path)


# ---------------------------------------------------------------- Gewinde
def thread_rod(major, pitch, length, offset=0.0):
    """Außengewinde (ISO-Profil, Flankenwinkel 60°) entlang +z, eingängig."""
    h = 0.6134 * pitch
    n = 96
    pts = []
    for k in range(n):
        th = 2 * np.pi * k / n
        u = (k / n) % 1.0
        d = abs(u - 0.5)                    # 0 = Mitte Gewindegrund, 0.5 = Spitze
        if d >= 0.5 - 1 / 16:
            r = major / 2
        elif d <= 1 / 8:
            r = major / 2 - h
        else:
            r = major / 2 - h + h * (d - 1 / 8) / (0.5 - 1 / 16 - 1 / 8)
        r += offset
        pts.append((r * np.cos(th), r * np.sin(th)))
    cs = m3.CrossSection([pts])
    turns = length / pitch
    return cs.extrude(length, n_divisions=int(turns * 36), twist_degrees=-360.0 * turns)


def axis_frame(y_back):
    """Lokal: z nach vorn (-Y), Ursprung auf der Laufachse bei Y = y_back."""
    return [[1, 0, 0, AX[0]], [0, 0, -1, y_back], [0, 1, 0, AX[1]]]


# ---------------------------------------------------------------- Abzug
def trigger(halves):
    """Abzug aus dem Original lösen, Nabe und Hebel ergänzen; liefert (Abzug, Freiraum)."""
    b1 = box(136.3, 140.6, 125.6, 142.4, -TRIG_T - 0.05, TRIG_T + 0.05)
    b2 = box(140.6, 168.0, 118.0, 141.5, -TRIG_T - 0.05, TRIG_T + 0.05)   # nur das Abzugsblatt, nicht der Bügel
    blade = halves ^ (b1 + b2)
    px, py = PIVOT

    def body(t):
        hub = m3.Manifold.cylinder(2 * t, HUB_R, HUB_R, SEG).translate((px, py, -t))
        arm = box(ARM[0], ARM[1], py, ARM[2], -t, t)
        boss = cyl((ARM[0], SPRING[0], 0), (ARM[0] - 1.5, SPRING[0], 0), 1.7)
        return hub + arm + boss

    part = blade + body(TRIG_T) - cyl((px, py, -10), (px, py, 10), PIN_HOLE_TRIGGER / 2)
    swept = None
    shape = blade + body(TRIG_T + TRIG_CLR)
    for deg in np.linspace(-0.5, TRAVEL, 11):
        r = rot_z(shape, deg, PIVOT)
        for dx, dy in ((0, 0), (TRIG_CLR, 0), (-TRIG_CLR, 0), (0, TRIG_CLR), (0, -TRIG_CLR)):
            c = r.translate((dx, dy, 0))
            swept = c if swept is None else swept + c
    cut = swept + b1 + b2
    cut = cut + cyl((px, py, -40), (px, py, 40), PIN_HOLE / 2)
    cut = cut + box(SWITCH[0], SWITCH[1], SWITCH[2], SWITCH[3], -SWITCH[4], SWITCH[4])
    cut = cut + cyl((SPRING[2], SPRING[0], 0), (ARM[0] + 0.5, SPRING[0], 0), SPRING[1] / 2)
    return part, cut


# ---------------------------------------------------------------- Optik, Frontkappe
def optics():
    """(Zusatzmaterial, Schnitt) am Schalldämpfer, Linsenhülse, Frontkappe – alles im Gun-Rahmen."""
    ax, az = AX
    add = None
    # dekorative Seitenbohrungen verschließen (Gewinde und Kabelkanal liegen dort)
    for x, z in ((74.18, 11.97), (84.86, -11.97)):
        c = cyl((x, Y_MUZZLE - 0.2, z), (x, -153.0, z), 3.4)
        add = c if add is None else add + c
    # LED-Sitz: Kragen liegt auf einer Scheibe, Körper in einer Zentrierhülse
    lens_back = Y_MUZZLE + SLEEVE[2] + LENS[1]
    tip = lens_back + LENS_LED
    yw = tip + LED[1]                                      # Vorderseite der Scheibe
    disc = cyl((ax, yw, az), (ax, yw + 3.0, az), 7.2) - cyl((ax, yw - 1, az), (ax, yw + 4, az), 1.75)
    tube = cyl((ax, yw - 4.0, az), (ax, yw + 0.1, az), 4.5) - cyl((ax, yw - 5, az), (ax, yw + 1, az), LED[0] / 2 + 0.1)
    add = add + disc + tube
    cut = thread_rod(THREAD[0], THREAD[1], THREAD_LEN + 0.5, THREAD[2]).transform(axis_frame(Y_MUZZLE + THREAD_LEN))
    # Zapfen für die Frontkappe
    ring = cyl((ax, Y_MUZZLE - 1, az), (ax, Y_MUZZLE + CAP[1], az), 30) - cyl((ax, Y_MUZZLE - 2, az), (ax, Y_MUZZLE + CAP[1] + 1, az), CAP[2])
    cut = cut + ring
    # Kabel Ringlicht: unten im Mantel, hinter dem LED-Sitz in die Bohrung
    yj = yw + 7.0
    cut = cut + capsule((ax + WIRE_R, Y_MUZZLE - 1, az), (ax + WIRE_R, yj, az), 1.5)
    cut = cut + capsule((ax + WIRE_R, yj, az), (TRUNK[0], yj, az), 1.5)
    # Linsenhülse (lokal z nach vorn)
    L, Lt, rec = SLEEVE
    sl = thread_rod(THREAD[0], THREAD[1], Lt)
    sl = sl + m3.Manifold.cylinder(L - Lt, SLEEVE_FRONT_R, SLEEVE_FRONT_R, 96).translate((0, 0, Lt))
    sl = sl - m3.Manifold.cylinder(L + 2, 8.0, 8.0, 64).translate((0, 0, -1))
    sl = sl - m3.Manifold.cylinder(LENS[1] + rec + 1, LENS[0] / 2 + 0.1, LENS[0] / 2 + 0.1, 96).translate((0, 0, L - LENS[1] - rec))
    for a in (0, 90):
        sl = sl - m3.Manifold.cube((THREAD[0] + 2, 2.0, 2.4)).translate((-(THREAD[0] + 2) / 2, -1.0, L - 1.2)).rotate((0, 0, a))
    # Gewindegänge von Hülse und Schalldämpfer in Phase bringen (nur für die Baugruppe)
    sl = sl.rotate((0, 0, -360.0 * ((THREAD_LEN - L) / THREAD[1] % 1.0)))
    sleeve = sl.transform(axis_frame(Y_MUZZLE + L))         # Vorderkante bündig mit der Stirnfläche
    # Frontkappe
    fw, sk, rz = CAP
    ro = 19.3
    y_front = Y_MUZZLE - RING[2] - 2.4 - fw
    cap = cyl((ax, y_front, az), (ax, Y_MUZZLE + sk, az), ro)
    cap = cap - cyl((ax, y_front + fw, az), (ax, Y_MUZZLE + 0.01, az), RING[0] / 2 + 0.25)      # Ringlicht
    cap = cap - cyl((ax, Y_MUZZLE - 0.01, az), (ax, Y_MUZZLE + sk + 1, az), rz + 0.15)          # über den Zapfen
    cap = cap - cyl((ax, y_front - 1, az), (ax, Y_MUZZLE + 1, az), RING[1] / 2 + 0.05)         # Mitte frei
    for k in range(12):
        a = np.radians(15 + 30 * k)
        x, z = ax + RING[3] * np.cos(a), az + RING[3] * np.sin(a)
        cap = cap - cyl((x, y_front - 1, z), (x, y_front + fw + 0.5, z), 2.3)
    return add, cut, sleeve, cap, tip, yw


# ---------------------------------------------------------------- Magazin
def magazine_parts(mag):
    """Akkuhalter, abnehmbarer Boden, Öffnung oben."""
    tm = to_tm(mag)

    def inner_section(origin, normal):
        s = tm.section(normal, origin)
        p, T = s.to_2D()
        rings = []
        for q in p.polygons_full:
            for r in q.interiors:
                rings.append(np.array(r.coords)[:, :2])
        def area(c):
            return np.sum(c[:-1, 0] * c[1:, 1] - c[1:, 0] * c[:-1, 1]) / 2
        big = max(rings, key=lambda c: abs(area(c)))
        if area(big) < 0:                                  # gegen den Uhrzeigersinn
            big = big[::-1]
        return m3.CrossSection([big[:-1].tolist()]), T

    def slab_at(origin, normal, thick, cs, T):
        man = cs.extrude(thick).translate((0, 0, -thick / 2))
        return man.transform(np.asarray(T)[:3].tolist())

    d = np.array([np.cos(np.radians(CELL_PHI)), -np.sin(np.radians(CELL_PHI)), 0.0])   # nach unten
    top = np.array([CELL_TOP[0], CELL_TOP[1], 0.0])
    bottom = top + d * CELL[1]
    ribs = None
    for s, hole in ((-1.2, 4.0), (25.0, CELL[0] / 2 + 0.2), (55.0, CELL[0] / 2 + 0.2)):
        o = top + d * s
        cs, T = inner_section(o, d)
        rib = slab_at(o, d, 2.0, cs.offset(0.3, m3.JoinType.Miter), T)   # in die Wand hinein
        rib = rib - cyl(o - d * 3, o + d * 3, hole)        # oben: Anschlag mit Kabeldurchlass, sonst Führung
        rib = rib ^ to_man(trimesh.convex.convex_hull(tm))
        ribs = rib if ribs is None else ribs + rib
    # Öffnung oben für Kabel und Stecker
    th = np.radians(B.MAG_TILT)
    ag = np.array([-np.cos(th), np.sin(th), 0])
    v = tm.vertices
    topc = v[v[:, 0] < v[:, 0].min() + 1.5].mean(0)
    slot = m3.Manifold.cube((10.0, 8.0, 6.0), True).transform(frame(ag, topc - ag * 2.0, (0, 1, 0)))
    # Unterteil abtrennen: Ebene quer zur Zelle, unter ihrem unteren Ende
    db = d
    o = bottom + d * (SPIGOT[0] + 1.0)
    half = m3.Manifold.cube((200, 200, 200), True).translate((0, 0, 100)).transform(frame(db, o))
    body = mag + ribs - half - slot
    floor = mag ^ half
    cs, T = inner_section(o, db)
    spig = cs.offset(-SPIGOT[1], m3.JoinType.Round).extrude(SPIGOT[0])
    if np.asarray(T)[:3, 2] @ db > 0:                      # Zapfen zeigt in den Magazinkörper (-db)
        spig = spig.translate((0, 0, -SPIGOT[0]))
    spig = spig.transform(np.asarray(T)[:3].tolist())
    floor = floor + spig
    return body, floor, top, bottom, topc, d, db


# ---------------------------------------------------------------- Gehäuse
def housing_cuts(tip, yw, mag_top):
    """Schnitte und Aufsätze in den Gehäusehälften (ohne Platine und Abzug)."""
    cut = None

    def add(c):
        nonlocal cut
        cut = c if cut is None else cut + c

    # Hauptschacht und Abzweig in den Magazinschacht
    add(capsule((TRUNK[0], -158.0, 0), (TRUNK[0], P.Y0 - 4.0, 0), TRUNK[1]))
    add(capsule((TRUNK[0], mag_top[1], 0), (88.0, mag_top[1], 0), DROP_R))
    # Vibrationsmotor
    mx, y0, y1, d, y2, d2 = MOTOR
    add(cyl((mx, y0, 0), (mx, y1 + 0.1, 0), d / 2))
    add(cyl((mx, y1, 0), (mx, y2, 0), d2 / 2))
    # Drehgeber unten im Griff
    n = np.array([ENC_NORMAL[0], ENC_NORMAL[1], 0.0]); n /= np.linalg.norm(n)
    f = np.array([ENC_FACE[0], ENC_FACE[1], 0.0])
    bd, bl, w, zw, h, back = ENC
    add(cyl(f + n * 1.0, f - n * bl, bd / 2))
    ebox = m3.Manifold.cube((w, zw, h + back), True)
    add(ebox.transform(frame(n, f - n * (bl + (h + back) / 2), (-n[1], n[0], 0))))
    e_back = f - n * (bl + h + back - 1.0)
    add(path([e_back, (152.0, 183.0, 0)], 2.5))
    # Motor -> Platine (Feld VIB)
    add(path([(146.0, 175.0, 0), (115.0, 170.0, 0), (P.X0 + 25.5, P.Y0 + 58.5, 0)], 2.5))
    # OLED: Rahmen der Schrägfläche (sv entlang nach unten hinten, nv nach außen, Z quer)
    sv = np.array([OLED_S[0], OLED_S[1], 0.0]); sv /= np.linalg.norm(sv)
    nv = np.array([-sv[1], sv[0], 0.0])
    gw, gh, gt, goff = OLED_GLASS
    pw, ph, pt = OLED_PCB
    c = np.array([OLED_FACE_C[0], OLED_FACE_C[1], 0.0]) + sv * OLED_SHIFT
    rot = np.column_stack([sv, np.array([0, 0, 1.0]), nv])       # lokal x = entlang, y = Z, z = außen

    frame_loc = np.column_stack([rot, c])                         # lokal -> Gun

    def oriented(ax, ay, z0, z1):
        b = m3.Manifold.cube((ax, ay, z1 - z0), True).translate((0, 0, (z0 + z1) / 2))
        return b.transform(frame_loc.tolist())

    def rounded(ax, ay, z0, z1, r):
        """Quader mit rundum abgerundeten Kanten (Radius r), lokal."""
        pts = [(sx * (ax / 2 - r), sy * (ay / 2 - r), z) for sx in (-1, 1) for sy in (-1, 1) for z in (z0 + r, z1 - r)]
        sph = m3.Manifold.sphere(r, 32)
        return m3.Manifold.batch_hull([sph.translate(q) for q in pts])

    mx, my = ph + 0.6, pw + 0.6                                     # Modul mit Spiel
    rx, ry = mx + 2 * OLED_FRAME[1], my + 2 * OLED_FRAME[1]          # Stufe für den Rahmen
    depth = OLED_FRAME[0] + gt + pt + OLED_BACK
    pocket = oriented(mx, my, -depth, -OLED_FRAME[0] + 0.01)
    def rrect(ax, ay, r, z0, z1):
        """Rechteck mit runden Ecken (in der Ebene), flach extrudiert, lokal."""
        cs = m3.CrossSection.square((ax - 2 * r, ay - 2 * r), True).offset(r, m3.JoinType.Round, circular_segments=32)
        return cs.extrude(z1 - z0).translate((0, 0, z0))
    recess = rrect(rx, ry, 2.0, -OLED_FRAME[0], 2.0).transform(frame_loc.tolist())
    pod = rounded(rx + 2 * WALL, ry + 2 * WALL, -depth - WALL - 4.0, 0.0, 2.5).transform(frame_loc.tolist())
    # Rahmen: Platte in der Stufe, Fenster über der aktiven Fläche mit 45°-Fase nach außen
    fr = rrect(rx - 0.3, ry - 0.3, 1.85, -OLED_FRAME[0], 0.0)
    wb = m3.Manifold.cube((OLED_WINDOW[1], OLED_WINDOW[0], 0.01), True).translate((0, 0, -OLED_FRAME[0] - 0.01))
    wt = m3.Manifold.cube((OLED_WINDOW[1] + 2 * OLED_FRAME[0], OLED_WINDOW[0] + 2 * OLED_FRAME[0], 0.01), True).translate((0, 0, 0.01))
    bezel = (fr - m3.Manifold.batch_hull([wb, wt])).transform(frame_loc.tolist())
    back = c - nv * (depth - 1.5) - sv * 9.0                       # hinter dem Modul, oben (Stiftseite)
    chan = path([back, (64.0, back[1] - 4.0, 0), (64.0, 156.0, 0), (P.X0 + 1.0, 156.0, 0)], 2.25)
    add(chan)
    return cut, pod, pocket + recess + chan, bezel, frame_loc


def build():
    to_right = np.linalg.inv(np.vstack([P.TO_RIGHT, [0, 0, 0, 1]]))
    L = P.load("obj_1_3")
    R = P.load("obj_3_6").transform(to_right[:3].tolist())
    parts = {name: (src, mat) for name, src, mat, _ in B.parts()}
    hg_mat = parts["Handschutz + Schalldaempfer (obj_10_2)"][1]
    ring_mat = parts["Zwischenring (obj_5_5)"][1]
    mag_mat = parts["Magazin (obj_6_9)"][1]

    trig, trig_cut = trigger(L + R)
    add, ocut, sleeve, cap, tip, yw = optics()
    mag = load_gun("obj_6_9", mag_mat)
    mag_body, mag_floor, cell_top, cell_bottom, mag_top, cell_dir, floor_dir = magazine_parts(mag)
    hcut, pod, pod_cut, oled_frame, oled_loc = housing_cuts(tip, yw, mag_top)
    pcut, bosses, pilots, stop = P.pocket_shapes()

    halves = []
    for H, side in ((L, P.HALF_L), (R, P.HALF_R)):
        H = H - pcut - trig_cut - hcut + (stop ^ side)
        if side is P.HALF_R:
            H = H + bosses - pilots
        halves.append(H)
    L, R = halves

    hg = load_gun("obj_10_2", hg_mat)
    hg = hg + (add ^ hg.hull()) - ocut - capsule((TRUNK[0], -156.0, 0), (TRUNK[0], 12.0, 0), TRUNK[1])
    ring = load_gun("obj_5_5", ring_mat) - capsule((TRUNK[0], 5.0, 0), (TRUNK[0], 35.0, 0), TRUNK[1])
    stocks = {}
    for key, orig, side in (("Schaft links (obj_4_7)", "obj_4_7", P.HALF_L), ("Schaft rechts (obj_2_4)", "obj_2_4", P.HALF_R)):
        mat = parts[key][1]
        stocks[key] = (load_gun(orig, mat) + (pod ^ side) - pod_cut, mat)

    os.makedirs(OUT, exist_ok=True)
    P.save(L, os.path.join(OUT, "obj_1_3_links.stl"))
    P.save(R.transform(P.TO_RIGHT), os.path.join(OUT, "obj_3_6_rechts.stl"))
    save_orig(hg, hg_mat, os.path.join(OUT, "obj_10_2_handschutz.stl"))
    save_orig(ring, ring_mat, os.path.join(OUT, "obj_5_5_zwischenring.stl"))
    save_orig(*stocks["Schaft links (obj_4_7)"], os.path.join(OUT, "obj_4_7_schaft_links.stl"))
    save_orig(*stocks["Schaft rechts (obj_2_4)"], os.path.join(OUT, "obj_2_4_schaft_rechts.stl"))
    save_orig(mag_body, mag_mat, os.path.join(OUT, "obj_6_9_magazin.stl"))
    P.save(P.steg(), os.path.join(OUT, f"steg_schaft_{P.STEG_L:.0f}mm.stl"))

    # neue Teile in Drucklage; Matrix Drucklage -> Gun-Rahmen
    lage = {}

    def new_part(name, man, print_from_gun):
        g2p = np.vstack([np.asarray(print_from_gun, float), [0, 0, 0, 1]])
        tm = to_tm(man)
        tm.apply_transform(g2p)
        shift = np.eye(4)
        shift[2, 3] = -tm.bounds[0][2]                     # aufs Druckbett
        tm.apply_transform(shift)
        lage[name] = np.linalg.inv(shift @ g2p).tolist()
        tm.export(os.path.join(OUT, name + ".stl"))

    flat = np.eye(4)[:3]                                   # Abzug liegt flach (Z oben)
    new_part("abzug", trig, flat)
    front_up = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0]], float)     # -Y -> +z
    front_down = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0]], float)   # -Y -> -z
    new_part("linsenhuelse", sleeve, front_up)
    new_part("frontkappe", cap, front_down)
    loc = np.vstack([oled_loc, [0, 0, 0, 1]])
    new_part("oled_rahmen", oled_frame, np.linalg.inv(loc)[:3])   # Außenseite oben
    fz = np.asarray(frame(-floor_dir, (0, 0, 0)))          # Boden: Zapfen nach oben
    r = np.linalg.inv(np.vstack([fz, [0, 0, 0, 1]]))
    new_part("magazinboden", mag_floor, r[:3])
    json.dump(lage, open(os.path.join(OUT, "lage.json"), "w"), indent=1)
    info = {"zelle_oben": cell_top.tolist(), "zelle_unten": cell_bottom.tolist(), "led_spitze_y": tip,
            "led_scheibe_y": yw}
    json.dump(info, open(os.path.join(OUT, "info.json"), "w"), indent=1)
    return L, R


if __name__ == "__main__":
    build()
    print("geschrieben nach", os.path.abspath(OUT))
