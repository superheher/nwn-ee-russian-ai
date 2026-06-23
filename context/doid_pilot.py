#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doid_pilot.py - pilot one DoID dialogue end-to-end: extract -> (translate) -> inject.

  doid_pilot.py prep  <dlg-resref>   reconstruct convo + dump English -> doid/pilot.en.json
  doid_pilot.py apply <dlg-resref>   read doid/pilot.ru.json {path:ru}, inject CP1251 into
                                      the .dlg, repack -> doid/DoID_pilot.nwm

Embedded-LocString path (premium module): we read/write the English strings inside
the module's GFF resources and repack the ERF (see gff.py / erf.py).
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import erf, gff

NWM = os.path.join(HERE, "..", "doid", "DoID.nwm")
DLG = 2029
EN = os.path.join(HERE, "..", "doid", "pilot.en.json")
RU = os.path.join(HERE, "..", "doid", "pilot.ru.json")
OUT = os.path.join(HERE, "..", "doid", "DoID_pilot.nwm")


def fd(struct):
    return {lbl: val for (lbl, ft, val) in struct["fields"]}


def loctext(loc):
    if isinstance(loc, dict) and loc.get("subs") and loc["subs"][0][1]:
        return loc["subs"][0][1].decode("cp1252", "replace")
    return ""


def reconstruct(root, max_lines=200):
    R = fd(root)
    entries, replies, starts = R.get("EntryList", []), R.get("ReplyList", []), R.get("StartingList", [])
    lines, seen = [], set()

    def walk(kind, idx, depth):
        if len(lines) >= max_lines or depth > 16 or idx < 0:
            return
        key = (kind, idx)
        if key in seen:
            return
        seen.add(key)
        pool = entries if kind == "E" else replies
        if idx >= len(pool):
            return
        node = fd(pool[idx])
        who = "NPC" if kind == "E" else "PC "
        txt = loctext(node.get("Text", {})).replace("\n", " / ")
        lines.append("  " * depth + f"[{who}] {txt}")
        nxt = node.get("RepliesList" if kind == "E" else "EntriesList", [])
        for link in nxt:
            walk("R" if kind == "E" else "E", fd(link).get("Index", -1), depth + 1)

    for s in starts:
        walk("E", fd(s).get("Index", -1), 0)
    return "\n".join(lines)


def strings_of(root):
    out = {}
    for path, loc in gff.iter_locstrings(root):
        en = loctext(loc)
        if en.strip():
            out[path] = en
    return out


def prep(resref):
    e = erf.read_erf(open(NWM, "rb").read())
    r = erf.get(e, resref, DLG)
    assert r, f"dialogue {resref} not found"
    ft, root = gff.read_gff(r["data"])
    data = {"dlg": resref, "script": reconstruct(root), "strings": strings_of(root)}
    json.dump(data, open(EN, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"dlg={resref}  strings={len(data['strings'])}")
    print("\n=== reconstructed conversation (EN) ===")
    print(data["script"])
    print(f"\nwrote {os.path.relpath(EN, HERE)}")


def apply(resref):
    ru = json.load(open(RU, encoding="utf-8"))
    e = erf.read_erf(open(NWM, "rb").read())
    r = erf.get(e, resref, DLG)
    ft, root = gff.read_gff(r["data"])
    applied = 0
    for path, loc in gff.iter_locstrings(root):
        if path in ru and ru[path].strip():
            rub = ru[path].encode("cp1251", "replace")
            loc["subs"] = [(sid, rub) for (sid, _b) in loc["subs"]] or [(0, rub)]
            applied += 1
    r["data"] = gff.write_gff(ft, root)
    open(OUT, "wb").write(erf.write_erf(e))
    print(f"applied {applied}/{len(ru)} RU strings into {resref}; wrote {os.path.relpath(OUT, HERE)}")


if __name__ == "__main__":
    mode, resref = sys.argv[1], sys.argv[2]
    (prep if mode == "prep" else apply)(resref)
