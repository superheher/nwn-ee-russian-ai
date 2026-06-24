#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tlk_fix.py - apply small RU string overrides to a built dialog.tlk.

For UI-wording tweaks after the base translation is built: a JSON map of
{strref: "Russian text"} is applied to dialog.tlk, rebuilding the string-data
section (offsets recomputed, so length changes are fine). Russian is written as
CP1251. Re-runnable; meant to be re-applied after any full tlk rebuild.

  tlk_fix.py --tlk build/dialog.tlk --overrides context/tlk_overrides.json [--out PATH]
"""
import argparse, json, struct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tlk", required=True)
    ap.add_argument("--overrides", required=True)
    ap.add_argument("--out", help="default: overwrite --tlk in place")
    args = ap.parse_args()

    ov = {int(k): v for k, v in json.load(open(args.overrides, encoding="utf-8")).items()}
    d = open(args.tlk, "rb").read()
    assert d[:8] == b"TLK V3.0", d[:8]
    n, eoff = struct.unpack_from("<II", d, 12)

    enttbl = bytearray(); blob = bytearray(); cur = 0; changed = 0
    for i in range(n):
        o = 20 + i * 40
        flags = struct.unpack_from("<I", d, o)[0]
        sound = d[o + 4:o + 20]
        volvar, pitchvar = struct.unpack_from("<II", d, o + 20)
        soff, ssz = struct.unpack_from("<II", d, o + 28)
        soundlen = d[o + 36:o + 40]
        txt = d[eoff + soff:eoff + soff + ssz] if (flags & 1) else b""
        if i in ov:
            txt = ov[i].encode("cp1251"); flags |= 1; changed += 1
        off = cur if (flags & 1) else 0
        sz = len(txt) if (flags & 1) else 0
        enttbl += (struct.pack("<I", flags) + sound + struct.pack("<II", volvar, pitchvar)
                   + struct.pack("<II", off, sz) + soundlen)
        if flags & 1:
            blob += txt; cur += len(txt)

    out = bytearray(d[:20])
    struct.pack_into("<I", out, 16, 20 + len(enttbl))   # StringEntriesOffset
    out += enttbl + blob
    outpath = args.out or args.tlk
    open(outpath, "wb").write(bytes(out))
    print(f"applied {changed}/{len(ov)} overrides -> {outpath} ({len(out):,} bytes, {n} strings)")


if __name__ == "__main__":
    main()
