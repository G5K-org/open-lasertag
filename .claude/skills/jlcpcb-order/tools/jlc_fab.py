#!/usr/bin/env python3
"""JLCPCB fabrication + assembly package from a KiCad board (run with system python3, needs pcbnew + kicad-cli).

    python3 jlc_fab.py BOARD.kicad_pcb OUT_DIR [--boards N] [--check]

Creates in OUT_DIR:
  gerber/                Gerber (Protel extensions) + Excellon drill + drill map
  <name>_gerber.zip      upload this as "Gerber file"
  <name>_bom.csv         Comment, Designator, Footprint, LCSC Part #
  <name>_cpl.csv         Designator, Mid X, Mid Y, Layer, Rotation (mm, JLC rotation corrections applied)
--check queries JLCPCB for every LCSC part: stock vs. N boards, basic/extended, unit price.
Footprints need an "LCSC" field; parts without it are listed and left out of BOM/CPL. Parts with an "LCSC Hand"
field instead (hand-soldered by default) go only into <name>_bom_komplett.csv / <name>_cpl_komplett.csv, parts with
an "LCSC Option" field (optional, not assembled by default) only into the *_flash variants.
ESP32-S3-WROOM-1 boards also get *_externe_antenne variants with the WROOM-1U (same footprint).
"""
import csv
import math
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

import pcbnew

LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"

# KiCad footprint orientation -> JLC reel orientation (from matthewlai/JLCKicadTools cpl_rotations_db.csv,
# also used by Bouni/kicad-jlcpcb-tools). First match wins. Always verify in the JLC placement preview.
ROTATIONS = [
    (r"^SOT-223", 180, 0, 0), (r"^SOT-23", -90, 0, 0), (r"^SOT-89", 180, 0, 0), (r"^TSOT-23", 180, 0, 0),
    (r"^SOT-323", -90, 0, 0), (r"^SOT-353", 180, 0, 0), (r"^SOT-363", 180, 0, 0), (r"^LQFP-", 270, 0, 0), (r"^TQFP-", 270, 0, 0),
    (r"^SOP-(?!18_)", 270, 0, 0), (r"^TSSOP-", 270, 0, 0), (r"^SSOP-", 270, 0, 0), (r"^SOIC-", 270, 0, 0), (r"^HSOP-", 270, 0, 0),
    (r"^DFN-", 270, 0, 0), (r"^(.*?_|V)?QFN-(16|20|24|28|40)(-|_|$)", 270, 0, 0),
    (r"^CP_EIA-", 0, 0, 0),  # DB says 180; JLC preview (TAJA106K016RNJ, 15.10.2026): "+" lands on pad 1 only with 0
    (r"^SW_SPST_B3", 90, 0, 0), (r"^JST_PH_S", 180, 0, 0), (r"^JST_GH_SM", 180, 0, 0),
    (r"^JST_SH_SM", 180, 0, 0),
    (r"^SC-74-6", 180, 0, 0), (r"^SOT-143", 180, 0, 0), (r"^ESP32-W", 270, 0, 0),
]


