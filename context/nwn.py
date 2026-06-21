#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nwn.py - readers for BioWare Aurora formats needed to reconstruct conversations:
  KEY V1 / BIFF V1  - resource index + containers (base game)
  ERF "MOD" V1.0    - campaign module archives (.nwm)
  GFF V3.2          - generic struct format; .dlg conversations are GFF

Goal: turn a .dlg into a readable conversation script with the dialog.tlk StrRef
of every line, so each line can be translated WITH its conversational context.
"""
import os, struct, sys

DLG = 2029

# ----------------------------------------------------------------- KEY/BIFF ----
def parse_key(path):
    k = open(path, "rb").read()
    assert k[:8] == b"KEY V1  "
    bif_count, key_count, file_off, key_off = struct.unpack_from("<IIII", k, 8)
    bifs = []
    o = file_off
    for _ in range(bif_count):
        fsize, fn_off, fn_size, drives = struct.unpack_from("<IIHH", k, o)
        bifs.append(k[fn_off:fn_off+fn_size].split(b"\x00")[0].decode("ascii").replace("\\", "/"))
        o += 12
    res = {}  # (resref.lower, restype) -> (bif_idx, res_idx)
    o = key_off
    for _ in range(key_count):
        resref = k[o:o+16].split(b"\x00")[0].decode("ascii", "replace").lower()
        restype, resid = struct.unpack_from("<HI", k, o+16)
        res[(resref, restype)] = (resid >> 20, resid & 0xFFFFF)
        o += 22
    return bifs, res

def bif_resource(game, bifs, bif_idx, res_idx):
    b = open(os.path.join(game, bifs[bif_idx]), "rb").read()
    assert b[:8] == b"BIFFV1  "
    var_count, fixed_count, var_off = struct.unpack_from("<III", b, 8)
    o = var_off
    for _ in range(var_count):
        rid, roff, rsize, rtype = struct.unpack_from("<IIII", b, o)
        if (rid & 0xFFFFF) == res_idx:
            return b[roff:roff+rsize]
        o += 16
    return None

# --------------------------------------------------------------------- ERF ----
def erf_resource(path, resref, restype=DLG):
    e = open(path, "rb").read()
    (lang_count, locstr_size, entry_count, off_locstr,
     off_keys, off_res) = struct.unpack_from("<IIIIII", e, 8)
    ko, ro = off_keys, off_res
    for _ in range(entry_count):
        rr = e[ko:ko+16].split(b"\x00")[0].decode("ascii", "replace").lower()
        resid, rtype, unused = struct.unpack_from("<IHH", e, ko+16)
        if rr == resref.lower() and rtype == restype:
            roff, rsize = struct.unpack_from("<II", e, ro)
            return e[roff:roff+rsize]
        ko += 24; ro += 8
    return None

# --------------------------------------------------------------------- GFF ----
class Gff:
    def __init__(self, data):
        self.d = data
        assert data[4:8] == b"V3.2", data[:8]
        (self.struct_off, self.struct_n, self.field_off, self.field_n,
         self.label_off, self.label_n, self.fdata_off, self.fdata_n,
         self.findices_off, self.findices_n, self.lindices_off,
         self.lindices_n) = struct.unpack_from("<12I", data, 8)

    def _label(self, i):
        o = self.label_off + i*16
        return self.d[o:o+16].split(b"\x00")[0].decode("ascii", "replace")

    def _field(self, i):
        o = self.field_off + i*12
        return struct.unpack_from("<III", self.d, o)  # type, labelIdx, dataOrOffset

    def struct(self, idx):
        o = self.struct_off + idx*12
        stype, dataoff, count = struct.unpack_from("<III", self.d, o)
        if count == 0:
            return {}
        if count == 1:
            fidx = [dataoff]
        else:
            fidx = [struct.unpack_from("<I", self.d, self.findices_off + dataoff + 4*j)[0]
                    for j in range(count)]
        out = {}
        for fi in fidx:
            ftype, lbl, val = self._field(fi)
            out[self._label(lbl)] = self._value(ftype, val)
        return out

    def _value(self, ftype, val):
        d = self.d
        if ftype in (0, 1, 2, 3, 4, 5, 8):          # <=32-bit simple
            return val
        if ftype in (6, 7, 9):                       # 64-bit
            return struct.unpack_from("<Q", d, self.fdata_off + val)[0]
        if ftype == 10:                              # CExoString
            o = self.fdata_off + val
            n = struct.unpack_from("<I", d, o)[0]
            return d[o+4:o+4+n].decode("cp1252", "replace")
        if ftype == 11:                              # CResRef
            o = self.fdata_off + val
            n = d[o]
            return d[o+1:o+1+n].decode("ascii", "replace")
        if ftype == 12:                              # CExoLocString
            o = self.fdata_off + val
            total, strref, count = struct.unpack_from("<III", d, o)
            return {"strref": -1 if strref == 0xFFFFFFFF else strref}
        if ftype == 14:                              # Struct
            return self.struct(val)
        if ftype == 15:                              # List
            o = self.lindices_off + val
            n = struct.unpack_from("<I", d, o)[0]
            idxs = struct.unpack_from(f"<{n}I", d, o+4) if n else ()
            return [self.struct(si) for si in idxs]
        return None

# ----------------------------------------------------------- .dlg -> script ----
def load_tlk(path):
    dd = open(path, "rb").read()
    cnt = struct.unpack_from("<I", dd, 12)[0]; eo = struct.unpack_from("<I", dd, 16)[0]
    def get(i):
        if i is None or i < 0 or i >= cnt:
            return ""
        b = 20 + i*40; fl = struct.unpack_from("<I", dd, b)[0]
        if not fl & 1:
            return ""
        off = struct.unpack_from("<I", dd, b+28)[0]; sz = struct.unpack_from("<I", dd, b+32)[0]
        return dd[eo+off:eo+off+sz].decode("cp1252", "replace")
    return get

def reconstruct(dlg_blob, tlk_get, max_lines=60):
    g = Gff(dlg_blob)
    top = g.struct(0)
    entries = top.get("EntryList", [])
    replies = top.get("ReplyList", [])
    starts = top.get("StartingList", [])
    lines = []
    seen = set()
    def strref(node):
        t = node.get("Text", {})
        return t.get("strref", -1) if isinstance(t, dict) else -1

    def walk(kind, idx, depth):
        if len(lines) >= max_lines or depth > 12:
            return
        key = (kind, idx)
        if key in seen:
            lines.append(("  " * depth) + f"… (→ повтор узла {kind}#{idx})")
            return
        seen.add(key)
        node = entries[idx] if kind == "E" else replies[idx]
        sr = strref(node)
        who = "NPC" if kind == "E" else "PC"
        speaker = node.get("Speaker", "") if kind == "E" else ""
        tag = f" «{speaker}»" if speaker else ""
        text = tlk_get(sr).replace("\n", " ⏎ ")
        lines.append(("  " * depth) + f"[{who}{tag} @{sr}] {text}")
        nxt = node.get("RepliesList" if kind == "E" else "EntriesList", [])
        for link in nxt:
            walk("R" if kind == "E" else "E", link.get("Index", -1), depth+1)

    for s in starts:
        walk("E", s.get("Index", -1), 0)
    return entries, replies, lines

# -------------------------------------------------------------------- main ----
def main():
    game = sys.argv[1]
    module = sys.argv[2] if len(sys.argv) > 2 else "Chapter1.nwm"
    resref = sys.argv[3] if len(sys.argv) > 3 else None
    tlk = load_tlk(os.path.join(os.path.dirname(__file__), "..", "backup", "english", "dialog.tlk"))

    mod_path = os.path.join(game, "data", "nwm", module)
    # if no resref given, list a few .dlg from the module and pick the first
    if resref is None:
        e = open(mod_path, "rb").read()
        (_, _, entry_count, _, off_keys, _) = struct.unpack_from("<IIIIII", e, 8)
        ko = off_keys
        for _ in range(entry_count):
            rr = e[ko:ko+16].split(b"\x00")[0].decode("ascii", "replace")
            _, rtype, _ = struct.unpack_from("<IHH", e, ko+16)
            if rtype == DLG:
                resref = rr; break
            ko += 24
    print(f"module={module} dlg={resref}")
    blob = erf_resource(mod_path, resref)
    if not blob:
        print("not found"); return
    entries, replies, lines = reconstruct(blob, tlk)
    print(f"entries(NPC)={len(entries)} replies(PC)={len(replies)}\n")
    print("=== reconstructed conversation (EN, with @strref) ===")
    for ln in lines:
        print(ln)

if __name__ == "__main__":
    main()
