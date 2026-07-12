#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_mega_jrl.py - one module.jrl holding the journal categories of EVERY official module.

Why this exists: five bonus modules (Chess, Contest, Dark Ranger's Treasure, Winds of Eremor,
To Heir is Human) ship with an empty Mod_HakList, so their journal cannot be reached the way
the DLC's is (translation inside the module's own hak). The only layer above the module that
needs no hak is development/ (71M) - and it is global: whatever module.jrl sits there replaces
the journal of EVERY module, official or not.

So the file must carry the tags of everything the player might legitimately launch:
campaign + SoU + HotU + 8 premium DLC + 5 bonus modules. A module whose tags are missing shows
"ERROR, blank journal entry: <tag>" - which is exactly why this ships as a SEPARATE, opt-in
Workshop item: any user module from the Vault (including the curated ones the game itself
lists under "Community") will have a broken journal while it is subscribed.

Merge rules:
  - categories are keyed by Tag
  - same Tag in several modules -> entries merged by ID
  - same ID with different text -> priority campaign > DLC > bonus (the campaign is what
    everyone plays; the only real case is 'Henchman' ID=50, see README)

  build_mega_jrl.py [--out build/workshop2/AI Russian Text Journals]
"""
import os, sys, argparse
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
PROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import erf
from gff import read_gff, write_gff

MNT = "/Volumes/twitch/nwn/data"
JRL = 2056
TITLE = "AI Russian Text Journals"

# (priority, path) - lower number wins an ID conflict. Translated modules where we have them,
# because the DLC/bonus journals carry embedded Russian text; campaign journals are StrRef-only
# and take their text from dialog.tlk, so the pristine originals are exactly right.
def sources():
    P = lambda *a: os.path.join(PROOT, *a)
    campaign = [f"{MNT}/nwm/{m}.nwm" for m in
                ["Prelude", "Chapter1", "Chapter1E", "Chapter2", "Chapter2E", "Chapter3", "Chapter4",
                 "XP1-Chapter 1", "XP1-Chapter 2", "XP1-Interlude",
                 "XP2_Chapter1", "XP2_Chapter2", "XP2_Chapter3"]]
    dlc = [P("ddf/DDF_ru_scr.nwm"),
           P("dlc/cormyr/cormyr_ru_scr.nwm"), P("dlc/daggerford/daggerford_ru_scr.nwm"),
           P("dlc/doid/doid_ru_scr.nwm"), P("dlc/dungeons/dungeons_ru_scr.nwm"),
           P("dlc/moonsea/moonsea_ru_scr.nwm"), P("dlc/pirates/pirates_ru_scr.nwm"),
           P("dlc/kingmaker/kingmaker_ru_scr.mod"), P("dlc/shadowguard/shadowguard_ru_scr.mod"),
           P("dlc/witchswake/witchswake_ru_scr.mod")]
    bonus = [P("dlc/chess/chess_ru_scr.mod"), P("dlc/contest/contest_ru_scr.mod"),
             P("dlc/treasure/treasure_ru_scr.mod"), P("dlc/eremor/eremor_ru_scr.mod"),
             P("dlc/toheir/toheir_ru_scr.mod")]
    return [(0, p) for p in campaign] + [(1, p) for p in dlc] + [(2, p) for p in bonus]


def fields(struct):
    return {l: v for l, _t, v in struct["fields"]}


# the campaign modules carry English Mod_Name ("Chapter One") - label them by hand
LABELS = {
    "Prelude.nwm": "Пролог", "Chapter1.nwm": "Глава 1", "Chapter1E.nwm": "Глава 1",
    "Chapter2.nwm": "Глава 2", "Chapter2E.nwm": "Глава 2", "Chapter3.nwm": "Глава 3",
    "Chapter4.nwm": "Глава 4",
    "XP1-Chapter 1.nwm": "Тени Undrentide", "XP1-Chapter 2.nwm": "Тени Undrentide",
    "XP1-Interlude.nwm": "Тени Undrentide",
    "XP2_Chapter1.nwm": "Орды Подземья", "XP2_Chapter2.nwm": "Орды Подземья",
    "XP2_Chapter3.nwm": "Орды Подземья",
}


def mod_name(path):
    """Human-readable module name: hand label for the campaign, Mod_Name for everything else."""
    base = os.path.basename(path)
    if base in LABELS:
        return LABELS[base]
    res = erf.read_erf(open(path, "rb").read())["resources"]
    ifo = next((r["data"] for r in res
                if r["resref"].lower() == "module" and r["restype"] == 2014), None)
    if ifo:
        nm = fields(read_gff(ifo)[1]).get("Mod_Name", {})
        if nm.get("subs"):
            name = nm["subs"][0][1].decode("cp1251", "replace")
            for prefix in ("Neverwinter Nights — ", "Neverwinter Nights - ", "Neverwinter Nights: "):
                if name.startswith(prefix):
                    name = name[len(prefix):]
            return name.strip()
    return base


def text_of(loc, tlk):
    s = loc.get("strref")
    if s not in (None, -1, 0xFFFFFFFF):
        return tlk(s) or ""
    return loc["subs"][0][1].decode("cp1251", "replace") if loc.get("subs") else ""


def locstring(text):
    """Inline CP1251 text (strref = -1) - a merged entry cannot be a single TLK reference."""
    return {"strref": 0xFFFFFFFF, "subs": [(0, text.encode("cp1251", "replace"))]}


def merge_texts(variants):
    """variants: [(module name, text)] -> one entry showing every version, labelled."""
    return "\n\n".join(f"[ {name} ]\n{txt}" for name, txt in variants)


def journal_of(path):
    if not os.path.exists(path):                       # no script pass -> GFF-only build
        path = path.replace("_ru_scr.", "_ru.")
    res = erf.read_erf(open(path, "rb").read())["resources"]
    blob = next((r["data"] for r in res
                 if r["resref"].lower() == "module" and r["restype"] == JRL), None)
    return read_gff(blob)[1] if blob else None


def entry_id(entry):
    return fields(entry).get("ID")


def load_tlk(path):
    import struct as _st
    d = open(path, "rb").read()
    cnt = _st.unpack_from("<I", d, 12)[0]
    eo = _st.unpack_from("<I", d, 16)[0]

    def get(i):
        if i is None or i < 0 or i >= cnt:
            return None
        b = 20 + i * 40
        if not _st.unpack_from("<I", d, b)[0] & 1:
            return None
        off, sz = _st.unpack_from("<II", d, b + 28)
        return d[eo + off:eo + off + sz].decode("cp1251", "replace")
    return get


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(PROOT, "build", "workshop2", TITLE))
    args = ap.parse_args()
    tlk = load_tlk(os.path.join(PROOT, "build", "dialog.tlk"))

    cats = OrderedDict()   # tag -> {"struct":.., "names": [(mod, text)], "entries": {id: {"struct":.., "vars": [(mod,text)]}}}
    modules = 0
    for _prio, path in sources():
        root = journal_of(path)
        if root is None:
            continue
        modules += 1
        name = mod_name(path if os.path.exists(path) else path.replace("_ru_scr.", "_ru."))
        for cat in fields(root)["Categories"]:
            cf = fields(cat)
            tag = cf.get("Tag")
            tag = tag.decode() if isinstance(tag, bytes) else tag
            slot = cats.setdefault(tag, {"struct": cat, "names": [], "entries": OrderedDict()})
            slot["names"].append((name, text_of(cf["Name"], tlk)))
            for e in cf.get("EntryList", []):
                i = entry_id(e)
                es = slot["entries"].setdefault(i, {"struct": e, "vars": []})
                es["vars"].append((name, text_of(fields(e).get("Text", {}), tlk)))

    merged_entries = merged_names = 0
    for tag, slot in cats.items():
        # category title: merge only if the modules disagree
        uniq = list(OrderedDict((t, m) for m, t in slot["names"]).items())     # text -> module
        cat = slot["struct"]
        if len(uniq) > 1:
            merged_names += 1
            title = " / ".join(t for t, _m in uniq)
            cat["fields"] = [(l, t, locstring(title) if l == "Name" else v) for l, t, v in cat["fields"]]

        entries = []
        for i, es in sorted(slot["entries"].items(), key=lambda kv: kv[0]):
            uv = list(OrderedDict((t, m) for m, t in es["vars"]).items())      # text -> module
            e = es["struct"]
            if len(uv) > 1:                                                    # same ID, different text
                merged_entries += 1
                body = merge_texts([(m, t) for t, m in uv])
                e["fields"] = [(l, t, locstring(body) if l == "Text" else v) for l, t, v in e["fields"]]
            entries.append(e)
        cat["fields"] = [(l, t, entries if l == "EntryList" else v) for l, t, v in cat["fields"]]

    root = {"type": 0xFFFFFFFF,
            "fields": [("Categories", 15, [s["struct"] for s in cats.values()])]}
    blob = write_gff(b"JRL ", root)

    os.makedirs(os.path.join(args.out, "development"), exist_ok=True)
    dst = os.path.join(args.out, "development", "module.jrl")
    open(dst, "wb").write(blob)

    total = sum(len(s["entries"]) for s in cats.values())
    print(f"{TITLE}")
    print(f"   modules read      : {modules}")
    print(f"   categories (tags) : {len(cats)}")
    print(f"   entries           : {total}")
    print(f"   merged entries    : {merged_entries}  (same tag+ID, different text -> both shown, labelled)")
    print(f"   merged titles     : {merged_names}")
    print(f"   -> {dst}  ({os.path.getsize(dst)/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
