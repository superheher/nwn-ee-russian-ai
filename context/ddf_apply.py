#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ddf_apply.py - apply translated strings back into a premium module and repack.

Reads ddf/index.json (id -> every (resref,restype,path) occurrence) and the
workflow output ddf/translated/*.json ({id: ru}); for every embedded LocString
occurrence of a translated string, writes the Russian (CP1251) into the GFF,
repacks the ERF -> ddf/DDF_ru.nwm. Untranslated strings stay English.

  ddf_apply.py [--nwm ddf/DDF.nwm] [--translated ddf/translated]
               [--index ddf/index.json] [--out ddf/DDF_ru.nwm] [--deploy]
  --deploy  also back up + copy the result over the module on the game mount.
"""
import os, sys, json, glob, argparse, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import erf, gff

MOUNT_MOD = "/Volumes/twitch/nwn/data/nwm/Neverwinter Nights - Dark Dreams of Furiae.nwm"


def load_ru(tdir):
    m = {}
    for p in sorted(glob.glob(os.path.join(tdir, "*.json"))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception as ex:
            print(f"  ! skip {p}: {ex}"); continue
        for k, v in d.items():
            if str(k).lstrip("-").isdigit() and isinstance(v, str) and v.strip():
                m[str(k)] = v
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nwm", default=os.path.join(HERE, "..", "ddf", "DDF.nwm"))
    ap.add_argument("--translated", default=os.path.join(HERE, "..", "ddf", "translated"))
    ap.add_argument("--index", default=os.path.join(HERE, "..", "ddf", "index.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "ddf", "DDF_ru.nwm"))
    ap.add_argument("--deploy", action="store_true")
    args = ap.parse_args()

    idx = json.load(open(args.index, encoding="utf-8"))
    id2occ = idx["id2occ"]
    ru = load_ru(args.translated)

    total = len(id2occ)
    have = sum(1 for i in id2occ if i in ru)
    print(f"coverage: {have}/{total} unique strings translated ({100*have/total:.1f}%)")
    missing = [i for i in id2occ if i not in ru]
    if missing:
        print(f"  {len(missing)} untranslated (will stay English), e.g. ids {missing[:5]}")

    # group patches per resource: (resref,restype) -> {path: ru}
    patches = {}
    for i, occs in id2occ.items():
        if i not in ru:
            continue
        for resref, restype, path in occs:
            patches.setdefault((resref, restype), {})[path] = ru[i]

    e = erf.read_erf(open(args.nwm, "rb").read())
    pr = ploc = 0
    for r in e["resources"]:
        pm = patches.get((r["resref"], r["restype"]))
        if not pm:
            continue
        ft, root = gff.read_gff(r["data"])
        n = 0
        for path, loc in gff.iter_locstrings(root):
            if path in pm:
                rub = pm[path].encode("cp1251", "replace")
                loc["subs"] = [(sid, rub) for (sid, _b) in loc["subs"]] or [(0, rub)]
                n += 1
        if n:
            r["data"] = gff.write_gff(ft, root); pr += 1; ploc += n
    out = erf.write_erf(e)
    open(args.out, "wb").write(out)
    # verify it re-reads
    erf.read_erf(open(args.out, "rb").read())
    print(f"patched {ploc} LocStrings across {pr} resources -> {os.path.relpath(args.out, HERE)} "
          f"({os.path.getsize(args.out):,} bytes); re-read OK")

    if args.deploy:
        if not os.path.exists(MOUNT_MOD):
            print(f"  ! mount module not found: {MOUNT_MOD}"); return
        if not os.path.exists(MOUNT_MOD + ".orig"):
            shutil.copy2(MOUNT_MOD, MOUNT_MOD + ".orig"); print("  backed up original -> .orig")
        shutil.copy2(args.out, MOUNT_MOD)
        print(f"  deployed to mount: {MOUNT_MOD}")


if __name__ == "__main__":
    main()
