#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tlkutil.py - shared helpers for post-translation audits.

Loads the three text sources an audit needs (English base tlk, OUR built RU tlk,
the 1C-derived russifier's line dump) and indexes which translated/**.json file
owns each StrRef, so a fix can be written back to its source of truth.
"""
import os, re, json, glob, struct

HERE = os.path.dirname(os.path.abspath(__file__))
EN_TLK = os.path.join(HERE, "..", "backup", "english", "dialog.tlk")
RU_TLK = os.path.join(HERE, "..", "build", "dialog.tlk")
REF_1C = os.path.join(HERE, "..", "payload", "patcher", "dialog.tlk_RU.txt")
TRANSLATED = os.path.join(HERE, "translated")


def read_tlk(path, encoding):
    d = open(path, "rb").read()
    assert d[:8] == b"TLK V3.0", d[:8]
    n, eoff = struct.unpack_from("<II", d, 12)
    out = []
    for i in range(n):
        o = 20 + i * 40
        flags = struct.unpack_from("<I", d, o)[0]
        soff, ssz = struct.unpack_from("<II", d, o + 28)
        out.append(d[eoff + soff:eoff + soff + ssz].decode(encoding, "replace")
                   if flags & 1 else "")
    return out


def load_all():
    en = read_tlk(EN_TLK, "cp1252")
    ru = read_tlk(RU_TLK, "cp1251")
    ref = open(REF_1C, "rb").read().decode("cp1251", "replace").split("\n")
    ref += [""] * max(0, len(en) - len(ref))
    return en, ru, ref


def strref_owner(tdir=TRANSLATED):
    """{strref -> path of the translated json that supplies it} (last wins, as
    assemble_tlk.py merges)."""
    owner = {}
    for p in sorted(glob.glob(os.path.join(tdir, "**", "*.json"), recursive=True)):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get("translations"), list):
            for t in d["translations"]:
                if "strref" in t and t.get("ru"):
                    owner[int(t["strref"])] = p
        elif isinstance(d, dict):
            for k, v in d.items():
                if k.lstrip("-").isdigit():
                    ru = v.get("ru") if isinstance(v, dict) else v
                    if isinstance(ru, str) and ru:
                        owner[int(k)] = p
    return owner


# --- crude Cyrillic -> Latin key, enough to match a name against its original ---
_TR = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
       "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
       "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
       "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
       "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "u", "я": "a"}


def translit(word):
    return "".join(_TR.get(c, c) for c in word.lower())


CYR_WORD = re.compile(r"[А-ЯЁ][а-яё]+(?:-[А-ЯЁа-яё]+)?")
