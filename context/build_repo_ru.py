#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_repo_ru.py - rebuild the Russian repository.json overlays from our own
translation (context/repo_translated.json) and the pristine English structure.

repository.json drives the campaign/module SELECTION screen (names + blurbs).
Our translation lives as a flat {key -> ru} map in repo_translated.json, where
key = "<sub>|<uuid-or-name>|<field>" (sub in {mod, nwm}; field in {name,
description}; "__top__" for the file-level name/description). This script applies
those strings onto the English structure (keeping uuids and every other field)
and writes payload/data/<sub>/repository.json, which install_ru.py then installs
with --repo remap (re-encoding Cyrillic to U+00xx for the bitmap UI font).

English source: the originals install_ru.py backed up under backup/orig/...; pass
--english-dir to point elsewhere (e.g. a pristine game data/ dir).

  build_repo_ru.py [--english-dir DIR] [--out-dir DIR] [--translated FILE]
"""
import argparse, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PROOT = os.path.dirname(HERE)
DEFAULT_GAME = os.path.expanduser(
    "~/Library/Application Support/Steam/steamapps/common/Neverwinter Nights")
# where install_ru.py mirrors the original game files
DEFAULT_EN_DIR = os.path.join(PROOT, "backup", "orig",
                              os.path.relpath(DEFAULT_GAME, "/"), "data")
DEFAULT_OUT_DIR = os.path.join(PROOT, "payload", "data")
DEFAULT_TRANSLATED = os.path.join(HERE, "repo_translated.json")
SUBS = ("mod", "nwm")


def apply_overlay(english, ru, sub):
    """Replace name/description on the English structure from the ru map."""
    applied = 0
    for f in ("name", "description"):
        k = f"{sub}|__top__|{f}"
        if k in ru and isinstance(english.get(f), str):
            english[f] = ru[k]; applied += 1
    for key in ("campaigns", "modules"):
        for it in (english.get(key) or []):
            if not isinstance(it, dict):
                continue
            uid = it.get("uuid") or it.get("name", "?")
            for f in ("name", "description"):
                k = f"{sub}|{uid}|{f}"
                if k in ru and isinstance(it.get(f), str):
                    it[f] = ru[k]; applied += 1
    return applied


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--english-dir", default=DEFAULT_EN_DIR)
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--translated", default=DEFAULT_TRANSLATED)
    args = ap.parse_args()

    ru = json.load(open(args.translated, encoding="utf-8"))
    for sub in SUBS:
        en_path = os.path.join(args.english_dir, sub, "repository.json")
        if not os.path.exists(en_path):
            print(f"  ! {sub}: English source not found: {en_path}"); continue
        d = json.load(open(en_path, encoding="utf-8"))
        n = apply_overlay(d, ru, sub)
        out = os.path.join(args.out_dir, sub, "repository.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(d, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"  {sub}: applied {n} RU fields -> {out}")


if __name__ == "__main__":
    main()
