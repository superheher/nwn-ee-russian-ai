#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_all_workshop.py - assemble all nine Steam Workshop items (base + 8 premium
DLC) for the Russian AI translation, ready to upload with WorkshopUpload.

Each DLC item:
  development/   translated module + hak resources (GFF + Cyrillic NCS, no base-game
                 resrefs, no .ifo) -> priority 71M, overrides the loaded module/hak
  override/ ovr/ Cyrillic fonts (so a subscriber without the base item still renders)
  thumbnail.png  (downscaled 512x512)
  tags.txt       override
The base item ships the translated dialog.tlk (override/ + ovr/) + fonts, plus the
small free bonus modules in development/.

  build_all_workshop.py [--out build/workshop]
"""
import os, sys, re, json, shutil, subprocess, argparse
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
PROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import erf, ncs

MNT = "/Volumes/twitch/nwn/data"
THUMBS = "/Users/heh/Downloads/nwn_thumbs"
FONTS = os.path.join(PROOT, "payload", "lang", "en", "data", "ovr")
TLK = os.path.join(PROOT, "build", "dialog.tlk")

EXT = {2012: "are", 2023: "git", 2025: "uti", 2027: "utc", 2029: "dlg", 2030: "itp",
       2032: "utt", 2033: "uts", 2035: "utm", 2040: "utw", 2042: "ute", 2044: "utd",
       2051: "gic", 2056: "jrl", 2058: "fac", 2010: "ncs"}
BASE = re.compile(r"^(nw_|x0_|x1_|x2_|x3_|nwnx)", re.I)
CYR = re.compile(rb"[\xc0-\xff]")


def P(*a):
    return os.path.join(PROOT, *a)


# item title -> (thumbnail, [(ru_archive, orig_archive), ...])
DLC = {
    "AI Russian Text Darkness over Daggerford": (
        "Darkness over Daggerford.png",
        [("dlc/daggerford/daggerford_ru_scr.nwm", f"{MNT}/nwm/Neverwinter Nights - Darkness over Daggerford.nwm.orig")]),
    "AI Russian Text Doom of Icewind Dale": (
        "Doom of Icewind Dale.png",
        [("dlc/doid/doid_ru_scr.nwm", f"{MNT}/nwm/Neverwinter Nights - Doom of Icewind Dale.nwm.orig")]),
    "AI Russian Text Tyrants of the Moonsea": (
        "Tyrants of the Moonsea.png",
        [("dlc/moonsea/moonsea_ru_scr.nwm", f"{MNT}/nwm/Neverwinter Nights - Tyrants of the Moonsea.nwm.orig")]),
    "AI Russian Text Dark Dreams of Furiae": (
        "Dark Dreams of Furiae.png",
        [("ddf/DDF_ru_scr.nwm", f"{MNT}/nwm/Neverwinter Nights - Dark Dreams of Furiae.nwm.orig")]),
    "AI Russian Text Pirates of the Sword Coast": (
        "Pirates of the Sword Coast.png",
        [("dlc/pirates/pirates_ru_scr.nwm", f"{MNT}/nwm/Neverwinter Nights - Pirates of the Sword Coast.nwm.orig"),
         ("dlc/pirates_hak/pirates_hak_ru.hak", f"{MNT}/hk/potsc_top.hak.orig")]),
    "AI Russian Text Infinite Dungeons": (
        "Infinite Dungeons.png",
        [("dlc/dungeons/dungeons_ru_scr.nwm", f"{MNT}/nwm/Neverwinter Nights - Infinite Dungeons.nwm.orig"),
         ("dlc/dungeons_hak/dungeons_hak_ru.hak", f"{MNT}/hk/id_resources.hak.orig")]),
    "AI Russian Text Wyvern Crown of Cormyr": (
        "Wyvern Crown of Cormyr.png",
        [("dlc/cormyr/cormyr_ru_scr.nwm", f"{MNT}/nwm/Neverwinter Nights - Wyvern Crown of Cormyr.nwm.orig"),
         ("dlc/cormyr_hak/cormyr_hak_ru.hak", f"{MNT}/hk/wc_top.hak.orig")]),
    "AI Russian Text Heroes of Neverwinter": (              # Kingmaker pack
        "Kingmaker (Heroes of Neverwinter).png",
        [("dlc/kingmaker/kingmaker_ru_scr.mod", f"{MNT}/mod/Kingmaker.mod.orig"),
         ("dlc/kingmaker_hak/kingmaker_hak_ru.hak", f"{MNT}/hk/km_resources.hak.orig"),
         ("dlc/shadowguard/shadowguard_ru_scr.mod", f"{MNT}/mod/ShadowGuard.mod.orig"),
         ("dlc/shadowguard_hak/shadowguard_hak_ru.hak", f"{MNT}/hk/sg_resources.hak.orig"),
         ("dlc/witchswake/witchswake_ru_scr.mod", f"{MNT}/mod/Witch's Wake.mod.orig"),
         ("dlc/witchswake_hak/witchswake_hak_ru.hak", f"{MNT}/hk/ww_resources.hak.orig")]),
}
# free bonus modules -> bundled into the base item's development/
BONUS = [
    ("dlc/chess/chess_ru_scr.mod", f"{MNT}/mod/Neverwinter Chess.mod.orig"),
    ("dlc/contest/contest_ru_scr.mod", f"{MNT}/mod/Contest Of Champions 0492.mod.orig"),
    ("dlc/treasure/treasure_ru_scr.mod", f"{MNT}/mod/The Dark Ranger's Treasure.mod.orig"),
    ("dlc/eremor/eremor_ru_scr.mod", f"{MNT}/mod/The Winds of Eremor.mod.orig"),
    ("dlc/toheir/toheir_ru_scr.mod", f"{MNT}/mod/To Heir is Human.mod.orig"),
]
BASE_THUMB = "Neverwinter Nights EE (base).png"


def extract_into(dev, pairs):
    """Write translated loose resources from each (ru, orig) archive pair into dev/."""
    per, seen = Counter(), set()
    for ru_path, orig_path in pairs:
        rp = P(ru_path)
        if not os.path.exists(rp):                  # no script pass -> use the GFF-only _ru
            rp = P(ru_path.replace("_ru_scr.", "_ru."))
        ru = erf.read_erf(open(rp, "rb").read())
        om = {(r["resref"], r["restype"]): r["data"]
              for r in erf.read_erf(open(orig_path, "rb").read())["resources"]}
        for r in ru["resources"]:
            ext = EXT.get(r["restype"]); rr = r["resref"].lower()
            if not ext or (rr, r["restype"]) in seen:
                continue
            if r["restype"] == 2010:
                if BASE.match(rr) or not ncs.round_trip(r["data"]) \
                        or not any(CYR.search(b) for _o, _l, b in ncs.strings(r["data"])):
                    continue
            elif om.get((r["resref"], r["restype"])) == r["data"]:
                continue
            open(os.path.join(dev, f"{rr}.{ext}"), "wb").write(r["data"])
            seen.add((rr, r["restype"])); per[r["restype"]] += 1
    return per


def copy_fonts(item):
    for d in ("override", "ovr"):
        dd = os.path.join(item, d); os.makedirs(dd, exist_ok=True)
        for f in os.listdir(FONTS):
            if not f.startswith("."):
                shutil.copy2(os.path.join(FONTS, f), os.path.join(dd, f))


def thumb(item, name):
    src = os.path.join(THUMBS, name)
    if os.path.exists(src):
        subprocess.run(["sips", "-Z", "512", "-s", "format", "png", src,
                        "--out", os.path.join(item, "thumbnail.png")],
                       check=True, capture_output=True)


def tags(item):
    open(os.path.join(item, "tags.txt"), "w").write("override\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(PROOT, "build", "workshop"))
    args = ap.parse_args()
    if os.path.isdir(args.out):
        shutil.rmtree(args.out)
    os.makedirs(args.out)

    for title, (thumb_name, pairs) in DLC.items():
        item = os.path.join(args.out, title)
        dev = os.path.join(item, "development"); os.makedirs(dev)
        per = extract_into(dev, pairs)
        copy_fonts(item); thumb(item, thumb_name); tags(item)
        sz = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(item) for f in fs)
        print(f"{title}\n   development/: {sum(per.values())} res ({dict(per)}); item {sz/1e6:.1f} MB")

    # base item: dialog.tlk (override/+ovr/) + fonts + bonus modules in development/
    base = os.path.join(args.out, "AI Russian Text Translation")
    copy_fonts(base)
    for d in ("override", "ovr"):
        shutil.copy2(TLK, os.path.join(base, d, "dialog.tlk"))
    dev = os.path.join(base, "development"); os.makedirs(dev)
    per = extract_into(dev, BONUS)
    thumb(base, BASE_THUMB); tags(base)
    sz = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(base) for f in fs)
    print(f"AI Russian Text Translation\n   dialog.tlk + fonts + "
          f"development/ {sum(per.values())} bonus res; item {sz/1e6:.1f} MB")
    print(f"\nAll items in {args.out}\n  upload each in-game: WorkshopUpload <raw path, no quotes>")


if __name__ == "__main__":
    main()
