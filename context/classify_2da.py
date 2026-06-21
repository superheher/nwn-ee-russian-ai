#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
classify_2da.py - build a StrRef -> system-text category map from the 2da tables.

Reads every .2da resource (restype 2017) indexed by nwn_base.key, parses the
textual "2DA V2.0" format, and records every StrRef found in name/description
columns. The result lets the coverage map split the dialog.tlk into
dialog / system / other and lets the workflow translate system text in
category batches (class/race/feat/skill/spell/item names & descriptions).

Output: context/system_map.json
  {
    "by_strref": { "<strref>": {"cat": "<2da>", "col": "<header>", "role": "name|desc"} , ...},
    "by_category": { "<2da>": {"name": [strref,...], "desc": [strref,...]} , ... },
    "stats": {...}
  }
"""
import os, sys, json, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nwn

TWODA = 2017

# Column headers (lowercased substring match) whose integer cells are StrRefs.
NAME_KEYS = ("name", "plural", "lower", "conver", "title", "namegen")
DESC_KEYS = ("desc", "descript", "hint", "tooltip")
# Extra exact column headers per 2da basename that don't match the keywords.
EXTRA = {
    "feat":       [("FEAT", "name"), ("DESCRIPTION", "desc")],
    "spells":     [("SpellDesc", "desc")],
    "baseitems":  [("DescIdentified", "desc")],
}
# 2da files known to hold pure UI / gameplay numbers, not translatable text:
# their "Name"-like columns are labels, not StrRefs. Skip to avoid noise.
SKIP = {"appearance", "placeables", "tailmodel", "wingmodel"}


def load_bif_index(path):
    """Read a BIFF once, return (bytes, {res_idx: (offset, size)})."""
    b = open(path, "rb").read()
    assert b[:8] == b"BIFFV1  ", b[:8]
    var_count, fixed_count, var_off = struct.unpack_from("<III", b, 8)
    idx = {}
    o = var_off
    for _ in range(var_count):
        rid, roff, rsize, rtype = struct.unpack_from("<IIII", b, o)
        idx[rid & 0xFFFFF] = (roff, rsize)
        o += 16
    return b, idx


def tokenize_2da(line):
    """Split a 2da row into cells, honouring double-quoted cells."""
    out, i, n = [], 0, len(line)
    while i < n:
        while i < n and line[i] in " \t":
            i += 1
        if i >= n:
            break
        if line[i] == '"':
            j = line.find('"', i + 1)
            if j < 0:
                out.append(line[i + 1:]); break
            out.append(line[i + 1:j]); i = j + 1
        else:
            j = i
            while j < n and line[j] not in " \t":
                j += 1
            out.append(line[i:j]); i = j
    return out


def parse_2da(text):
    """Return (header_cols, rows) for a 2DA V2.0 table; ([],[]) if malformed."""
    lines = text.split("\n")
    if not lines or not lines[0].startswith("2DA"):
        return [], []
    i = 1
    while i < len(lines) and (not lines[i].strip() or
                              lines[i].strip().upper().startswith("DEFAULT:")):
        i += 1
    if i >= len(lines):
        return [], []
    header = tokenize_2da(lines[i])
    rows = []
    for ln in lines[i + 1:]:
        if not ln.strip():
            continue
        rows.append(tokenize_2da(ln))
    return header, rows


def main():
    game = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.expanduser("~/Library/Application Support/Steam/steamapps/"
                           "common/Neverwinter Nights")
    key_path = os.path.join(game, "data", "nwn_base.key")
    bifs, res = nwn.parse_key(key_path)

    # cache opened bifs by index
    bif_cache = {}
    def get_res(bif_idx, res_idx):
        if bif_idx not in bif_cache:
            bif_cache[bif_idx] = load_bif_index(os.path.join(game, bifs[bif_idx]))
        data, idx = bif_cache[bif_idx]
        if res_idx not in idx:
            return None
        off, size = idx[res_idx]
        return data[off:off + size]

    twoda_keys = [(rr, loc) for (rr, rt), loc in res.items() if rt == TWODA]
    twoda_keys.sort()

    by_strref = {}            # strref -> {cat, col, role}  (first writer wins)
    by_category = {}          # cat -> {"name": set, "desc": set}
    collisions = 0
    parsed = 0

    for rr, (bif_idx, res_idx) in twoda_keys:
        if rr in SKIP:
            continue
        blob = get_res(bif_idx, res_idx)
        if not blob:
            continue
        text = blob.decode("cp1252", "replace")
        header, rows = parse_2da(text)
        if not header:
            continue
        parsed += 1
        # which columns are translatable, and their role
        cols = []   # (col_index, header, role)
        for ci, h in enumerate(header):
            hl = h.lower()
            role = None
            if any(k in hl for k in DESC_KEYS):
                role = "desc"
            elif any(k in hl for k in NAME_KEYS):
                role = "name"
            if role:
                cols.append((ci, h, role))
        for h, role in EXTRA.get(rr, []):
            if h in header:
                ci = header.index(h)
                if not any(c[0] == ci for c in cols):
                    cols.append((ci, h, role))
        if not cols:
            continue
        cat = by_category.setdefault(rr, {"name": set(), "desc": set()})
        for row in rows:
            for ci, h, role in cols:
                # row[0] is the row index; data columns start at row[1]
                vi = ci + 1
                if vi >= len(row):
                    continue
                cell = row[vi]
                if cell == "****" or not cell.lstrip("-").isdigit():
                    continue
                sr = int(cell)
                if sr < 0 or sr >= 0x01000000:   # skip custom/alt-tlk refs
                    continue
                cat[role].add(sr)
                if sr not in by_strref:
                    by_strref[sr] = {"cat": rr, "col": h, "role": role}
                else:
                    collisions += 1

    out = {
        "by_strref": {str(k): v for k, v in sorted(by_strref.items())},
        "by_category": {k: {"name": sorted(v["name"]), "desc": sorted(v["desc"])}
                        for k, v in sorted(by_category.items())},
        "stats": {
            "twoda_total": len(twoda_keys),
            "twoda_parsed": parsed,
            "categories": len(by_category),
            "unique_strrefs": len(by_strref),
            "collisions": collisions,
        },
    }
    outp = os.path.join(HERE, "system_map.json")
    json.dump(out, open(outp, "w"), ensure_ascii=False, indent=1)

    s = out["stats"]
    print(f"2da resources: {s['twoda_total']}  parsed: {s['twoda_parsed']}")
    print(f"categories: {s['categories']}  unique system StrRefs: {s['unique_strrefs']}"
          f"  (collisions ignored: {s['collisions']})")
    top = sorted(out["by_category"].items(),
                 key=lambda kv: -(len(kv[1]['name']) + len(kv[1]['desc'])))[:25]
    print("\ntop categories by StrRef count (name+desc):")
    for cat, d in top:
        print(f"  {cat:<24} name={len(d['name']):<6} desc={len(d['desc'])}")
    print(f"\nwrote {outp}")


if __name__ == "__main__":
    main()
