#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gff.py - LOSSLESS reader + writer for BioWare GFF V3.2 (the format inside .dlg,
.utc, .uti, .are, .jrl, module.ifo, ... resources of a .nwm/.mod).

nwn.py reads GFF for display (lossy: CExoLocString -> just the strref). To
TRANSLATE a premium module whose text is embedded (DoID), we must read the
embedded strings AND write them back. This module round-trips the full tree.

Tree model:
  struct = {"type": int, "fields": [ (label:str, ftype:int, value) ]}
  value by ftype:
    0..5, 8   inline (BYTE/CHAR/WORD/SHORT/DWORD/INT/FLOAT) -> raw 4-byte uint (int)
    6,7,9     DWORD64/INT64/DOUBLE -> raw 8 bytes
    10        CExoString  -> bytes (content)
    11        CResRef     -> bytes (content)
    12        CExoLocString -> {"strref": int(-1 if none), "subs": [(stringid:int, bytes)]}
    13        VOID        -> bytes (content)
    14        Struct      -> nested struct dict
    15        List        -> [struct dict, ...]
"""
import struct as _s

INLINE = {0, 1, 2, 3, 4, 5, 8}


class _Reader:
    def __init__(self, data):
        self.d = data
        self.ftype4 = data[:4]
        assert data[4:8] == b"V3.2", data[:8]
        (self.so, self.sn, self.fo, self.fn, self.lo, self.ln,
         self.do, self.dn, self.io, self.in_, self.lio, self.lin) = _s.unpack_from("<12I", data, 8)

    def label(self, i):
        o = self.lo + i * 16
        return self.d[o:o + 16].split(b"\x00")[0].decode("ascii", "replace")

    def struct(self, idx):
        o = self.so + idx * 12
        stype, dataoff, count = _s.unpack_from("<III", self.d, o)
        if count == 0:
            fidx = []
        elif count == 1:
            fidx = [dataoff]
        else:
            fidx = [_s.unpack_from("<I", self.d, self.io + dataoff + 4 * j)[0] for j in range(count)]
        fields = []
        for fi in fidx:
            o2 = self.fo + fi * 12
            ftype, lbl, val = _s.unpack_from("<III", self.d, o2)
            fields.append((self.label(lbl), ftype, self.value(ftype, val)))
        return {"type": stype, "fields": fields}

    def value(self, ftype, val):
        d = self.d
        if ftype in INLINE:
            return val                                   # raw 4-byte uint, re-emitted verbatim
        if ftype in (6, 7, 9):
            return d[self.do + val:self.do + val + 8]    # raw 8 bytes
        if ftype == 10:                                  # CExoString
            o = self.do + val; n = _s.unpack_from("<I", d, o)[0]
            return d[o + 4:o + 4 + n]
        if ftype == 11:                                  # CResRef
            o = self.do + val; n = d[o]
            return d[o + 1:o + 1 + n]
        if ftype == 12:                                  # CExoLocString
            o = self.do + val
            total, strref, count = _s.unpack_from("<III", d, o)
            p = o + 12; subs = []
            for _ in range(count):
                sid, ln = _s.unpack_from("<II", d, p)
                subs.append((sid, d[p + 8:p + 8 + ln])); p += 8 + ln
            return {"strref": -1 if strref == 0xFFFFFFFF else strref, "subs": subs}
        if ftype == 13:                                  # VOID
            o = self.do + val; n = _s.unpack_from("<I", d, o)[0]
            return d[o + 4:o + 4 + n]
        if ftype == 14:                                  # Struct
            return self.struct(val)
        if ftype == 15:                                  # List
            o = self.lio + val; n = _s.unpack_from("<I", d, o)[0]
            idxs = _s.unpack_from(f"<{n}I", d, o + 4) if n else ()
            return [self.struct(si) for si in idxs]
        raise ValueError(f"unknown GFF field type {ftype}")


def read_gff(data):
    r = _Reader(data)
    return r.ftype4, r.struct(0)


def write_gff(ftype4, root):
    structs = []
    def assign(s):
        s["_idx"] = len(structs); structs.append(s)
        for (_lbl, ft, v) in s["fields"]:
            if ft == 14:
                assign(v)
            elif ft == 15:
                for cs in v:
                    assign(cs)
    assign(root)

    labels = []; lab_idx = {}
    def lab(name):
        if name not in lab_idx:
            lab_idx[name] = len(labels); labels.append(name)
        return lab_idx[name]

    fields = []                 # (ftype, labelindex, dataordataoffset)
    fdata = bytearray()
    findices = bytearray()
    lindices = bytearray()
    struct_entries = []

    def enc(ft, v):
        if ft in INLINE:
            return v
        if ft in (6, 7, 9):
            off = len(fdata); fdata.extend(v); return off
        if ft == 10:
            off = len(fdata); fdata.extend(_s.pack("<I", len(v))); fdata.extend(v); return off
        if ft == 11:
            off = len(fdata); fdata.append(len(v)); fdata.extend(v); return off
        if ft == 12:
            subs = bytearray()
            for sid, b in v["subs"]:
                subs.extend(_s.pack("<II", sid, len(b))); subs.extend(b)
            strref = 0xFFFFFFFF if v["strref"] == -1 else v["strref"]
            total = 8 + len(subs)
            off = len(fdata)
            fdata.extend(_s.pack("<III", total, strref, len(v["subs"]))); fdata.extend(subs)
            return off
        if ft == 13:
            off = len(fdata); fdata.extend(_s.pack("<I", len(v))); fdata.extend(v); return off
        if ft == 14:
            return v["_idx"]
        if ft == 15:
            off = len(lindices); lindices.extend(_s.pack("<I", len(v)))
            for cs in v:
                lindices.extend(_s.pack("<I", cs["_idx"]))
            return off
        raise ValueError(f"unknown GFF field type {ft}")

    for s in structs:
        fidxs = []
        for (name, ft, v) in s["fields"]:
            fi = len(fields)
            fields.append((ft, lab(name), enc(ft, v)))
            fidxs.append(fi)
        cnt = len(fidxs)
        if cnt == 0:
            dod = 0
        elif cnt == 1:
            dod = fidxs[0]
        else:
            dod = len(findices)
            for fi in fidxs:
                findices.extend(_s.pack("<I", fi))
        struct_entries.append((s["type"], dod, cnt))

    for s in structs:
        s.pop("_idx", None)

    struct_blob = b"".join(_s.pack("<III", *e) for e in struct_entries)
    field_blob = b"".join(_s.pack("<III", *f) for f in fields)
    label_blob = b"".join(n.encode("ascii")[:16].ljust(16, b"\x00") for n in labels)

    so = 56
    fo = so + len(struct_blob)
    lo = fo + len(field_blob)
    do = lo + len(label_blob)
    io = do + len(fdata)
    lio = io + len(findices)
    header = ftype4 + b"V3.2" + _s.pack(
        "<12I", so, len(struct_entries), fo, len(fields), lo, len(labels),
        do, len(fdata), io, len(findices), lio, len(lindices))
    return (header + struct_blob + field_blob + label_blob +
            bytes(fdata) + bytes(findices) + bytes(lindices))


# --------------------------------------------------------- LocString helpers ---
def iter_locstrings(struct, path=""):
    """Yield (path, locstring_dict) for every CExoLocString in the tree."""
    for (label, ftype, value) in struct["fields"]:
        p = f"{path}.{label}"
        if ftype == 12:
            yield p, value
        elif ftype == 14:
            yield from iter_locstrings(value, p)
        elif ftype == 15:
            for i, cs in enumerate(value):
                yield from iter_locstrings(cs, f"{p}[{i}]")
