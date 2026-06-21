#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_sys_batches.py - prepare system-text (2da) translation batches.

- Deterministically pre-fills the ~89 core glossary StrRefs (class/race/skill/
  ability/... names) with their authoritative hybrid Russian, written straight to
  context/translated/_sys_glossary/core.json (no LLM needed).
- Groups the remaining system StrRefs (spell/feat/item names & descriptions, ...)
  by (category, role) into ~70-line batches under context/sysbatches/ for the
  batch-translation workflow. Each StrRef appears once (uses the deduped map).
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nwn

GLOSS = os.path.join(HERE, "..", "glossary")
BATCH = 70


def core_by_strref():
    """{strref -> RU} for core glossary with hybrid overrides applied."""
    over = {}
    for ln in open(os.path.join(GLOSS, "hybrid_overrides.tsv"), encoding="utf-8") \
            .read().splitlines()[1:]:
        c = ln.split("\t")
        if len(c) >= 2 and c[0]:
            over[c[0]] = c[1]
    out = {}
    for ln in open(os.path.join(GLOSS, "core_glossary.tsv"), encoding="utf-8") \
            .read().splitlines()[1:]:
        c = ln.split("\t")
        if len(c) >= 4 and c[3].strip().isdigit():
            en, ru, sr = c[1], c[2], int(c[3])
            out[sr] = over.get(en, ru)
    return out


def main():
    game = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.expanduser("~/Library/Application Support/Steam/steamapps/"
                           "common/Neverwinter Nights")
    tlk = nwn.load_tlk(os.path.join(HERE, "..", "backup", "english", "dialog.tlk"))
    smap = json.load(open(os.path.join(HERE, "system_map.json")))
    prefill = core_by_strref()

    # 1) deterministic core prefill
    pdir = os.path.join(HERE, "translated", "_sys_glossary")
    os.makedirs(pdir, exist_ok=True)
    json.dump({str(k): v for k, v in sorted(prefill.items())},
              open(os.path.join(pdir, "core.json"), "w"), ensure_ascii=False, indent=1)

    # 2) remaining system strrefs grouped by (cat, role), deduped via by_strref
    groups = {}
    for sr_s, info in smap["by_strref"].items():
        sr = int(sr_s)
        if sr in prefill:
            continue
        en = tlk(sr)
        if not en or not en.strip():
            continue
        groups.setdefault((info["cat"], info["role"]), []).append((sr, en))

    bdir = os.path.join(HERE, "sysbatches")
    os.makedirs(bdir, exist_ok=True)
    for f in os.listdir(bdir):
        os.remove(os.path.join(bdir, f))

    idx = 0
    total = 0
    for (cat, role) in sorted(groups):
        terms = sorted(groups[(cat, role)])
        for i in range(0, len(terms), BATCH):
            chunk = terms[i:i + BATCH]
            name = f"{idx:03d}_{cat}_{role}"
            json.dump({"batch": name, "cat": cat, "role": role,
                       "terms": [{"strref": s, "en": e} for s, e in chunk]},
                      open(os.path.join(bdir, f"{name}.json"), "w"),
                      ensure_ascii=False, indent=1)
            idx += 1
            total += len(chunk)

    print(f"core prefill (deterministic): {len(prefill)} strrefs -> {pdir}/core.json")
    print(f"system batches needing LLM:   {idx} batches, {total} strrefs -> {bdir}/")


if __name__ == "__main__":
    main()
