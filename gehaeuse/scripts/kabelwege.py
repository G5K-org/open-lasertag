"""Prüfung aller Kabelwege in der Baugruppe: jede Leitung vom Stecker auf der Platine bis zum Bauteil.

Aufruf: python kabelwege.py   (mp5_umbau/ muss mit umbau.py erzeugt sein; Platine per kicad-cli)

Jede Leitung ist eine Kette gerader Stücke (Gun-Rahmen, siehe platine_einbau.py). Entlang des Wegs wird ein
Zylinder mit dem Radius des Kabelbündels gegen alle Teile der Baugruppe geprüft (Platine eingeschlossen).
Am Steckermaul (erste 3 mm) wird nicht geprüft, dort sitzt der Stecker selbst. Zwischen den Zonen am
Platinenrand laufen die Kabel im Spalt unter der Platine (Dome, 2,5 mm).
Ausgabe: Länge, Bündelradius, frei/blockiert und die Füllung der gemeinsam genutzten Schächte.
"""
import os
import sys
import tempfile

import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import baugruppe as B  # noqa: E402
import platine_einbau as P  # noqa: E402
import umbau as U  # noqa: E402

AWG28, AWG24 = 0.9, 1.3       # Außendurchmesser Litze mit Isolierung (mm)


def meshes():
    out = {}
    for name, src, mat, _ in B.parts():
        if name.startswith("Steg vorn"):
            m = B.steg_vorn()
        elif name.startswith("Steg hinten"):
            m = B.bar(P.STEG_L, B.X_REAR_BAR, P.STOP[3])
        else:
            m = B.load(src if os.path.isabs(src) else os.path.join(B.SRC, src + ".stl"))
            m.apply_transform(mat)
        out[name] = m
    with tempfile.TemporaryDirectory() as tmp:
        bs, g = B.board(tmp)
        pcb = []
        for node in bs.graph.nodes_geometry:
            t, gn = bs.graph[node]
            geo = bs.geometry[gn].copy()
            geo.apply_transform(g @ t)
            pcb.append(geo)
        out["Platine"] = trimesh.util.concatenate(pcb)
    return out


def routes(M):
    ax = U.AX[0]
    mv = M[B.NAMES["magazin"]].vertices
    mag_top = mv[mv[:, 0] < mv[:, 0].min() + 1.5].mean(0)          # wie magazine_parts()
    sv = np.array([U.OLED_S[0], U.OLED_S[1], 0.0]); sv /= np.linalg.norm(sv)
    nv = np.array([-sv[1], sv[0], 0.0])
    c = np.array([U.OLED_FACE_C[0], U.OLED_FACE_C[1], 0.0]) + sv * U.OLED_SHIFT
    depth = U.OLED_FRAME[0] + U.OLED_GLASS[2] + U.OLED_PCB[2] + U.OLED_BACK
    oled = c - nv * (depth - 1.5) - sv * 9.0                       # wie housing_cuts()
    n = np.array([U.ENC_NORMAL[0], U.ENC_NORMAL[1], 0.0]); n /= np.linalg.norm(n)
    bd, bl, w, zw, h, back = U.ENC
    enc = np.array([U.ENC_FACE[0], U.ENC_FACE[1], 0.0]) - n * (bl + h + back - 1.0)
    zu = -(P.STANDOFF / 2 + P.T_PCB)                                 # Spalt unter der Platine
    trunk_in = [(81.0, 88.5, 0)]                                     # Hauptschacht in der linken Zone
    hg = [(81, 12, 0), (81, -40.5, 0), (U.LOBE[0], -44, U.LOBE[1]), (U.LOBE[0], -103, U.LOBE[1]),
          (81, -116, 0), (81, -156, 0)]
    under = [(100, 91, zu), (100, 90, 0)]                            # unter der Platine in die linke Zone
    xb = U.GX[0] - U.GX_SPOT[1] - U.GX_HOLE[1] - U.GX_NUT[1] - U.GX_BODY[1]
    spk = (ax - U.BASS[0] / 2 + 1, U.SPK_Y - U.SPK[1] - 4, U.LOBE[1])
    # Name: (Adern, Ader-Ø, Weg ab Steckermaul auf der Platine, gemeinsame Schächte)
    return {
        "Akku (BT1)": (2, AWG24, [(81.2, 97.8, 2), (81.2, 89.5, 2)] + trunk_in
                       + [(81, mag_top[1], 0), (88, mag_top[1], 0), tuple(mag_top + [3, 0, 0])], ["Hauptschacht Gehäuse"]),
        "IR-LED (LED1)": (2, AWG28, [(88.8, 96, 2), (88.8, 89.5, 2)] + trunk_in + hg
                          + [(81, -193.4, 0), (ax, -197, 0)], ["Hauptschacht Gehäuse", "Hauptschacht Handschutz"]),
        "TSOP 6 (J6)": (3, AWG28, [(96.6, 96, 2), (96.6, 89.5, 2)] + trunk_in + hg[:5]
                        + [(81, -129.4, 0), (59.3, -129.4, 0)], ["Hauptschacht Gehäuse", "Hauptschacht Handschutz"]),
        "Ringlicht (J1)": (3, AWG28, [(117.1, 105.9, 2), (125, 105.9, 2), (125, 105.9, zu)] + under + trunk_in + hg
                           + [(81, -193.4, 0), (ax + U.WIRE_R, -193.4, 0), (ax + U.WIRE_R, -236, 0)],
                           ["Hauptschacht Gehäuse", "Hauptschacht Handschutz"]),
        "Lautsprecher (SP1)": (2, AWG28, [(117.1, 141.5, 2), (125, 141.5, 2), (125, 141.5, zu)] + under + trunk_in
                               + hg[:4] + [(U.LOBE[0], spk[1], U.LOBE[1]), spk],
                               ["Hauptschacht Gehäuse", "Hauptschacht Handschutz"]),
        "Abzug (SW1)": (2, AWG28, [(103, 96, 2), (103, 89.5, 2), (103, 90, zu), (120, 100, zu), (125, 135, zu),
                                   (125, 145, 0), (128.7, 152, 0)], []),
        "Weste (J2)": (7, AWG28, [(118.9, 127.9, 2), (125, 127.9, 2), (125.5, 144, 0)]
                       + [tuple(p) for p in U.GX_PATH[::-1][1:]] + [(xb + 2, U.GX[1], 0), (xb + 6, U.GX[1], 0)],
                       ["Westenschacht"]),
        "OLED (J4)": (4, AWG28, [(81.5, 149.4, 2), (81.5, 156, 2), (P.X0 + 1, 156, 0), (68, 170, 0), tuple(oled)],
                      ["OLED-Schacht"]),
        "Drehgeber (J5)": (4, AWG28, [(89.5, 149.4, 2), (89.5, 156, 2), (97.5, 156, 0), (100, 152, 0),
                                      (101.5, 151.4, 0), (115, 170, 0), (146, 175, 0), (152, 183, 0), tuple(enc)],
                           ["Motor-/Drehgeberschacht"]),
        "Vibrationsmotor (M1)": (2, AWG28, [(100.8, 143.8, 2), (100.8, 150, 2), (101.5, 151.4, 0), (115, 170, 0),
                                            (146, 175, 0), (149, 170, 0)], ["Motor-/Drehgeberschacht"]),
    }


