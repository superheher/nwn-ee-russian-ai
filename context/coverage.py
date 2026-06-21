#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
coverage.py - partition every StrRef of the English dialog.tlk into
dialog / system / other, prove nothing is lost, and size the work.

Inputs:  backup/english/dialog.tlk, context/dialog_index.json, context/system_map.json
Output:  context/coverage.json   { buckets, overlaps, char/byte totals, the id sets }
"""
import os, sys, json, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def load_tlk_entries(path):
    """Return list of (strref, text) for every non-empty TEXT_PRESENT entry."""
    d = open(path, "rb").read()
    assert d[:8] == b"TLK V3.0", d[:8]
    count = struct.unpack_from("<I", d, 12)[0]
    eo = struct.unpack_from("<I", d, 16)[0]
    out = {}
    for i in range(count):
        b = 20 + i * 40
        flags = struct.unpack_from("<I", d, b)[0]
        if not flags & 1:
            continue
        off = struct.unpack_from("<I", d, b + 28)[0]
        sz = struct.unpack_from("<I", d, b + 32)[0]
        if sz == 0:
            continue
        txt = d[eo + off:eo + off + sz].decode("cp1252", "replace")
        if txt.strip():
            out[i] = txt
    return count, out


def chars(idset, textmap):
    return sum(len(textmap[s]) for s in idset if s in textmap)


def main():
    tlk_path = os.path.join(HERE, "..", "backup", "english", "dialog.tlk")
    count, textmap = load_tlk_entries(tlk_path)
    translatable = set(textmap)

    didx = json.load(open(os.path.join(HERE, "dialog_index.json")))
    smap = json.load(open(os.path.join(HERE, "system_map.json")))
    dialog_sr = set(didx["all_dialog_strref"])
    system_sr = set(int(k) for k in smap["by_strref"])

    # Priority: a StrRef used in any conversation counts as dialog first.
    dialog_in = translatable & dialog_sr
    system_in = (translatable & system_sr) - dialog_in
    other_in = translatable - dialog_in - system_in

    overlap_ds = dialog_sr & system_sr                    # referenced by both
    dialog_blank = dialog_sr - translatable               # referenced but empty in tlk
    system_blank = system_sr - translatable

    cov = {
        "tlk_entries_total": count,
        "translatable_total": len(translatable),
        "buckets": {
            "dialog":  {"n": len(dialog_in),  "chars": chars(dialog_in, textmap)},
            "system":  {"n": len(system_in),  "chars": chars(system_in, textmap)},
            "other":   {"n": len(other_in),   "chars": chars(other_in, textmap)},
        },
        "checks": {
            "sum_buckets": len(dialog_in) + len(system_in) + len(other_in),
            "lost": len(translatable) - (len(dialog_in) + len(system_in) + len(other_in)),
            "dialog_referenced_but_blank": len(dialog_blank),
            "system_referenced_but_blank": len(system_blank),
            "dialog_system_overlap": len(overlap_ds),
        },
        "ids": {
            "system": sorted(system_in),
            "other": sorted(other_in),
        },
    }
    json.dump(cov, open(os.path.join(HERE, "coverage.json"), "w"),
              ensure_ascii=False, indent=1)

    b = cov["buckets"]
    print(f"tlk entries total:        {count:>7}")
    print(f"translatable (non-empty): {len(translatable):>7}")
    print(f"  dialog : {b['dialog']['n']:>6}  ({b['dialog']['chars']:>9,} chars)")
    print(f"  system : {b['system']['n']:>6}  ({b['system']['chars']:>9,} chars)")
    print(f"  other  : {b['other']['n']:>6}  ({b['other']['chars']:>9,} chars)")
    c = cov["checks"]
    print(f"\nsum of buckets = {c['sum_buckets']}  (lost: {c['lost']})")
    print(f"dialog refs blank in tlk: {c['dialog_referenced_but_blank']}")
    print(f"dialog/system overlap (dedup to dialog): {c['dialog_system_overlap']}")
    tot_chars = sum(x['chars'] for x in b.values())
    print(f"\ntotal translatable chars: {tot_chars:,}  (~{tot_chars//4:,} tokens of EN text)")
    print(f"wrote {os.path.join(HERE, 'coverage.json')}")


if __name__ == "__main__":
    main()
