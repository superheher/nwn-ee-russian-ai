#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nss_prep.py - extract player-visible strings hard-coded in a module's SCRIPTS
(NSS) into translation batches + a write-back index. Companion to nss_apply.py.

Pipeline (per module):
  1. read every NSS (restype 2009) from the given ERF(s) [.nwm + content hak],
     write them to a work/include dir <out>/nss/ (English, comment-fixed).
  2. close dangling /* block comments (BioWare idiom that breaks nwnsc).
  3. extract ONLY display-bound literals (see nss_lex.DISPLAY_SLOTS + cutscene
     string vars); dedup by English; group by script for translator context.
  4. write batches (wf-shaped: {"terms":[{strref:id,en}]}) + index.json.

index.json:
  id2en : {id: english/template}
  id2occ: {id: [ occurrence, ... ]}   occurrence =
            {"f": resref, "k": "s", "r": [start,end]}                 simple literal
            {"f": resref, "k": "c", "lits": [[s,e],...]}              concat group
  meta  : {"archives": {resref: archive_basename}, ...}              for apply

  nss_prep.py --erf <a.nwm> [--erf <b.hak> ...] --out dlc/<mod>_scripts
              --nssdir tools/<mod>_src [--batch 90]
"""
import os, sys, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import erf, nss_lex

NSS = 2009


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--erf", action="append", required=True,
                    help="ERF archive(s) holding the scripts (.nwm/.mod and/or content hak)")
    ap.add_argument("--out", required=True, help="output dir for batches/index (dlc/<mod>_scripts)")
    ap.add_argument("--nssdir", required=True, help="work/include dir for the .nss sources (tools/<mod>_src)")
    ap.add_argument("--batch", type=int, default=90)
    args = ap.parse_args()

    os.makedirs(args.nssdir, exist_ok=True)
    os.makedirs(os.path.join(args.out, "batches"), exist_ok=True)

    # 1+2: dump NSS, fix comments, remember source archive per resref
    archive_of = {}
    sources = {}            # resref -> fixed bytes
    fixed_n = 0
    for path in args.erf:
        base = os.path.basename(path)
        e = erf.read_erf(open(path, "rb").read())
        for r in e["resources"]:
            if r["restype"] != NSS:
                continue
            rr = r["resref"].lower()
            if rr in sources:                       # first archive wins (.nwm before hak)
                continue
            data, changed = nss_lex.fix_comments(r["data"])
            fixed_n += changed
            sources[rr] = data
            archive_of[rr] = base
            open(os.path.join(args.nssdir, rr + ".nss"), "wb").write(data)
    print(f"NSS scripts: {len(sources)} (comment-fixed {fixed_n}) -> {args.nssdir}")

    # 3: extract units, dedup by English/template, group by script
    slots = nss_lex.discover_display_slots(sources)     # + module display-wrapper funcs
    wrappers = sorted(set(slots) - set(nss_lex.DISPLAY_SLOTS))
    if wrappers:
        print(f"display wrappers discovered ({len(wrappers)}): "
              + ", ".join(f"{w}{sorted(slots[w])}" for w in wrappers[:12])
              + (" ..." if len(wrappers) > 12 else ""))
    occ = {}                # en -> [occurrence...]
    order = []              # unique en, first-seen (grouped by script via sort below)
    for rr in sorted(sources):
        s = sources[rr].decode("latin-1")
        for u in nss_lex.extract(sources[rr], slots):
            en = u["en"]
            if en not in occ:
                occ[en] = []; order.append(en)
            if u["kind"] == "s":
                occ[en].append({"f": rr, "k": "s", "r": [u["start"], u["end"]]})
            else:                               # concat: whole-expr span + verbatim code pieces
                occ[en].append({"f": rr, "k": "c", "span": list(u["span"]),
                                "codes": [s[a:b] for a, b in u["codes"]]})

    en2id = {en: i for i, en in enumerate(order)}

    # 4: batches + index
    nb = 0
    for i in range(0, len(order), args.batch):
        chunk = order[i:i + args.batch]
        terms = [{"strref": en2id[en], "en": en} for en in chunk]
        json.dump({"batch": f"{nb:04d}", "terms": terms},
                  open(os.path.join(args.out, "batches", f"{nb:04d}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False)
        nb += 1

    index = {"id2en": {i: en for en, i in en2id.items()},
             "id2occ": {str(en2id[en]): occ[en] for en in order},
             "meta": {"archives": archive_of, "nssdir": os.path.abspath(args.nssdir)}}
    json.dump(index, open(os.path.join(args.out, "index.json"), "w", encoding="utf-8"),
              ensure_ascii=False)

    nocc = sum(len(v) for v in occ.values())
    nconc = sum(1 for v in occ.values() for o in v if o["k"] == "c")
    nchars = sum(len(en) for en in order)
    print(f"unique display strings: {len(order)}  occurrences: {nocc}  (concat groups: {nconc})")
    print(f"source chars: {nchars}  batches: {nb} (size {args.batch})")
    print(f"wrote {args.out}/batches/*.json + index.json")


if __name__ == "__main__":
    main()
