"""Umbau des MP5-Gehäuses für die Lasertag-Elektronik.

Alle Maße im Gun-Rahmen (siehe platine_einbau.py): X nach unten, Y nach hinten (Mündung bei kleinem Y),
Z zur linken Außenseite, Teilungsebene der Gehäusehälften Z = 0, mm.

Einbauten:
  - Platinentasche, Dome, USB-C-Öffnung, Anschlag für den Schaft-Steg (platine_einbau.py)
  - Abzug: freigeschnitten, gelagert auf Stahlstift Ø 3, Druckfeder Ø 5 x 10–15, Mikroschalter D2F
  - Schalldämpfer: Innengewinde M24 x 1,5 für die Linsenhülse (Linse Ø 20 x 7), IR-LED 5 mm 21 mm
    hinter der Linse, Ringlicht 12 x WS2812 (Ø 36,8/23,3) in einer Frontkappe mit 12 Fenstern
  - Kabelschacht von der Mündung bis in die Platinentasche, Abzweig in den Magazinschacht
  - Handschutz vorn mit Schalldämpfer links/rechts geteilt, 5 x M3 x 10 mit Einschmelzmuttern; umschließt
    einen Zapfen am hinteren Handschutz, je Hälfte 2 x M3 x 10 in Einschmelzmuttern im Zapfen
  - Lautsprecher Ø 40 im vorderen Handschutz, strahlt nach hinten in eine Schallkammer mit Löchern
    in den Rillen, geschlossene Basskammer davor
  - TSOP 6 vorn an der Rundung unter dem Korn, über dem Schalldämpfer: Aufnahme + gedruckter Einsatz
  - Magazin: Halter für 1 x 18650, abnehmbarer Boden, Öffnung oben für Kabel und JST-PH-Stecker
  - OLED 0,96" 128 x 64 angewinkelt in der Schrägfläche vorn oben am Schaft, Kabelschacht zur Platine
    (Kimme und Korn bleiben)
  - Gehäusehälften mit 6 x M3 x 10 und Einschmelzmuttern verschraubt
  - GX16-7 Buchse für das Sensorkabel der Weste unten vorn am Schaft (15° nach hinten), Kabelschacht zur Platine (J2)
  - Nachladetaste (Taster 6 x 6 mit gedruckter Kappe) links über dem Griff
  - Verstärkung: Stege aus Stahl, je 2 Zuganker M4 vorn (Zapfen bis Gehäuse) und hinten (Gehäuse bis Schaft),
    Zwischenring mit Zentrierbund und Nut
  - Drehgeber EC11 unten im Griff (Welle nach unten), Vibrationsmotor 10 x 20 über dem Griff,
    Kabelschacht Drehgeber -> Motor -> Platine

Kabelschächte sind Ketten gerader Stücke zwischen beliebigen Punkten (path(), auch diagonal).

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

# ---------------------------------------------------------------- Lautsprecher im Handschutz
SPK = (40.0, 6.0)             # Lautsprecher Ø, Einbautiefe (Korb + Magnet + Anschlüsse)
SPK_Y = -56.0                 # Vorderkante Lautsprecher (strahlt nach hinten in die Schallkammer)
SOUND = (36.0, 9.0)           # Schallkammer hinter der Membran: Ø, Länge
BASS = (37.0, 39.0)           # geschlossene Kammer hinter dem Magneten: Ø, Länge (ca. 42 cm³)
HOLES_D = 1.8                 # Schalllöcher in den Rillen zwischen den Rippen
RIB_VALLEY_Z0, RIB_PITCH = 1.5, 4.0   # Rillen im Handschutz (z ab Rückseite)
# Verbindung Handschutz hinten <-> vorn (statt Stiften und Kleber): Zapfen vorn am hinteren Teil (Hals + Kopf mit
# zwei Flächen), die beiden vorderen Hälften umschließen ihn formschlüssig; je Hälfte 2 x M3 x 10 quer in
# Einschmelzmuttern im Kopf. Lautsprecher, Schall- und Basskammer liegen damit ganz im vorderen Teil.
JOINT_Y = -32.0               # Teilung hinten/vorn (vorderer Steg auf 96 mm gekürzt, endet bei -31,6)
NECK = (11.0, 3.0)            # Hals: Radius, Länge
HEAD_J = (16.5, 8.0, 10.5)    # Kopf: Radius, Länge, halber Abstand der Flächen (Z, Auflage der Muttern)
JOINT_CLR = (0.2, 0.1, 0.3)   # Spiel radial, Schulter axial, vor dem Kopf
JOINT_SCREWS = (69.0, 90.0)   # X der Querschrauben (Y = Kopfmitte), je eine von links und rechts
LOBE = (52.5, -3.0)           # Kabelschacht weicht hier oben ins Rohr aus (X, Z), weg vom Spannhebel-Loch

# ---------------------------------------------------------------- TSOP 6 an der Waffe
TSOP_BODY = (6.0, 6.95, 5.6)  # TSOP34838: Breite, Höhe (Beinchen unten), Tiefe mit Linse
TSOP_FRONT = (56.0, -133.4)   # Mitte der Linse (X), Vorderkante Einsatz (Y): vorn an der Rundung unter dem
                              # Korn, über dem Schalldämpfer; Linse nach vorn, Beinchen nach unten
TSOP_LEN = 8.6                # Einsatz in Beinchenrichtung (oben 0,15 Luft zum Steg des Korns)
TSOP_INSERT = (8.6, 6.0, 0.15)   # Einsatz: Breite, Tiefe, Spiel in der Aufnahme

# ---------------------------------------------------------------- Verschraubung der Gehäusehälften
# M3 x 10 (ISO 4762) von rechts, Einschmelzmutter M3 x 5,7 in der linken Hälfte (von der Teilung aus)
SCREWS = [(55.0, 45.0), (60.0, 120.0), (55.0, 190.0), (135.5, 106.0), (110.0, 190.0), (185.0, 207.0)]   # X, Y
INSERT = (4.0, 6.5)           # Loch für die Einschmelzmutter: Ø, Tiefe ab Teilung (links)
SCREW_HOLE = 3.4              # Durchgang rechts
HEAD = (6.2, 5.0)             # Kopfsenkung rechts: Ø, Auflage so weit vor der Teilung (Z = -5)
# Handschutz vorn mit Schalldämpfer: links/rechts geteilt, ebenso verschraubt (X, Y)
HG_SCREWS = [(92.0, -108.0), (61.0, -113.0), (67.0, -165.0), (92.0, -165.0), (67.0, -200.0)]

# ---------------------------------------------------------------- Kabelschächte
TRUNK = (81.0, 2.5)           # Hauptschacht X, Radius (Mündung -> Platinentasche)
DROP_R = 3.0                  # Abzweig in den Magazinschacht

# ---------------------------------------------------------------- Sensorkabel zur Weste
# GX16-7 Einbaubuchse unten vorn am Schaft, leicht schräg nach hinten unten: der Stecker hängt hinter dem Griff,
# frei von der Schießhand. Mutter in einer Sechskanttasche (Schlüsselweite quer zur Teilung), Buchse von außen
# eindrehen. Kabelschacht schräg durch das Gehäuse, gemeinsam mit dem Motorschacht in die VIB-Zone, unter der
# Platine zu J2 (7 Adern).
GX = (111.4, 230.0)           # Mitte der Auflage des Flanschs (X, Y); Unterseite des Schafts bei X = 114,4
GX_TILT = 15.0                # Achse gegen die Senkrechte nach hinten geneigt (Grad)
GX_SPOT = (21.0, 25.0)        # Planfläche für den Flansch: Ø, Freiraum nach außen
GX_HOLE = (16.3, 2.9)         # Durchgang M16 x 1, Wandstärke
GX_NUT = (19.4, 3.4)          # Mutter SW 19 (mit Spiel), Höhe
GX_BODY = (16.6, 12.0)        # Raum für Gewinde und Lötkelche: Ø, Länge
GX_PATH = [(104.0, 186.0, 0), (104.0, 178.0, 0)]   # nach der Buchse bis in den Motorschacht
GX_WIRE = 2.5                 # Radius Kabelschacht (7 x AWG 28)
MOTOR_PATH = [(146.0, 175.0, 0), (104.0, 178.0, 0), (P.X0 + 25.5, P.Y0 + 58.5, 0)]   # Motor -> VIB-Zone
MOTOR_WIRE = 3.0              # Motor, Drehgeber und Weste gemeinsam (13 Adern)

# ---------------------------------------------------------------- Nachladetaste
# Taster 6 x 6 links über dem Griff am oberen Rand des Sicherungshebel-Knopfs (Daumen). Der Taster liegt mit dem Körper
# auf der Teilungsfläche der rechten Hälfte (Beinchen in zwei Schlitzen), die gedruckte Kappe steckt mit Bund im
# Loch der linken Hälfte und ist zwischen Taster und Schulter gefangen. Kabel in einer Nut an der Teilung in die
# Tasche des Abzugsschalters, von dort wie das Abzugskabel zu SW2.
RELOAD = (114.0, 160.0)       # X, Y; Achse Z nach links außen (hinter der Zone für Motor- und Westenstecker)
TACT = (6.0, 3.5, 5.0, 3.5)   # Taster: Kante, Körperhöhe, Höhe bis Stößel, Stößel Ø
TACT_LEGS = (3.25, 2.0, 7.4, 3.5)   # Beinchen bei ±X: Abstand, Schlitzbreite, Schlitzlänge, Tiefe (rechte Hälfte)
CAP_R = (10.0, 1.2, 8.0, 0.8, 0.2)  # Kappe: Bund Ø, Bund Dicke, Schaft Ø, Überstand außen, Spiel
RELOAD_WIRE = [(117.0, 160.0, -0.5), (126.8, 155.0, -0.5)]   # Nut zur Tasche des Abzugsschalters

# ---------------------------------------------------------------- Verstärkung
# Die Stege (Rundstab Ø 10) werden aus Stahl eingesetzt. Dazu je zwei Zuganker M4 (Gewindestange):
# vorn vom Kopf des Zapfens (Mutter gefangen in der Stirnfläche) durch Handschutz hinten, Zwischenring und
# Gehäuse bis in eine Mutternische vor der Platinentasche; hinten von einer Mutternische hinter der
# Platinentasche durch das Gehäuse bis in den Schaft (Mutter gefangen, Schlitz von der Teilung).
# Die Nischen im Gehäuse sind von der Teilungsfläche aus offen (Mutter vor dem Zusammensetzen anziehen).
# Zentrierbunde nach vorn: Bund am Gehäuse in der Nut des Zwischenrings, Bund am Zwischenring in der Nut des
# Handschutzes hinten.
TIE_FRONT = [(78.0, 6.6), (78.0, -6.6)]   # X, Z
TIE_REAR = [(72.0, 9.0), (72.0, -9.0)]
TIE_HOLE = 4.5                # Durchgang M4
TIE_NUT = (7.2, 3.5)          # Mutter M4: Schlüsselweite mit Spiel, Höhe
TIE_FRONT_Y = (-43.0, 87.0)   # Gewindestange vorn: Stirnfläche Zapfenkopf .. Ende in der Nische
TIE_FRONT_NICHE = (5.0, 82.5, 87.5, 11.0)   # halbe Breite X, Y0, Y1, Tiefe ab Teilung
TIE_REAR_Y = (149.5, 242.5)   # Gewindestange hinten: Nische im Gehäuse .. Mutter im Schaft
TIE_REAR_NICHE = (5.0, 149.5, 154.5, 12.5)
COLLAR = (18.0, 21.0, 2.0, 0.15)   # Zentrierbund: Radius innen, außen, Höhe, Spiel

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
    # Motor -> Platine (Feld VIB), oben um die Nachladetaste herum; auch Drehgeber und Weste
    add(path(MOTOR_PATH, MOTOR_WIRE))
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
    # diagonal: aus dem Schaft schräg durch das Gehäuse, am Steg zum Schaft vorbei in die Tasche
    chan = path([back, (68.0, 170.0, 0), (P.X0 + 1.0, 156.0, 0)], 2.25)
    add(chan)
    return cut, pod, pocket + recess + chan, bezel, frame_loc


def tsop():
    """Aufnahme und Einsatz für den TSOP vorn am Handschutz; liefert (Schnitt, Einsatz, Lage)."""
    n = np.array([0, -1.0, 0])                              # Linse nach vorn
    y = np.array([1.0, 0, 0])                               # Beinchen nach unten
    x = np.cross(y, n)
    surf = np.array([TSOP_FRONT[0], TSOP_FRONT[1], 0.0])
    loc = np.column_stack([x, y, n, surf])                 # lokal: x quer, y Beinchen, z nach außen
    w, h, d = TSOP_BODY
    iw, idp, clr = TSOP_INSERT
    ih = TSOP_LEN
    ins = box(-iw / 2, iw / 2, -ih / 2, ih / 2, -idp, 0)
    y0 = -ih / 2 + 0.7                                      # Körper liegt oben an, Beinchen nach +y
    ins = ins - box(-w / 2 - 0.08, w / 2 + 0.08, y0, y0 + h + 0.15, -idp - 1, -1.0)        # Sensor, von hinten
    ins = ins - box(-2.4, 2.4, y0 + 0.9, y0 + h - 1.3, -1.5, 1)                         # Fenster für die Linse
    ins = ins - box(-3.3, 3.3, y0 + h - 0.5, ih / 2 + 1, -idp - 1, -2.4)                # Beinchen
    sock = box(-iw / 2 - clr, iw / 2 + clr, -ih / 2 - clr, ih / 2 + clr, -idp - clr, 4.0)
    sock = sock.transform(loc.tolist())
    # Kabel: unten hinten aus der Aufnahme senkrecht nach unten in den Hauptschacht
    start = surf + y * (ih / 2 - 1.0) - n * (idp - 2.0)
    wire = capsule(start, (TRUNK[0], start[1], 0.0), 1.5)
    return sock + wire, ins.transform(loc.tolist()), loc


def speaker(y_back):
    """Schnitte im Handschutz für den Lautsprecher; liefert (Schnitt, Kabelschacht im Handschutz)."""
    ax, az = AX
    d, depth = SPK
    cut = cyl((ax, SPK_Y - depth, az), (ax, SPK_Y + 0.01, az), d / 2 + 0.2)               # Lautsprecher
    cut = cut + cyl((ax, SPK_Y - depth - BASS[1], az), (ax, SPK_Y - depth + 0.01, az), BASS[0] / 2)   # Basskammer
    cut = cut + cyl((ax, SPK_Y - 0.01, az), (ax, SPK_Y + SOUND[1], az), SOUND[0] / 2)   # Schallkammer
    # Schalllöcher radial in den Rillen über der Schallkammer, unten und seitlich
    for k in range(40):
        z = RIB_VALLEY_Z0 + RIB_PITCH * k
        y = y_back - z
        if not (SPK_Y + 1.5 < y < SPK_Y + SOUND[1] - 1.0):
            continue
        for a in np.radians(np.arange(-110, 110.1, 12.5)):
            dirn = np.array([np.cos(a), 0, np.sin(a)])
            p0 = np.array([ax, y, az]) + dirn * (SOUND[0] / 2 - 1)
            cut = cut + cyl(p0, p0 + dirn * 10, HOLES_D / 2, 16)
    # Kabel des Lautsprechers aus der Basskammer in den Schacht (nach dem Löten abdichten)
    cut = cut + cyl((ax - BASS[0] / 2 + 1, SPK_Y - depth - 4, LOBE[1]), (LOBE[0], SPK_Y - depth - 4, LOBE[1]), 1.25)
    pts = [(TRUNK[0], -156.0, 0), (TRUNK[0], -116.0, 0), (LOBE[0], -103.0, LOBE[1]), (LOBE[0], -44.0, LOBE[1]),
           (TRUNK[0], -40.5, 0), (TRUNK[0], 12.0, 0)]
    trunk = path(pts, TRUNK[1])
    # wo der Schacht neben der Teilungsebene läuft: Nut bis zur Teilungsfläche, Kabel wird eingelegt
    for a, b in zip(pts[1:4], pts[2:5]):
        a0, b0 = (a[0], a[1], 0.0), (b[0], b[1], 0.0)
        trunk = trunk + m3.Manifold.batch_hull([capsule(a, b, TRUNK[1]), capsule(a0, b0, TRUNK[1])])
    return cut, trunk


def joint():
    """Zapfen am hinteren Handschutz, Aussparung in den vorderen Hälften, Querschrauben (Gun-Rahmen)."""
    ax, az = AX
    (rn, ln), (rh, lh, zf), (cr, ca, cf) = NECK, HEAD_J, JOINT_CLR
    y_head = JOINT_Y - ln                                   # Rückseite des Kopfs
    flats = box(-500, 500, -500, 500, -zf, zf)
    spigot = cyl((ax, y_head - 0.01, az), (ax, JOINT_Y + 2.0, az), rn)
    spigot = spigot + (cyl((ax, y_head - lh, az), (ax, y_head, az), rh) ^ flats)
    spigot = spigot - cyl((B.X_FRONT_BAR, JOINT_Y - 0.1, 0), (B.X_FRONT_BAR, JOINT_Y + 3.0, 0), 5.45)   # Stegkanal frei
    pocket = cyl((ax, y_head - 0.01, az), (ax, JOINT_Y + 1.0, az), rn + cr)
    pocket = pocket + (cyl((ax, y_head - lh - cf, az), (ax, y_head + ca, az), rh + cr) ^ box(-500, 500, -500, 500, -zf - cr, zf + cr))
    yc = y_head - lh / 2
    nut, hole = None, None
    for x in JOINT_SCREWS:
        for sgn in (1, -1):
            n = cyl((x, yc, sgn * (zf + 0.01)), (x, yc, sgn * (zf - INSERT[1])), INSERT[0] / 2, 32)
            seat = zf + cr + 3.3                            # Wand unter dem Schraubenkopf
            h = cyl((x, yc, sgn * (zf - 0.5)), (x, yc, sgn * seat), SCREW_HOLE / 2, 32)
            h = h + cyl((x, yc, sgn * seat), (x, yc, sgn * 40.0), HEAD[0] / 2, 32)
            nut = n if nut is None else nut + n
            hole = h if hole is None else hole + h
    return spigot - nut, pocket + hole


def gx_axis():
    """GX16-Buchse: Mitte der Auflage, Achse nach außen, innerer Punkt am Ende des Buchsenraums."""
    t = np.radians(GX_TILT)
    a = np.array([np.cos(t), np.sin(t), 0.0])
    seat = np.array([GX[0], GX[1], 0.0])
    inner = seat - a * (GX_HOLE[1] + GX_NUT[1] + GX_BODY[1])
    return seat, a, inner


def vest():
    """Aufnahme der GX16-Buchse im Schaft und Kabelschacht zur Platine (Gun-Rahmen, beide Hälften)."""
    seat, a, inner = gx_axis()
    cut = cyl(seat, seat + a * GX_SPOT[1], GX_SPOT[0] / 2, 64)
    w = seat - a * GX_HOLE[1]
    cut = cut + cyl(w - a * 0.01, seat + a * 0.01, GX_HOLE[0] / 2, 64)
    n = w - a * GX_NUT[1]
    hexa = m3.CrossSection.circle(GX_NUT[0] / np.sqrt(3), 6).extrude(GX_NUT[1])     # Flächen bei ±Z (SW quer)
    cut = cut + hexa.rotate((0, 0, 30)).transform(frame(a, n, (0, 0, 1)))
    cut = cut + cyl(inner, n + a * 0.01, GX_BODY[0] / 2, 64)
    cut = cut + path([tuple(inner + a * 2.0)] + GX_PATH, GX_WIRE)
    return cut


def reload_button(left):
    """Nachladetaste: (Schnitt links, Schnitt rechts, Nut an der Teilung, Kappe) im Gun-Rahmen."""
    x, y = RELOAD
    e, hb, hp, dp = TACT
    lx, lw, ll, ld = TACT_LEGS
    cd, ct, sd, proud, clr = CAP_R
    tm = to_tm(left)
    rays = [(x + dx, y + dy) for dx in (-sd / 2, 0, sd / 2) for dy in (-sd / 2, 0, sd / 2)]
    loc, _, _ = tm.ray.intersects_location([(px, py, 60.0) for px, py in rays], [(0, 0, -1.0)] * len(rays))
    z_out = loc[:, 2].max()                                 # höchster Punkt der Außenfläche unter der Kappe
    z_cap = hp                                              # Unterseite der Kappe liegt auf dem Stößel
    z_sh = z_cap + ct + 0.05                                # Schulter: Bund liegt in Ruhe an
    cl = box(x - e / 2 - 0.2, x + e / 2 + 0.2, y - e / 2 - 0.2, y + e / 2 + 0.2, -0.01, hb + 0.1)       # Körper
    cl = cl + box(x - lx - lw / 2, x + lx + lw / 2, y - e / 2 - 0.2, y + e / 2 + 0.2, -0.01, 1.2)      # Beinchen
    cl = cl + cyl((x, y, hb), (x, y, z_sh), cd / 2 + clr * 2, 64)                                        # Bund
    cl = cl + cyl((x, y, z_sh - 0.01), (x, y, 60.0), sd / 2 + clr, 64)                                   # Schaft
    cr = None
    for sx in (-1, 1):
        s = box(x + sx * lx - lw / 2, x + sx * lx + lw / 2, y - ll / 2, y + ll / 2, -ld, 0.01)
        cr = s if cr is None else cr + s
    groove = path(RELOAD_WIRE, 1.5)
    cr = cr + capsule((x + lx, y, -1.5), RELOAD_WIRE[0], 1.2)
    cap = cyl((x, y, z_cap), (x, y, z_cap + ct), cd / 2, 64) + cyl((x, y, z_cap + ct - 0.01), (x, y, z_out + proud), sd / 2, 64)
    cap = cap - cyl((x, y, z_cap - 0.01), (x, y, z_cap + 0.6), dp / 2 + 0.2, 32)                         # Stößel
    return cl, cr, groove, cap


def reinforcement():
    """Zuganker, Nischen, gefangene Muttern und Zentrierbunde (Gun-Rahmen).

    Liefert Schnitte für Gehäuse (beide Hälften), Zwischenring, Handschutz hinten und Schaft sowie die Bunde
    für Zwischenring und Handschutz hinten."""
    ax, az = AX
    hexa = m3.CrossSection.circle(TIE_NUT[0] / np.sqrt(3), 6)                  # Flächen bei ±Z

    def nut(x, z, y0, y1, slot=False):
        """Sechskant entlang Y; slot: Flächen bei ±X (von der Teilung eingeschoben)."""
        h = hexa.rotate(30) if slot else hexa
        return h.extrude(y1 - y0).transform(frame((0, 1, 0), (x, y0, z), (1, 0, 0)))

    front = rear = stock = None
    for x, z in TIE_FRONT:
        sz = 1 if z > 0 else -1
        c = cyl((x, TIE_FRONT_Y[0] - 0.01, z), (x, TIE_FRONT_Y[1], z), TIE_HOLE / 2, 32)
        c = c + nut(x, z, TIE_FRONT_Y[0] - 0.01, TIE_FRONT_Y[0] + TIE_NUT[1])
        hx, y0, y1, d = TIE_FRONT_NICHE
        c = c + box(x - hx, x + hx, y0, y1, min(0, sz * d), max(0, sz * d))
        front = c if front is None else front + c
    for x, z in TIE_REAR:
        sz = 1 if z > 0 else -1
        c = cyl((x, TIE_REAR_Y[0], z), (x, TIE_REAR_Y[1], z), TIE_HOLE / 2, 32)
        hx, y0, y1, d = TIE_REAR_NICHE
        c = c + box(x - hx, x + hx, y0, y1, min(0, sz * d), max(0, sz * d))
        yn = TIE_REAR_Y[1] - TIE_NUT[1]
        n = nut(x, z, yn, TIE_REAR_Y[1], slot=True) + box(x - TIE_NUT[0] / 2, x + TIE_NUT[0] / 2, yn, TIE_REAR_Y[1],
                                                 min(0, z), max(0, z))
        rear = c if rear is None else rear + c
        stock = n if stock is None else stock + n
    ri, ro, h, clr = COLLAR

    def annulus(y0, y1, r0, r1):
        return cyl((ax, y0, az), (ax, y1, az), r1, 96) - cyl((ax, y0 - 1, az), (ax, y1 + 1, az), r0, 96)
    # Bunde zeigen nach vorn (-Y): Gehäuse -> Nut im Zwischenring, Zwischenring -> Nut im Handschutz hinten;
    # so liegen Zwischenring (Nut unten) und Handschutz hinten (Nut unten) beim Druck flach auf
    y_ring_back, y_ring_front = B.Y_FRONT, B.Y_FRONT - B.RING_L
    housing_collar = annulus(y_ring_back - h, y_ring_back + 0.01, ri, ro)
    ring_groove = annulus(y_ring_back - h - 0.2, y_ring_back + 0.01, ri - clr, ro + clr)
    ring_collar = annulus(y_ring_front - h, y_ring_front + 0.01, ri, ro)
    hg_groove = annulus(y_ring_front - h - 0.2, y_ring_front + 0.01, ri - clr, ro + clr)
    return dict(front=front, rear=rear, stock=stock, housing_collar=housing_collar, ring_groove=ring_groove,
                ring_collar=ring_collar, hg_groove=hg_groove)


def screws(points=None):
    """Bohrungen für eine Verschraubung über die Teilungsebene Z = 0 (beide Hälften, Gun-Rahmen)."""
    cut = None
    for x, y in (SCREWS if points is None else points):
        c = cyl((x, y, -0.01), (x, y, INSERT[1]), INSERT[0] / 2, 32)                     # links: Einschmelzmutter
        c = c + cyl((x, y, 0.01), (x, y, -HEAD[1]), SCREW_HOLE / 2, 32)                 # rechts: Durchgang
        c = c + cyl((x, y, -HEAD[1]), (x, y, -40.0), HEAD[0] / 2, 32)                   # rechts: Kopfsenkung
        cut = c if cut is None else cut + c
    return cut


def build():
    to_right = np.linalg.inv(np.vstack([P.TO_RIGHT, [0, 0, 0, 1]]))
    L = P.load("obj_1_3")
    R = P.load("obj_3_6").transform(to_right[:3].tolist())
    parts = {name: (src, mat) for name, src, mat, _ in B.parts()}
    hg_mat = B.hg_matrix()
    ring_mat = parts[B.NAMES["zwischenring"]][1]
    mag_mat = parts[B.NAMES["magazin"]][1]

    trig, trig_cut = trigger(L + R)
    add, ocut, sleeve, cap, tip, yw = optics()
    mag = load_gun("obj_6_9", mag_mat)
    mag_body, mag_floor, cell_top, cell_bottom, mag_top, cell_dir, floor_dir = magazine_parts(mag)
    hcut, pod, pod_cut, oled_frame, oled_loc = housing_cuts(tip, yw, mag_top)
    pcut, bosses, pilots, stop = P.pocket_shapes()
    vcut = vest()

    rl, rr, rgroove, rcap = reload_button(L)
    rf = reinforcement()
    halves = []
    for H, side in ((L - rl, P.HALF_L), (R - rr, P.HALF_R)):
        H = H - pcut - trig_cut - hcut - screws() - vcut - rgroove - rf["front"] - rf["rear"] + (rf["housing_collar"] ^ side) + (stop ^ side)
        if side is P.HALF_R:
            H = H + bosses - pilots
        halves.append(H)
    L, R = halves

    hg = load_gun("obj_10_2", hg_mat)
    scut, strunk = speaker(B.Y_FRONT - B.RING_L)
    tcut, tsop_ins, tsop_loc = tsop()
    hg = hg + (add ^ hg.hull()) - ocut - scut - strunk - tcut
    split = box(-500, 500, JOINT_Y, 500, -500, 500)
    spigot, pocket = joint()
    hg_rear = (hg ^ split) + (spigot - strunk) - rf["hg_groove"] - rf["front"]
    hg_front = hg - split - pocket - screws(HG_SCREWS)
    hg_front_l, hg_front_r = hg_front ^ P.HALF_L, hg_front ^ P.HALF_R
    ring = load_gun("obj_5_5", ring_mat) + rf["ring_collar"] - rf["ring_groove"]
    ring = ring - capsule((TRUNK[0], 5.0, 0), (TRUNK[0], 35.0, 0), TRUNK[1]) - rf["front"]
    stocks = {}
    for key, orig, side in (("schaft_links", "obj_4_7", P.HALF_L), ("schaft_rechts", "obj_2_4", P.HALF_R)):
        mat = parts[B.NAMES[key]][1]
        stocks[key] = (load_gun(orig, mat) + (pod ^ side) - pod_cut - vcut - rf["rear"] - rf["stock"], mat)

    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):                               # alter Stand (auch frühere Dateinamen)
        if f.endswith(".stl"):
            os.remove(os.path.join(OUT, f))
    # vollständiger Drucksatz mit eindeutigen Namen (Schlüssel aus baugruppe.NAMES)
    P.save(L, os.path.join(OUT, "gehaeuse_links.stl"))
    P.save(R.transform(P.TO_RIGHT), os.path.join(OUT, "gehaeuse_rechts.stl"))
    save_orig(hg_rear, hg_mat, os.path.join(OUT, "handschutz_hinten.stl"))
    save_orig(ring, ring_mat, os.path.join(OUT, "zwischenring.stl"))
    save_orig(*stocks["schaft_links"], os.path.join(OUT, "schaft_links.stl"))
    save_orig(*stocks["schaft_rechts"], os.path.join(OUT, "schaft_rechts.stl"))
    save_orig(mag_body, mag_mat, os.path.join(OUT, "magazin.stl"))
    P.save(P.steg(), os.path.join(OUT, f"steg_hinten_{P.STEG_L:.0f}mm.stl"))
    # unveränderte Teile, nur umbenannt
    P.save(P.steg(B.STEG_VORN_L), os.path.join(OUT, f"steg_vorn_{B.STEG_VORN_L:.0f}mm.stl"))
    for key, orig in (("korn", "obj_7_1"), ("spannhebel_stift", "obj_11_12"), ("spannhebel_knauf", "obj_9_10")):
        trimesh.load(os.path.join(P.SRC, orig + ".stl")).export(os.path.join(OUT, key + ".stl"))

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
    new_part("nachladetaste", rcap, flat)                                     # Bund unten
    new_part("handschutz_vorn_links", hg_front_l, flat)                       # Teilungsfläche unten
    new_part("handschutz_vorn_rechts", hg_front_r,
             np.array([[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, -1, 0]], float))   # gedreht, Teilungsfläche unten
    front_up = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0]], float)     # -Y -> +z
    front_down = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0]], float)   # -Y -> -z
    new_part("linsenhuelse", sleeve, front_up)
    new_part("frontkappe", cap, front_down)
    loc = np.vstack([oled_loc, [0, 0, 0, 1]])
    new_part("oled_rahmen", oled_frame, np.linalg.inv(loc)[:3])   # Außenseite oben
    tl = np.vstack([tsop_loc, [0, 0, 0, 1]])
    new_part("tsop_einsatz", tsop_ins, np.linalg.inv(tl)[:3])      # Fensterseite oben
    fz = np.asarray(frame(-floor_dir, (0, 0, 0)))          # Boden: Zapfen nach oben
    r = np.linalg.inv(np.vstack([fz, [0, 0, 0, 1]]))
    new_part("magazin_unterteil", mag_floor, r[:3])
    json.dump(lage, open(os.path.join(OUT, "lage.json"), "w"), indent=1)
    info = {"zelle_oben": cell_top.tolist(), "zelle_unten": cell_bottom.tolist(), "led_spitze_y": tip,
            "led_scheibe_y": yw}
    json.dump(info, open(os.path.join(OUT, "info.json"), "w"), indent=1)
    return L, R


if __name__ == "__main__":
    build()
    print("geschrieben nach", os.path.abspath(OUT))
