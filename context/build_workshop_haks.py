#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_workshop_haks.py - assemble Steam Workshop items that deliver the Russian
translation through each DLC's OWN hakpack instead of the global development/ folder.

Why: development/ (71M) is global - it overrides every module, so module.jrl there
replaces the journal of the original campaign ("ERROR, blank journal entry").
A hak (31M) outranks the module (20M) but is loaded ONLY by the module that lists it
in Mod_HakList. So the translation lands exactly where it belongs and nowhere else.

Layout per DLC item:
  hak/<first hak of Mod_HakList>.hak   original hak + every translated resource
  override/ ovr/                       Cyrillic fonts (CP1251 rendering)

  build_workshop_haks.py [--out build/workshop2] [--only <item substring>]
"""
import os, sys, struct, mmap, shutil, argparse
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import erf
from gff import read_gff

MNT = "/Volumes/twitch/nwn/data"
FONTS = os.path.join(PROOT, "payload", "lang", "en", "data", "ovr")
IFO = 2014                                    # module.ifo - never ship it, see below

# item -> [(translated module, original module, translated hak base or None)]
ITEMS = {
    "AI Russian Text Wyvern Crown of Cormyr": [
        ("dlc/cormyr/cormyr_ru_scr.nwm", f"{MNT}/nwm/Neverwinter Nights - Wyvern Crown of Cormyr.nwm",
         "dlc/cormyr_hak/cormyr_hak_ru.hak")],
    "AI Russian Text Pirates of the Sword Coast": [
        ("dlc/pirates/pirates_ru_scr.nwm", f"{MNT}/nwm/Neverwinter Nights - Pirates of the Sword Coast.nwm",
         "dlc/pirates_hak/pirates_hak_ru.hak")],
    "AI Russian Text Darkness over Daggerford": [
        ("dlc/daggerford/daggerford_ru_scr.nwm", f"{MNT}/nwm/Neverwinter Nights - Darkness over Daggerford.nwm",
         None)],
    "AI Russian Text Tyrants of the Moonsea": [
        ("dlc/moonsea/moonsea_ru_scr.nwm", f"{MNT}/nwm/Neverwinter Nights - Tyrants of the Moonsea.nwm",
         None)],
    "AI Russian Text Doom of Icewind Dale": [
        ("dlc/doid/doid_ru_scr.nwm", f"{MNT}/nwm/Neverwinter Nights - Doom of Icewind Dale.nwm",
         None)],
    "AI Russian Text Dark Dreams of Furiae": [
        ("ddf/DDF_ru_scr.nwm", f"{MNT}/nwm/Neverwinter Nights - Dark Dreams of Furiae.nwm",
         None)],
    "AI Russian Text Infinite Dungeons": [
        ("dlc/dungeons/dungeons_ru_scr.nwm", f"{MNT}/nwm/Neverwinter Nights - Infinite Dungeons.nwm",
         "dlc/dungeons_hak/dungeons_hak_ru.hak")],
    "AI Russian Text Heroes of Neverwinter": [
        ("dlc/kingmaker/kingmaker_ru_scr.mod", f"{MNT}/mod/Kingmaker.mod",
         "dlc/kingmaker_hak/kingmaker_hak_ru.hak"),
        ("dlc/shadowguard/shadowguard_ru_scr.mod", f"{MNT}/mod/ShadowGuard.mod",
         "dlc/shadowguard_hak/shadowguard_hak_ru.hak"),
        ("dlc/witchswake/witchswake_ru_scr.mod", f"{MNT}/mod/Witch's Wake.mod",
         "dlc/witchswake_hak/witchswake_hak_ru.hak")],
}


def P(*a):
    return os.path.join(PROOT, *a)


def first_hak(ru_module):
    """Mod_HakList[0] - the top hak, highest priority among the module's haks."""
    res = erf.read_erf(open(ru_module, "rb").read())["resources"]
    ifo = next(r["data"] for r in res if r["resref"].lower() == "module" and r["restype"] == IFO)
    root = read_gff(ifo)[1]
    f = {l: v for l, _t, v in root["fields"]}
    haks = f.get("Mod_HakList", [])
    if not haks:
        return None
    h = {l: v for l, _t, v in haks[0]["fields"]}["Mod_Hak"]
    return h.decode() if isinstance(h, bytes) else h


