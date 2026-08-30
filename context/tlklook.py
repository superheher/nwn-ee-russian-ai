#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tlklook.py - look up strings across the three text sources.

  tlklook.py 50788 67 ...             show English / ours / 1C for each StrRef
  tlklook.py --grep-ru "ОТМЕНА"       our Russian text matches (regex)
  tlklook.py --grep-en "Level Up"     English matches (regex)
  tlklook.py --exact-en "Cancel"      StrRefs whose English is exactly this
  tlklook.py --owner 50788            which translated/*.json supplies it
"""
import os, re, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tlkutil


def show(en, ru, ref, i):
    print(f"@{i}\n  EN : {en[i]}\n  OUR: {ru[i]}\n  1C : {ref[i].strip()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("strrefs", nargs="*", type=int)
    ap.add_argument("--grep-ru"); ap.add_argument("--grep-en")
    ap.add_argument("--exact-en"); ap.add_argument("--owner", type=int)
    ap.add_argument("--limit", type=int, default=40)
    a = ap.parse_args()
    en, ru, ref = tlkutil.load_all()
    for i in a.strrefs:
        show(en, ru, ref, i)
    if a.owner is not None:
        print(tlkutil.strref_owner().get(a.owner, "<not translated by us>"))
    for pat, src in ((a.grep_ru, ru), (a.grep_en, en)):
        if pat:
            rx = re.compile(pat, re.I)
            n = 0
            for i, s in enumerate(src):
                if s and rx.search(s):
                    show(en, ru, ref, i); n += 1
                    if n >= a.limit:
                        print(f"... stopped at {a.limit} matches"); break
    if a.exact_en:
        for i, s in enumerate(en):
            if s.strip() == a.exact_en:
                show(en, ru, ref, i)


if __name__ == "__main__":
    main()
