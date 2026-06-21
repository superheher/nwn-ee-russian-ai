#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_dlg.py - locate and extract BioWare .dlg (conversation) resources from
the game's KEY/BIFF archives. Step 1 of building dialogue context for translation.

Formats (BioWare Aurora):
  KEY V1  : index of resources -> (bif index, resource id)
  BIFF V1 : container holding the actual resource blobs
  .dlg    : a GFF "DLG V3.2" file (parsed in a later step)
"""
import os, struct, sys

DLG = 2029  # resource type for conversation files

def parse_key(path):
    k = open(path, "rb").read()
    assert k[:8] == b"KEY V1  ", k[:8]
    bif_count, key_count, file_off, key_off = struct.unpack_from("<IIII", k, 8)
    bifs = []
    o = file_off
    for _ in range(bif_count):
        fsize, fn_off, fn_size, drives = struct.unpack_from("<IIHH", k, o)
        name = k[fn_off:fn_off+fn_size].split(b"\x00")[0].decode("ascii", "replace")
        bifs.append(name.replace("\\", "/"))
        o += 12
    # resource keys: ResRef[16], ResType u16, ResID u32  (22 bytes)
    res = []  # (resref, restype, bif_idx, res_idx)
    o = key_off
    for _ in range(key_count):
        resref = k[o:o+16].split(b"\x00")[0].decode("ascii", "replace")
        restype, resid = struct.unpack_from("<HI", k, o+16)
        res.append((resref, restype, resid >> 20, resid & 0xFFFFF))
        o += 22
    return bifs, res

def bif_table(path):
    b = open(path, "rb").read()
    assert b[:8] == b"BIFFV1  ", b[:8]
    var_count, fixed_count, var_off = struct.unpack_from("<III", b, 8)
    table = {}  # res_idx -> (offset, size)
    o = var_off
    for _ in range(var_count):
        rid, roff, rsize, rtype = struct.unpack_from("<IIII", b, o)
        table[rid & 0xFFFFF] = (roff, rsize)
        o += 16
    return b, table

def main():
    game = sys.argv[1]
    key_path = os.path.join(game, "data", "nwn_base.key")
    bifs, res = parse_key(key_path)
    dlgs = [(rr, bi, ri) for (rr, rt, bi, ri) in res if rt == DLG]
    print(f"BIFs in key: {len(bifs)}")
    # which bifs hold .dlg?
    by_bif = {}
    for rr, bi, ri in dlgs:
        by_bif.setdefault(bi, []).append((rr, ri))
    print(f"total .dlg resources: {len(dlgs)}")
    for bi, items in sorted(by_bif.items()):
        print(f"  bif[{bi}] = {bifs[bi]}  -> {len(items)} dlg")

    # extract a sample .dlg and verify GFF header
    sample_bif = max(by_bif, key=lambda b: len(by_bif[b]))
    bpath = os.path.join(game, bifs[sample_bif])
    print(f"\nopening {bpath}")
    data, table = bif_table(bpath)
    print(f"  bif resources: {len(table)}")
    shown = 0
    for rr, ri in by_bif[sample_bif][:5]:
        if ri in table:
            off, size = table[ri]
            blob = data[off:off+size]
            print(f"  {rr:18s} idx={ri:6d} size={size:7d} head={blob[:8]!r}")
            shown += 1
    print(f"\nsample extracted: {shown} (head should be b'DLG V3.2')")

if __name__ == "__main__":
    main()
