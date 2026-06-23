#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doid_extract.py - extract translatable text from the Doom of Icewind Dale module.

Unlike the base game (text in the shared dialog.tlk), this premium module stores
its text as EMBEDDED localized strings (CExoLocString with the English inline,
strref = -1; Mod_CustomTlk is empty). So we read the embedded English directly
out of every GFF resource (DLG/UTC/UTI/ARE/JRL/IFO/...) inside the .nwm (ERF).

Output: scope report (per-type counts, chars) + doid/strings.json worklist
(every embedded English string with its resource + field path, for translation).
NOTE: scripts (NSS source) are NOT included here - hardcoded display strings in
scripts are a separate, harder concern.

  doid_extract.py [path-to.nwm]   default: doid/DoID.nwm
"""
import os, sys, struct, json
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nwn

RT = {2012:"ARE",2014:"IFO",2023:"GIT",2025:"UTI",2027:"UTC",2029:"DLG",2030:"ITP",
      2032:"UTT",2033:"UTS",2035:"UTM",2040:"UTW",2042:"UTE",2044:"UTD",2045:"UTP",
      2051:"GIC",2056:"JRL",2058:"FAC"}


class LocGff(nwn.Gff):
    """Like nwn.Gff but CExoLocString returns the embedded substrings too."""
    def _value(self, ftype, val):
        if ftype == 12:
            o = self.fdata_off + val
            total, strref, count = struct.unpack_from("<III", self.d, o)
            p = o + 12
            strings = []
            for _ in range(count):
                langid, length = struct.unpack_from("<II", self.d, p)
                txt = self.d[p+8:p+8+length].decode("cp1252", "replace")
                strings.append((langid, txt))
                p += 8 + length
            return {"__loc__": True,
                    "strref": -1 if strref == 0xFFFFFFFF else strref,
                    "strings": strings}
        return super()._value(ftype, val)


def erf_iter(path):
    e = open(path, "rb").read()
    assert e[:4] == b"MOD ", e[:8]
    _, _, n, _, off_keys, off_res = struct.unpack_from("<IIIIII", e, 8)
    ko, ro = off_keys, off_res
    for _ in range(n):
        rr = e[ko:ko+16].split(b"\x00")[0].decode("ascii", "replace")
        _, rtype, _ = struct.unpack_from("<IHH", e, ko+16)
        roff, rsize = struct.unpack_from("<II", e, ro)
        yield rr, rtype, e[roff:roff+rsize]
        ko += 24; ro += 8


def collect(obj, path, out):
    if isinstance(obj, dict):
        if obj.get("__loc__"):
            en = next((t for lid, t in obj["strings"] if lid in (0, 1)), "")  # 0=EN(m),1=EN(f)
            if not en and obj["strings"]:
                en = obj["strings"][0][1]
            if en.strip():
                out.append((path, obj["strref"], en))
            return
        for k, v in obj.items():
            collect(v, f"{path}.{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            collect(v, f"{path}[{i}]", out)


def main():
    nwm = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "doid", "DoID.nwm")
    per_type = Counter(); per_type_chars = Counter()
    worklist = []
    for rr, rtype, blob in erf_iter(nwm):
        if blob[4:8] != b"V3.2":          # only GFF resources carry LocStrings
            continue
        try:
            top = LocGff(blob).struct(0)
        except Exception as e:
            continue
        found = []
        collect(top, "", found)
        for path, strref, en in found:
            per_type[rtype] += 1; per_type_chars[rtype] += len(en)
            worklist.append({"res": rr, "type": RT.get(rtype, str(rtype)), "path": path, "en": en})

    total = len(worklist); chars = sum(len(w["en"]) for w in worklist)
    uniq = {w["en"] for w in worklist}
    uchars = sum(len(s) for s in uniq)
    print("=== translatable embedded English strings (GFF resources) ===")
    for t, n in sorted(per_type.items(), key=lambda x: -x[1]):
        print(f"  {RT.get(t, str(t)):<6} {n:>5} strings  {per_type_chars[t]:>8,} chars")
    print(f"\n  TOTAL        {total:>5} strings  {chars:>8,} chars  (~{chars//4:,} tokens)")
    print(f"  UNIQUE       {len(uniq):>5} strings  {uchars:>8,} chars  (~{uchars//4:,} tokens)  <- real work after dedup")

    out = os.path.join(HERE, "..", "doid", "strings.json")
    json.dump(worklist, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nwrote {os.path.relpath(out, HERE)} ({total} entries)")


if __name__ == "__main__":
    main()
