#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_manifests.py - split the 1,664 conversations into balanced chunk manifests
for the dialog workflow, each <= ~420 conversations so a chunk's agent count
(1 loader + 2 per conversation) stays safely under the 1000-agent workflow cap.
Also pre-creates the per-source translated/ output directories.
"""
import os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))

GROUPS = {
    "g1": ["Chapter1", "base_dialog", "Chapter1E", "Prelude"],
    "g2": ["Chapter2", "Chapter2E"],
    "g3": ["Chapter3", "XP1-Chapter_1", "Chapter4"],
    "g4": ["XP2_Chapter2", "XP2_Chapter1", "XP2_Chapter3"],
    "g5": ["XP1-Interlude", "XP1-Chapter_2"],
}


def main():
    mdir = os.path.join(HERE, "manifests")
    os.makedirs(mdir, exist_ok=True)
    grand = 0
    for g, sources in GROUPS.items():
        work = []
        for safe in sources:
            os.makedirs(os.path.join(HERE, "translated", safe), exist_ok=True)
            cdir = os.path.join(HERE, "convos", safe)
            resrefs = sorted(os.path.splitext(os.path.basename(p))[0]
                             for p in glob.glob(os.path.join(cdir, "*.json")))
            for rr in resrefs:
                work.append({"source": safe, "resref": rr})
        json.dump(work, open(os.path.join(mdir, f"{g}.json"), "w"),
                  ensure_ascii=False)
        agents = 1 + 2 * len(work)
        grand += len(work)
        print(f"{g}: {len(work):>4} convos ({'+'.join(sources)})  ~{agents} agents")
    print(f"total: {grand} conversations across {len(GROUPS)} chunks")


if __name__ == "__main__":
    main()