def jlc_part(code):
    req = urllib.request.Request(
        "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList",
        data=json.dumps({"keyword": code, "currentPage": 1, "pageSize": 5}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    for it in json.load(urllib.request.urlopen(req, timeout=30))["data"]["componentPageInfo"]["list"] or []:
        if it["componentCode"] == code:
            return it
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pcb, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    boards = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--boards=")), "5"))
    name = os.path.splitext(os.path.basename(pcb))[0]
    gdir = os.path.join(out, "gerber")
    shutil.rmtree(gdir, ignore_errors=True)
    os.makedirs(gdir)

    run = lambda *c: subprocess.run(["kicad-cli", *c], check=True, capture_output=True, text=True)
    run("pcb", "export", "gerbers", "--layers", LAYERS, "--subtract-soldermask", "--check-zones",
        "--output", gdir + "/", pcb)
    run("pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm",
        "--excellon-zeros-format", "decimal", "--excellon-oval-format", "alternate", "--drill-origin", "absolute",
        "--generate-map", "--map-format", "gerberx2", "--output", gdir + "/", pcb)
    zpath = os.path.join(out, f"{name}_gerber.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gdir)):
            z.write(os.path.join(gdir, f), f)

    board = pcbnew.LoadBoard(pcb)
    parts, missing = [], []   # (ref, footprint, lcsc, value, cpl row, hand, option)
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if fp.IsDNP() or fp.IsExcludedFromBOM():
            continue
        lcsc = fp.GetFieldText("LCSC") if fp.HasField("LCSC") else ""
        hand = fp.GetFieldText("LCSC Hand") if fp.HasField("LCSC Hand") else ""
        opt = fp.GetFieldText("LCSC Option") if fp.HasField("LCSC Option") else ""
        if not lcsc:
            missing.append(ref)
            if not hand and not opt:
                continue
        fpname = fp.GetFPID().GetLibItemName().wx_str()
        rot, dx, dy = 0, 0.0, 0.0
        for pat, r, ox, oy in ROTATIONS:
            if re.search(pat, fpname):
                rot, dx, dy = r, ox, oy
                break
        p = fp.GetPosition()
        bottom = fp.GetLayer() == pcbnew.B_Cu
        row = (ref, round(p.x / 1e6 + dx, 4), round(-p.y / 1e6 + dy, 4), "Bottom" if bottom else "Top",
               round((fp.GetOrientationDegrees() + rot) % 360, 2))
        parts.append((ref, fpname, lcsc or hand or opt, fp.GetValue(), row, bool(hand) and not lcsc, bool(opt) and not lcsc))

    def natkey(r):
        m = re.match(r"([A-Za-z]+)(\d+)", r)
        return (m.group(1), int(m.group(2))) if m else (r, 0)

    # variant for an external antenna: same footprint, ESP32-S3-WROOM-1U (U.FL) instead of the PCB-antenna module
    # (the 1U footprint origin sits 3.15 mm further towards the pins -> CPL centre moves along the module axis)
    ALT = {"C2913202": ("C3013946", "ESP32-S3-WROOM-1U-N16R8")}
    ALT_SHIFT = {"C3013946": 3.15}

    def write(suffix, hand, alt, opt=False):
        groups = {}
        for ref, fpname, lcsc, val, row, is_hand, is_opt in parts:
            if (is_hand and not hand) or (is_opt and not opt):
                continue
            code, v = ALT.get(lcsc, (lcsc, val)) if alt else (lcsc, val)
            g = groups.setdefault((fpname, code), {"refs": [], "vals": [], "rows": []})
            g["refs"].append(ref)
            if v not in g["vals"]:
                g["vals"].append(v)
            if code in ALT_SHIFT and alt:  # shift along the module's own +y (towards the pins), CPL y is inverted
                ref, x, y, layer, rot = row
                a = math.radians(rot)
                row = (ref, round(x - ALT_SHIFT[code] * math.sin(a), 4), round(y - ALT_SHIFT[code] * math.cos(a), 4),
                       layer, rot)
            g["rows"].append(row)
        with open(os.path.join(out, f"{name}_bom{suffix}.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
            for (fpname, code), g in sorted(groups.items(), key=lambda kv: natkey(sorted(kv[1]["refs"], key=natkey)[0])):
                w.writerow([" / ".join(sorted(g["vals"])), ",".join(sorted(g["refs"], key=natkey)), fpname, code])
        with open(os.path.join(out, f"{name}_cpl{suffix}.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
            for row in sorted((r for g in groups.values() for r in g["rows"]), key=lambda r: natkey(r[0])):
                w.writerow(row)
        return groups

    has_alt = any(p[2] in ALT for p in parts)
    has_hand = any(p[5] for p in parts)
    has_opt = any(p[6] for p in parts)
    groups = check = write("", False, False)
    for opt in ([False, True] if has_opt else [False]):
        f = "_flash" if opt else ""
        if opt:
            write(f, False, False, True)
        if has_alt:
            write("_externe_antenne" + f, False, True, opt)
        if has_hand:  # hand-solder parts (field "LCSC Hand") assembled by JLCPCB as well
            c = write("_komplett" + f, True, False, opt)
            if opt:
                check = c
            elif not has_opt:
                check = c
            if has_alt:
                write("_komplett_externe_antenne" + f, True, True, opt)
    bom = os.path.join(out, f"{name}_bom.csv")
    cpl = [r for g in groups.values() for r in g["rows"]]

    print(f"gerber : {zpath} ({len(os.listdir(gdir))} files)")
    print(f"bom    : {bom} ({len(groups)} lines, {sum(len(g['refs']) for g in groups.values())} parts)")
    print(f"cpl    : {len(cpl)} placements")
    hand = sorted((r[0] for r in parts if r[5]), key=natkey)
    if hand:
        print("LCSC Hand (only in *_komplett):", ", ".join(hand))
    opts = sorted((r[0] for r in parts if r[6]), key=natkey)
    if opts:
        print("LCSC Option (only in *_flash):", ", ".join(opts))
    nolcsc = sorted(set(missing) - set(hand) - set(opts), key=natkey)
    if nolcsc:
        print("NO LCSC field (not assembled):", ", ".join(nolcsc))

    if "--check" in sys.argv:
        ext, total, ok = 0, 0.0, True
        print(f"\nJLCPCB stock check for {boards} boards:")
        for (fpname, lcsc), g in sorted(check.items(), key=lambda kv: kv[0][1]):
            refs, val = g["refs"], " / ".join(sorted(g["vals"]))
            need = len(refs) * boards
            it = jlc_part(lcsc)
            if not it:
                print(f"  {lcsc:10s} NOT FOUND  ({val}, {','.join(refs)})"); ok = False
                continue
            basic = it["componentLibraryType"] == "base"
            ext += 0 if basic else 1
            price = (it.get("componentPrices") or [{}])[0].get("productPrice", 0) or 0
            total += price * need
            flag = "OK " if it["stockCount"] >= need else "LOW"
            ok &= it["stockCount"] >= need
            print(f"  {flag} {lcsc:10s} {'basic' if basic else 'ext  '} stock {it['stockCount']:>8} need {need:>4}  "
                  f"${price:<7} {it['componentModelEn'][:28]:28s} {','.join(sorted(refs, key=natkey))}")
        print(f"  -> {ext} extended parts (JLC setup fee per extended part), parts ~${total:.2f} for {boards} boards,"
              f" {'all in stock' if ok else 'STOCK PROBLEMS'}")


if __name__ == "__main__":
    main()
