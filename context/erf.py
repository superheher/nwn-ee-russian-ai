#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
erf.py - reader + writer for BioWare ERF "MOD V1.0" archives (.nwm/.mod).

Write strategy (robust + byte-faithful): we only ever EDIT resource data (never
add/remove resources), so we keep the original file bytes verbatim up to the
ResourceList (header + localized-string list + key list + a reserved zero table
that the header's off_res pointer skips), and rebuild ONLY the ResourceList
offsets/sizes and the contiguous resource-data section. For an unmodified module
this reproduces the original byte-for-byte.

  erf = read_erf(open(path,'rb').read())
  erf["resources"][i]["data"] = <new GFF bytes>
  open(out,'wb').write(write_erf(erf))
"""
import struct as _s


def read_erf(data):
    assert data[:4] in (b"MOD ", b"HAK ", b"ERF ", b"SAV "), data[:8]
    lang_count, locstr_size, n, off_locstr, off_keys, off_res = _s.unpack_from("<6I", data, 8)
    ko, ro = off_keys, off_res
    resources = []
    for _ in range(n):
        rr = data[ko:ko + 16].split(b"\x00")[0].decode("ascii", "replace")
        resid, rtype, _u = _s.unpack_from("<IHH", data, ko + 16)
        roff, rsize = _s.unpack_from("<II", data, ro)
        resources.append({"resref": rr, "restype": rtype, "resid": resid,
                          "data": data[roff:roff + rsize]})
        ko += 24; ro += 8
    return {"prefix": data[:off_res],   # header + locstr + keylist + reserved zero-table (verbatim)
            "off_res": off_res, "n": n, "resources": resources}


def write_erf(erf):
    res = erf["resources"]
    assert len(res) == erf["n"], "resource count changed - prefix (keylist) would be stale"
    off_res = erf["off_res"]
    data_start = off_res + 8 * len(res)
    reslist = bytearray()
    blobs = bytearray()
    cur = data_start
    for r in res:
        d = r["data"]
        reslist.extend(_s.pack("<II", cur, len(d)))
        blobs.extend(d); cur += len(d)
    return bytes(erf["prefix"]) + bytes(reslist) + bytes(blobs)


def get(erf, resref, restype):
    for r in erf["resources"]:
        if r["resref"].lower() == resref.lower() and r["restype"] == restype:
            return r
    return None
