#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepare a single conversation as structured input for the pilot translation
workflow: the readable script (context), the unique translatable lines, and a
relevant glossary subset."""
import os, sys, json, struct, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nwn

def main():
    game = sys.argv[1]
    module = sys.argv[2] if len(sys.argv) > 2 else "Chapter1.nwm"
    resref = sys.argv[3] if len(sys.argv) > 3 else "m1q01a03eltr"
    tlk = nwn.load_tlk(os.path.join(HERE, "..", "backup", "english", "dialog.tlk"))
    blob = nwn.erf_resource(os.path.join(game, "data", "nwm", module), resref)
    entries, replies, lines = nwn.reconstruct(blob, tlk, max_lines=200)

    # unique translatable lines (skip empty / -1)
    seen, items = set(), []
    for role, arr in (("NPC", entries), ("PC", replies)):
        for n in arr:
            t = n.get("Text", {})
            sr = t.get("strref", -1) if isinstance(t, dict) else -1
            en = tlk(sr)
            if sr >= 0 and en and sr not in seen:
                seen.add(sr); items.append({"strref": sr, "role": role, "en": en})
    items.sort(key=lambda x: x["strref"])

    # relevant glossary: core + hybrid overrides + mined terms that appear here
    def load_tsv(p):
        out = {}
        for ln in open(os.path.join(HERE, "..", "glossary", p), encoding="utf-8").read().splitlines()[1:]:
            c = ln.split("\t")
            if p == "core_glossary.tsv":
                if len(c) >= 3 and c[1]:
                    out[c[1]] = c[2]          # core: category, EN, RU, strref -> EN->RU
            else:
                if len(c) >= 2 and c[0]:
                    out[c[0]] = c[1]          # mined: EN, RU -> EN->RU
        return out
    core = load_tsv("core_glossary.tsv")
    over = {r.split("\t")[0]: r.split("\t")[1] for r in
            open(os.path.join(HERE, "..", "glossary", "hybrid_overrides.tsv"),
                 encoding="utf-8").read().splitlines()[1:] if r.split("\t")[0]}
    mined = load_tsv("mined_glossary.tsv")
    text_all = " ".join(i["en"] for i in items)
    rel = {}
    for en_t, ru_t in mined.items():
        if len(en_t) >= 4 and re.search(r"\b" + re.escape(en_t) + r"\b", text_all):
            rel[en_t] = ru_t
    glossary = {**core, **rel}              # core + matched
    glossary = dict(sorted(glossary.items(), key=lambda x: -len(x[0]))[:80])  # cap

    out = {"module": module, "dlg": resref,
           "script": "\n".join(lines),
           "lines": items, "glossary": glossary, "overrides": over}
    json.dump(out, open(os.path.join(HERE, "pilot_input.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"lines to translate: {len(items)}  | glossary terms: {len(glossary)}  | overrides: {len(over)}")
    print("low-INT / tricky samples:")
    for i in items:
        if "Me " in i["en"] or " me " in i["en"].lower()[:8] or "<" in i["en"]:
            print(f"   @{i['strref']} [{i['role']}] {i['en'][:70]}")
    print("\noverrides:", over)
    print("glossary sample:", dict(list(glossary.items())[:8]))
    print("pilot_input.json written.")

if __name__ == "__main__":
    main()
