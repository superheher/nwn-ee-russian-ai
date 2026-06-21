#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_worklist.py - prepare a dialog source for the translation workflow.

Splits one source bundle (context/dialogs/<safe>.json) into per-conversation
input files (context/convos/<safe>/<resref>.json) that a workflow agent reads
on its own, and emits a small worklist (context/worklists/<safe>.json) holding
the active hybrid glossary + the list of conversations to translate. The
worklist is small enough to pass as Workflow `args`.

Usage:  make_worklist.py <safe>     where <safe> is the dialogs/<safe>.json basename
        e.g. Prelude | XP1-Chapter_1 | base_dialog
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
GLOSS = os.path.join(HERE, "..", "glossary")


def active_glossary():
    """Hybrid term base: community core with HW overrides applied (hard rules)."""
    core = {}
    for ln in open(os.path.join(GLOSS, "core_glossary.tsv"), encoding="utf-8") \
            .read().splitlines()[1:]:
        c = ln.split("\t")
        if len(c) >= 3 and c[1]:
            core[c[1]] = c[2]                       # EN -> RU
    over = {}
    for ln in open(os.path.join(GLOSS, "hybrid_overrides.tsv"), encoding="utf-8") \
            .read().splitlines()[1:]:
        c = ln.split("\t")
        if len(c) >= 2 and c[0]:
            over[c[0]] = c[1]
    core.update(over)                              # overrides win
    return core, over


def main():
    safe = sys.argv[1]
    bundle = json.load(open(os.path.join(HERE, "dialogs", f"{safe}.json")))
    source = bundle["source"]
    cdir = os.path.join(HERE, "convos", safe)
    os.makedirs(cdir, exist_ok=True)

    work = []
    for c in bundle["conversations"]:
        rr = c["resref"]
        json.dump({"resref": rr, "source": source,
                   "script": c["script"], "lines": c["lines"]},
                  open(os.path.join(cdir, f"{rr}.json"), "w"),
                  ensure_ascii=False)
        work.append({"resref": rr, "n": c["n_unique"]})

    gloss, over = active_glossary()
    wl = {"source": source, "safe": safe,
          "glossary": gloss, "overrides": over, "work": work}
    os.makedirs(os.path.join(HERE, "worklists"), exist_ok=True)
    wlp = os.path.join(HERE, "worklists", f"{safe}.json")
    json.dump(wl, open(wlp, "w"), ensure_ascii=False, indent=1)

    # standalone active glossary (same for every source) for workflow agents to read
    json.dump({"terms": gloss, "overrides": over},
              open(os.path.join(HERE, "glossary_active.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"{source}: {len(work)} conversations, "
          f"{sum(w['n'] for w in work)} strrefs, glossary {len(gloss)} terms")
    print(f"  inputs : context/convos/{safe}/<resref>.json")
    print(f"  worklist: {wlp}")


if __name__ == "__main__":
    main()
