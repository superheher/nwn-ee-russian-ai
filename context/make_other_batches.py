#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_other_batches.py - batch the "other" bucket (UI / journal / misc strings
that are neither dialog nor 2da system text) for translation.

Reads context/coverage.json ids.other, fetches the English text, and writes
fixed-size batches under context/otherbatches/. These have no conversational
context; they are translated with the glossary + code validation.
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nwn

BATCH = 90


def main():
    tlk = nwn.load_tlk(os.path.join(HERE, "..", "backup", "english", "dialog.tlk"))
    cov = json.load(open(os.path.join(HERE, "coverage.json")))
    other = cov["ids"]["other"]

    bdir = os.path.join(HERE, "otherbatches")
    os.makedirs(bdir, exist_ok=True)
    for f in os.listdir(bdir):
        os.remove(os.path.join(bdir, f))

    idx = total = 0
    for i in range(0, len(other), BATCH):
        chunk = []
        for s in other[i:i + BATCH]:
            en = tlk(s)
            if en and en.strip():
                chunk.append({"strref": s, "en": en})
        if not chunk:
            continue
        json.dump({"batch": f"{idx:04d}", "terms": chunk},
                  open(os.path.join(bdir, f"{idx:04d}.json"), "w"),
                  ensure_ascii=False, indent=1)
        idx += 1
        total += len(chunk)
    print(f"other batches: {idx} batches, {total} strrefs -> {bdir}/")


if __name__ == "__main__":
    main()
