#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ddf_override.py - emit the TRANSLATED module resources as loose override files.

Workshop can't override a DLC's whole .nwm (data/nwm is not an override path),
but NWN's override folder DOES take priority over a module's own resources. So
we extract every resource we changed (translated) from DDF_ru.nwm and write it as
<resref>.<ext> — drop these in the override folder (locally to test, or in a
Workshop item's override/ to ship) and the module loads Russian.

  ddf_override.py [--orig ddf/DDF.nwm] [--ru ddf/DDF_ru.nwm] [--out ddf/override]
"""
import os, sys, argparse
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import erf

# restype -> extension (skip IFO=2014: overriding module.ifo is risky and unneeded)
EXT = {2012:"are",2023:"git",2025:"uti",2027:"utc",2029:"dlg",2030:"itp",2032:"utt",
       2033:"uts",2035:"utm",2040:"utw",2042:"ute",2044:"utd",2051:"gic",2056:"jrl",2058:"fac"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orig", default=os.path.join(HERE, "..", "ddf", "DDF.nwm"))
    ap.add_argument("--ru", default=os.path.join(HERE, "..", "ddf", "DDF_ru.nwm"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "ddf", "override"))
    args = ap.parse_args()

    orig = erf.read_erf(open(args.orig, "rb").read())
    ru = erf.read_erf(open(args.ru, "rb").read())
    om = {(r["resref"], r["restype"]): r["data"] for r in orig["resources"]}

    os.makedirs(args.out, exist_ok=True)
    per = Counter(); n = 0
    for r in ru["resources"]:
        ext = EXT.get(r["restype"])
        if not ext:
            continue
        if om.get((r["resref"], r["restype"])) != r["data"]:   # changed = translated
            fn = f"{r['resref'].lower()}.{ext}"
            open(os.path.join(args.out, fn), "wb").write(r["data"])
            per[r["restype"]] += 1; n += 1
    print(f"wrote {n} translated override resources -> {os.path.relpath(args.out, HERE)}")
    for t, c in sorted(per.items(), key=lambda x: -x[1]):
        print(f"  .{EXT[t]:<4} {c}")


if __name__ == "__main__":
    main()
