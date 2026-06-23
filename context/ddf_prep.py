#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ddf_prep.py - extract a premium module's embedded text into translation batches
+ a write-back index. (Built for Dark Dreams of Furiae; works for any embedded-
LocString module via --nwm/--out.)

- Dedup by English (translate each unique string once).
- Order strings grouped by resource (dialogue lines of one conversation stay
  adjacent -> implicit context for the translator).
- Batches are in the same shape wf_module.js / wf_batches.js consume:
    {"batch": "NNNN", "terms": [{"strref": <int id>, "en": "..."}]}
- index.json maps each id -> every (resref, restype, path) occurrence, for apply.

  ddf_prep.py [--nwm ddf/DDF.nwm] [--out ddf] [--batch 90]
"""
import os, sys, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import erf, gff


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nwm", default=os.path.join(HERE, "..", "ddf", "DDF.nwm"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "ddf"))
    ap.add_argument("--batch", type=int, default=90)
    args = ap.parse_args()

    e = erf.read_erf(open(args.nwm, "rb").read())
    occ = {}        # en -> [(resref, restype, path), ...]
    order = []      # unique en, first-seen order (grouped by resource)
    # group by resource so a dialogue's lines stay together
    for r in sorted(e["resources"], key=lambda x: (x["restype"], x["resref"])):
        if r["data"][4:8] != b"V3.2":
            continue
        try:
            _ft, root = gff.read_gff(r["data"])
        except Exception:
            continue
        for path, loc in gff.iter_locstrings(root):
            if loc.get("subs") and loc["subs"][0][1].strip():
                en = loc["subs"][0][1].decode("cp1252", "replace")
                if en not in occ:
                    occ[en] = []; order.append(en)
                occ[en].append((r["resref"], r["restype"], path))

    en2id = {en: i for i, en in enumerate(order)}
    bdir = os.path.join(args.out, "batches")
    os.makedirs(bdir, exist_ok=True)
    nb = 0
    for i in range(0, len(order), args.batch):
        chunk = order[i:i + args.batch]
        terms = [{"strref": en2id[en], "en": en} for en in chunk]
        json.dump({"batch": f"{nb:04d}", "terms": terms},
                  open(os.path.join(bdir, f"{nb:04d}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False)
        nb += 1

    index = {"id2en": {i: en for en, i in en2id.items()},
             "id2occ": {str(en2id[en]): occ[en] for en in order}}
    json.dump(index, open(os.path.join(args.out, "index.json"), "w", encoding="utf-8"),
              ensure_ascii=False)

    nocc = sum(len(v) for v in occ.values())
    print(f"unique strings: {len(order)}  occurrences: {nocc}  batches: {nb} (size {args.batch})")
    print(f"wrote {os.path.relpath(bdir, HERE)}/*.json + index.json")


if __name__ == "__main__":
    main()
