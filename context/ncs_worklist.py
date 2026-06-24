#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ncs_worklist.py - build a translation worklist DIRECTLY from the deployed NCS
bytecode (model-independent: no assumption about which functions are "display").

Collects every English string constant that looks like player-readable prose
(>=4 words, narrative), EXCLUDING any value ever used as an EQUAL/NEQUAL operand
in ANY module (translating those would break logic). Dedups globally (the patch
in ncs_patch.py is by string value). Writes wf-shaped batches + index.

  ncs_worklist.py [--out dlc/ncs_audit] [--batch 80]
Then translate with the nss Workflow (inDir=<out>/batches, outDir=<out>/translated),
then apply with ncs_patch.py.
"""
import os, sys, re, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import erf, ncs
import importlib.util
_spec = importlib.util.spec_from_file_location("ae", os.path.join(HERE, "audit_english.py"))
ae = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ae)


def translatable(s):
    """Good-recall player-prose filter: a real phrase, >=4 words, >=2 narrative
    words, not a trailing-label var dump."""
    if not ae.looks_player_text(s):
        return False
    s2 = s.strip()
    if re.search(r"(=|:)\s*$", s2):
        return False
    if len(ae.WORD.findall(s2)) < 4:
        return False
    return len(ae._NARRATIVE.findall(s2)) >= 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "..", "dlc", "ncs_audit"))
    ap.add_argument("--batch", type=int, default=80)
    args = ap.parse_args()
    cfg = json.load(open(os.path.join(HERE, "nss_modules.json"), encoding="utf-8"))

    compared = set()                                # global: never translate these
    cand = {}                                       # english(str) -> set(modules)
    for m, c in cfg.items():
        if not os.path.exists(c["deploy"]):
            continue
        e = erf.read_erf(open(c["deploy"], "rb").read())
        for r in e["resources"]:
            if r["restype"] != 2010 or not ncs.round_trip(r["data"]):
                continue
            compared |= ncs.compared_strings(r["data"])
            for _o, _l, b in ncs.strings(r["data"]):
                s = b.decode("cp1251", "replace")
                if translatable(s):
                    cand.setdefault(s, set()).add(m)

    work = sorted(s for s in cand if s.encode("cp1251", "replace") not in compared)
    excluded = len(cand) - len(work)
    bdir = os.path.join(args.out, "batches")
    os.makedirs(bdir, exist_ok=True)
    os.makedirs(os.path.join(args.out, "translated"), exist_ok=True)
    id2en = {i: s for i, s in enumerate(work)}
    nb = 0
    for i in range(0, len(work), args.batch):
        terms = [{"strref": j, "en": work[j]} for j in range(i, min(i + args.batch, len(work)))]
        json.dump({"batch": f"{nb:04d}", "terms": terms},
                  open(os.path.join(bdir, f"{nb:04d}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False); nb += 1
    json.dump({"id2en": id2en, "modules": {s: sorted(cand[s]) for s in work}},
              open(os.path.join(args.out, "index.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"worklist: {len(work)} unique English strings ({excluded} excluded as compare-operands), "
          f"{nb} batches -> {os.path.relpath(args.out, HERE)}")


if __name__ == "__main__":
    main()
