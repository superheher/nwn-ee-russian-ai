#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_workshop_base.py - assemble the base Steam Workshop item.

  override/ ovr/   dialog.tlk (campaign + SoU + HotU + UI, journal via StrRef) + Cyrillic fonts
  development/     translated resources of the five bonus modules that ship with the game
                   (Chess, Contest of Champions, Dark Ranger's Treasure, Winds of Eremor,
                    To Heir is Human) - they have no haks, so this global layer is the only
                    way to reach them

Two rules make development/ safe here:
  1. module.jrl is NEVER shipped - its resref is "module" for EVERY module in the game,
     so it would replace the journal of the campaign ("ERROR, blank journal entry").
     Cost: the journal of three bonus modules stays English. Nothing else is affected.
  2. no resource whose (resref, restype) also exists in the base game - otherwise it
     silently replaces campaign content (area001.are is "Fort Ilkard", creature001.utc, ...).

Extensions are derived from the real GFF type: the engine resolves a loose file by its
extension, so a UTP written as ".utd" is simply never seen.
"""
import os, sys, shutil, argparse
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import erf

MNT = "/Volumes/twitch/nwn/data"
FONTS = os.path.join(PROOT, "payload", "lang", "en", "data", "ovr")
TLK = os.path.join(PROOT, "build", "dialog.tlk")
TITLE = "AI Russian Text Translation"

# restype -> extension, verified against the GFF signature inside each resource
EXT = {2010: "ncs", 2012: "are", 2023: "git", 2025: "uti", 2027: "utc", 2029: "dlg",
       2030: "itp", 2032: "utt", 2035: "uts", 2040: "ute", 2042: "utd", 2044: "utp",
       2046: "gic", 2051: "utm", 2058: "utw"}
JRL = 2056                                   # never shipped - see rule 1
IFO = 2014

BONUS = [
    ("dlc/chess/chess_ru_scr.mod",        f"{MNT}/mod/Neverwinter Chess.mod"),
    ("dlc/contest/contest_ru_scr.mod",    f"{MNT}/mod/Contest Of Champions 0492.mod"),
    ("dlc/treasure/treasure_ru_scr.mod",  f"{MNT}/mod/The Dark Ranger's Treasure.mod"),
    ("dlc/eremor/eremor_ru_scr.mod",      f"{MNT}/mod/The Winds of Eremor.mod"),
    ("dlc/toheir/toheir_ru_scr.mod",      f"{MNT}/mod/To Heir is Human.mod"),
]
CAMPAIGN = ["Prelude", "Chapter1", "Chapter1E", "Chapter2", "Chapter2E", "Chapter3", "Chapter4",
            "XP1-Chapter 1", "XP1-Chapter 2", "XP1-Interlude",
            "XP2_Chapter1", "XP2_Chapter2", "XP2_Chapter3"]


def P(*a):
    return os.path.join(PROOT, *a)


def base_game_resources():
    """(resref, restype) of everything in the campaign + expansions - the blacklist."""
    out = set()
    for m in CAMPAIGN:
        for r in erf.read_erf(open(f"{MNT}/nwm/{m}.nwm", "rb").read())["resources"]:
            out.add((r["resref"].lower(), r["restype"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=P("build", "workshop2"))
    args = ap.parse_args()

    item = os.path.join(args.out, TITLE)
    dev = os.path.join(item, "development")
    os.makedirs(dev, exist_ok=True)

    for d in ("override", "ovr"):
        dd = os.path.join(item, d)
        os.makedirs(dd, exist_ok=True)
        for fn in os.listdir(FONTS):
            if not fn.startswith("."):
                shutil.copy2(os.path.join(FONTS, fn), os.path.join(dd, fn))
        shutil.copy2(TLK, os.path.join(dd, "dialog.tlk"))

    blacklist = base_game_resources()
    print(f"base game: {len(blacklist)} resources (blacklist)")

    written, seen = Counter(), set()
    skipped = Counter()
    for ru_rel, orig in BONUS:
        ru = P(ru_rel)
        if not os.path.exists(ru):
            ru = P(ru_rel.replace("_ru_scr.", "_ru."))
        om = {(r["resref"].lower(), r["restype"]): r["data"]
              for r in erf.read_erf(open(orig, "rb").read())["resources"]}
        for r in erf.read_erf(open(ru, "rb").read())["resources"]:
            key = (r["resref"].lower(), r["restype"])
            if r["restype"] in (JRL, IFO):
                skipped["journal/ifo"] += 1;  continue
            if r["restype"] not in EXT or om.get(key) == r["data"] or key in seen:
                continue
            if key in blacklist:                       # would replace campaign content
                skipped["clashes with base game"] += 1
                print(f"   skip {key[0]}.{EXT[r['restype']]} - exists in the base game")
                continue
            open(os.path.join(dev, f"{key[0]}.{EXT[r['restype']]}"), "wb").write(r["data"])
            seen.add(key); written[r["restype"]] += 1

    total = sum(written.values())
    sz = sum(os.path.getsize(os.path.join(rt, f)) for rt, _d, fs in os.walk(item) for f in fs)
    print(f"\n{TITLE}")
    print(f"   dialog.tlk + fonts (override/ + ovr/)")
    print(f"   development/: {total} bonus-module resources; skipped {dict(skipped)}")
    print(f"   item total: {sz/1e6:.0f} MB")


if __name__ == "__main__":
    main()