SHAFTS = {"Hauptschacht Gehäuse": U.TRUNK[1], "Hauptschacht Handschutz": U.TRUNK[1], "Westenschacht": U.GX_WIRE,
          "OLED-Schacht": 2.25, "Motor-/Drehgeberschacht": 2.5}


def bundle_r(n, d):
    return 0.5 * d * np.sqrt(n) * 1.15


def blocked(M, pts, r, step=0.5):
    hits = []
    p0 = np.array(pts[0], float)
    for a, b in zip(pts, pts[1:]):
        a, b = np.array(a, float), np.array(b, float)
        L = np.linalg.norm(b - a)
        if L < 1e-6:
            continue
        d = (b - a) / L
        u = np.cross(d, [0, 0, 1.0])
        if np.linalg.norm(u) < 1e-6:
            u = np.cross(d, [1.0, 0, 0])
        u /= np.linalg.norm(u)
        v = np.cross(d, u)
        cs = [a + (b - a) * t for t in np.linspace(0, 1, int(L / step) + 2)]
        Q = np.array([p + r * (np.cos(q) * u + np.sin(q) * v) for p in cs
                      for q in np.linspace(0, 2 * np.pi, 8, endpoint=False)] + cs)
        for k, m in M.items():
            sel = ((Q >= m.bounds[0] - 0.01) & (Q <= m.bounds[1] + 0.01)).all(1)
            if not sel.any():
                continue
            ins = np.zeros(len(Q), bool)
            ins[sel] = m.contains(Q[sel])
            ins &= np.linalg.norm(Q - p0, axis=1) > 3.0 + r
            if ins.any():
                hits.append((k, np.round(Q[ins].mean(0), 1).tolist()))
    return hits


def main():
    M = meshes()
    fill = {k: 0.0 for k in SHAFTS}
    ok = True
    for name, (n, d, pts, shafts) in routes(M).items():
        r = bundle_r(n, d)
        length = sum(np.linalg.norm(np.subtract(b, a)) for a, b in zip(pts, pts[1:]))
        hits = blocked(M, pts, r)
        ok &= not hits
        print(f"{name:22s} {n} x Ø {d:.1f}  Bündel Ø {2 * r:.1f}  Weg ca. {length:4.0f} mm  "
              + ("frei" if not hits else "BLOCKIERT"))
        for h in hits:
            print("    in", h[0], "bei", h[1])
        for s in shafts:
            fill[s] += n * np.pi * d * d / 4
    print()
    for s, a in fill.items():
        print(f"{s:26s} Ø {2 * SHAFTS[s]:.1f}  Adern {a:5.1f} mm²  Füllung {100 * a / (np.pi * SHAFTS[s] ** 2):3.0f} %")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
