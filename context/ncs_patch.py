#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ncs_patch.py - apply the audit-worklist translations (dlc/ncs_audit) directly into
the deployed module NCS, by byte-patching string constants (ncs.patch_strings, which
relocates jumps + verifies). Model-independent companion to ncs_worklist.py: it
translates whatever English the bytecode actually contained, regardless of which
function produced it.

Patches each module's <ru>_scr file (what nss_apply produced) so it stays the
canonical artifact, then redeploys. Strings used in comparisons were already
excluded from the worklist, so this cannot change game logic.

  ncs_patch.py [--audit dlc/ncs_audit] [--deploy]
"""
import os, sys, json, glob, shutil, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import erf, ncs, ru_encode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", default=os.path.join(HERE, "..", "dlc", "ncs_audit"))
    ap.add_argument("--deploy", action="store_true")
    args = ap.parse_args()
    cfg = json.load(open(os.path.join(HERE, "nss_modules.json"), encoding="utf-8"))

    id2en = json.load(open(os.path.join(args.audit, "index.json"), encoding="utf-8"))["id2en"]
    ru = {}
    for p in sorted(glob.glob(os.path.join(args.audit, "translated", "*.json"))):
        ru.update(json.load(open(p, encoding="utf-8")))
    repl = {}
    for i, en in id2en.items():
        rv = ru.get(i) or ru.get(str(i))
        if isinstance(rv, str) and rv.strip() and rv != en:
            # NCS strings are length-prefixed (no quote escaping needed); cp1251 round-trips
            repl[ru_encode.en_bytes(en)] = ru_encode.cp1251_bytes(rv)
    print(f"translations: {len(repl)} / {len(id2en)} worklist strings")

    for m, c in cfg.items():
        stem, ext = os.path.splitext(c["ru"])
        scr = os.path.join(HERE, "..", stem + "_scr" + ext)
        if not os.path.exists(scr):
            continue
        e = erf.read_erf(open(scr, "rb").read())
        npatch = nstr = nfail = 0
        for r in e["resources"]:
            if r["restype"] != 2010:
                continue
            new, k = ncs.patch_strings(r["data"], repl)
            if k and new is not None:
                r["data"] = new; npatch += 1; nstr += k
            elif new is None and k == 0 and any(en in r["data"] for en in repl):
                pass                                # unparseable+contains a key: left as-is (rare)
        if not nstr:
            print(f"{m:12} nothing to patch"); continue
        open(scr, "wb").write(erf.write_erf(e))
        erf.read_erf(open(scr, "rb").read())        # verify re-read
        print(f"{m:12} byte-patched {nstr} strings across {npatch} NCS -> {os.path.basename(scr)}")
        if args.deploy and os.path.exists(c["deploy"] + ".orig"):
            shutil.copy2(scr, c["deploy"])
            print(f"             deployed -> mount")


if __name__ == "__main__":
    main()
