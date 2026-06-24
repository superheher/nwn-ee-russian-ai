#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_dlc_override.py - collect every TRANSLATED resource of a premium DLC as loose
files for a Workshop item's development/ folder (priority 71M, overrides the loaded
module + its haks). Generalises ddf_override.py to:
  * multiple archives per item (.nwm/.mod AND content hak(s), and packs of several),
  * translated SCRIPTS too: NCS that carry Cyrillic strings (recompiled/byte-patched),
  * excludes base-game resrefs (nw_/x0_/x1_/x2_/x3_) so we never globally override
    the base game's own scripts, and module.ifo (2014).

  make_dlc_override.py --out DIR --pair RU_ARCHIVE ORIG_ARCHIVE [--pair ...]
"""
import os, sys, re, argparse
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import erf, ncs

EXT = {2012: "are", 2023: "git", 2025: "uti", 2027: "utc", 2029: "dlg", 2030: "itp",
       2032: "utt", 2033: "uts", 2035: "utm", 2040: "utw", 2042: "ute", 2044: "utd",
       2051: "gic", 2056: "jrl", 2058: "fac", 2010: "ncs"}
BASE = re.compile(r"^(nw_|x0_|x1_|x2_|x3_|nwnx)", re.I)
CYR = re.compile(rb"[\xc0-\xff]")               # cp1251 Cyrillic byte range


def has_cyrillic_string(data):
    if not ncs.round_trip(data):
        return False
    return any(CYR.search(b) for _o, _l, b in ncs.strings(data))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--pair", nargs=2, action="append", required=True,
                    metavar=("RU", "ORIG"), help="translated archive + its English original")
    args = ap.parse_args()

    if os.path.isdir(args.out):
        import shutil; shutil.rmtree(args.out)
    os.makedirs(args.out)
    per = Counter(); seen = set()
    for ru_path, orig_path in args.pair:
        ru = erf.read_erf(open(ru_path, "rb").read())
        om = {(r["resref"], r["restype"]): r["data"]
              for r in erf.read_erf(open(orig_path, "rb").read())["resources"]}
        for r in ru["resources"]:
            ext = EXT.get(r["restype"])
            rr = r["resref"].lower()
            if not ext or (rr, r["restype"]) in seen:
                continue
            if r["restype"] == 2010:                        # NCS: ship only translated, non-base
                if BASE.match(rr) or not has_cyrillic_string(r["data"]):
                    continue
            else:                                           # GFF: ship if changed vs English
                if om.get((r["resref"], r["restype"])) == r["data"]:
                    continue
            open(os.path.join(args.out, f"{rr}.{ext}"), "wb").write(r["data"])
            seen.add((rr, r["restype"])); per[r["restype"]] += 1

    n = sum(per.values())
    print(f"  {n} resources -> {os.path.relpath(args.out, HERE)}")
    for t, c in sorted(per.items(), key=lambda x: -x[1]):
        print(f"    .{EXT[t]:<4} {c}")


if __name__ == "__main__":
    main()
