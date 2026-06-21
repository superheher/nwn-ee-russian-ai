#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Map where dialogue text lives: tally en_convo.bif resource types and read a
campaign .nwm (ERF) to count its .dlg conversations."""
import os, struct, sys, collections

DLG = 2029

def bif_types(path):
    b = open(path, "rb").read()
    var_count, fixed_count, var_off = struct.unpack_from("<III", b, 8)
    hist = collections.Counter()
    sample = {}
    o = var_off
    for _ in range(var_count):
        rid, roff, rsize, rtype = struct.unpack_from("<IIII", b, o)
        hist[rtype] += 1
        if rtype not in sample:
            sample[rtype] = b[roff:roff+8]
        o += 16
    return hist, sample

def erf_read(path):
    e = open(path, "rb").read()
    ftype, ver = e[:4], e[4:8]
    (lang_count, locstr_size, entry_count, off_locstr,
     off_keys, off_res) = struct.unpack_from("<IIIIII", e, 8)
    entries = []
    ko, ro = off_keys, off_res
    for _ in range(entry_count):
        resref = e[ko:ko+16].split(b"\x00")[0].decode("ascii", "replace")
        resid, rtype, unused = struct.unpack_from("<IHH", e, ko+16)
        roff, rsize = struct.unpack_from("<II", e, ro)
        entries.append((resref, rtype, roff, rsize))
        ko += 24; ro += 8
    return ftype, ver, e, entries

def main():
    game = sys.argv[1]
    print("=== en_convo.bif resource types ===")
    hist, sample = bif_types(os.path.join(game, "data", "en_convo.bif"))
    for rt, c in hist.most_common(6):
        print(f"  type {rt}: {c:6d}  sample head={sample[rt]!r}")

    print("\n=== campaign Chapter1.nwm (ERF) ===")
    ftype, ver, blob, entries = erf_read(os.path.join(game, "data", "nwm", "Chapter1.nwm"))
    print(f"  ERF type={ftype!r} ver={ver!r}, entries={len(entries)}")
    rh = collections.Counter(rt for _, rt, _, _ in entries)
    print("  top resource types:", dict(rh.most_common(8)))
    dlgs = [(rr, ro, rs) for rr, rt, ro, rs in entries if rt == DLG]
    print(f"  .dlg conversations: {len(dlgs)}")
    for rr, ro, rs in dlgs[:4]:
        print(f"    {rr:18s} size={rs:7d} head={blob[ro:ro+8]!r}")

if __name__ == "__main__":
    main()