def translated_resources(ru_path, orig_path):
    """Every resource that differs from the original - i.e. everything we touched.
    module.ifo is excluded: the engine reads it from the module before haks load."""
    ru = erf.read_erf(open(ru_path, "rb").read())["resources"]
    om = {(r["resref"].lower(), r["restype"]): r["data"]
          for r in erf.read_erf(open(orig_path, "rb").read())["resources"]}
    out = {}
    for r in ru:
        key = (r["resref"].lower(), r["restype"])
        if r["restype"] == IFO or om.get(key) == r["data"]:
            continue
        out[key] = r["data"]
    return out


def merge_into_hak(base_path, payload, dst_path):
    """base hak + payload (replace on collision, append otherwise) -> dst, streamed."""
    f = open(base_path, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    assert mm[:4] in (b"HAK ", b"ERF "), mm[:4]
    n, _off_loc, off_keys, off_res = struct.unpack_from("<4I", mm, 16)

    entries, seen = [], set()
    for i in range(n):
        ko, ro = off_keys + 24 * i, off_res + 8 * i
        rr = mm[ko:ko + 16].split(b"\x00")[0].decode("ascii", "replace").lower()
        rt = struct.unpack_from("<H", mm, ko + 20)[0]
        roff, rsize = struct.unpack_from("<II", mm, ro)
        key = (rr, rt)
        seen.add(key)
        entries.append((rr, rt, ("mem", payload[key]) if key in payload else ("mm", roff, rsize)))
    replaced = sum(1 for k in payload if k in seen)
    added = [(rr, rt, ("mem", d)) for (rr, rt), d in payload.items() if (rr, rt) not in seen]
    entries.extend(added)

    N = len(entries)
    off_keys2 = 160
    off_res2 = off_keys2 + 24 * N
    cur = off_res2 + 8 * N
    hdr = bytearray(160)
    hdr[0:4], hdr[4:8] = b"HAK ", b"V1.0"
    struct.pack_into("<IIIIII", hdr, 8, 0, 0, N, off_keys2, off_keys2, off_res2)
    struct.pack_into("<III", hdr, 32, 0, 0, 0xFFFFFFFF)
    keys, reslist = bytearray(), bytearray()
    for i, (rr, rt, src) in enumerate(entries):
        size = len(src[1]) if src[0] == "mem" else src[2]
        keys.extend(rr.encode("ascii", "replace").ljust(16, b"\x00"))
        keys.extend(struct.pack("<IHH", i, rt, 0))
        reslist.extend(struct.pack("<II", cur, size))
        cur += size

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "wb") as out:
        out.write(hdr); out.write(keys); out.write(reslist)
        for _rr, _rt, src in entries:
            out.write(src[1] if src[0] == "mem" else mm[src[1]:src[1] + src[2]])
    mm.close(); f.close()
    return N, replaced, len(added)


def copy_fonts(item):
    for d in ("override", "ovr"):
        dd = os.path.join(item, d)
        os.makedirs(dd, exist_ok=True)
        for fn in os.listdir(FONTS):
            if not fn.startswith("."):
                shutil.copy2(os.path.join(FONTS, fn), os.path.join(dd, fn))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=P("build", "workshop2"))
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    for title, mods in ITEMS.items():
        if args.only and args.only.lower() not in title.lower():
            continue
        item = os.path.join(args.out, title)
        os.makedirs(item, exist_ok=True)
        for ru_rel, orig, tr_hak in mods:
            ru = P(ru_rel)
            hak = first_hak(ru)
            if not hak:
                print(f"!! {title}: {os.path.basename(ru)} has no haks - skipped")
                continue
            payload = translated_resources(ru, orig)
            base = P(tr_hak) if tr_hak else f"{MNT}/hk/{hak}.hak"
            dst = os.path.join(item, "hak", f"{hak}.hak")
            n, rep, add = merge_into_hak(base, payload, dst)
            types = Counter(rt for _rr, rt in payload)
            print(f"{title}\n   {os.path.basename(ru)} -> hak/{hak}.hak  "
                  f"[{n} res: {rep} replaced, {add} added]  {os.path.getsize(dst)/1e6:.0f} MB")
        copy_fonts(item)
        sz = sum(os.path.getsize(os.path.join(r, f)) for r, _d, fs in os.walk(item) for f in fs)
        print(f"   item total: {sz/1e6:.0f} MB\n")


if __name__ == "__main__":
    main()
