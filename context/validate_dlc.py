#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_dlc.py - final code-validation of the translated DLC batches.

Mirrors the workflow's inline validate(): for every translated string, the set of
identifier <...> tags (excluding gender-fork tokens that contain '/'), the printf
%s/%d placeholders, and the literal-newline count must match the English source.
Also flags empty RU and untranslated (missing) strrefs. Run after translation to
catch the rare batch whose repair step failed (e.g. during an API outage).

  validate_dlc.py [dlc_dir]   default: ../dlc
"""
import os, sys, json, re, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "dlc")

TAG = re.compile(r"<[^>\n]+>")
PH = re.compile(r"%[-+ 0-9.]*[sdifcuxXeg%]")
def tags(s): return sorted(t for t in TAG.findall(str(s)) if "/" not in t and not t.startswith("<<"))
def phs(s): return sorted(PH.findall(str(s)))
def nls(s): return str(s).count("\n")

problems = 0
for moddir in sorted(glob.glob(os.path.join(ROOT, "*"))):
    if not os.path.isdir(moddir):
        continue
    mod = os.path.basename(moddir)
    en = {}
    for bp in glob.glob(os.path.join(moddir, "batches", "*.json")):
        for t in json.load(open(bp, encoding="utf-8")).get("terms", []):
            en[str(t["strref"])] = t["en"]
    ru = {}
    for tp in glob.glob(os.path.join(moddir, "translated", "*.json")):
        for k, v in json.load(open(tp, encoding="utf-8")).items():
            ru[str(k)] = v
    missing = [k for k in en if k not in ru]
    bad = []
    for k, e in en.items():
        if k not in ru:
            continue
        r = ru[k]
        if not str(r).strip():
            bad.append((k, "empty RU"))
        elif tags(e) != tags(r):
            bad.append((k, f"tags {tags(e)} vs {tags(r)}"))
        elif phs(e) != phs(r):
            bad.append((k, f"placeholders {phs(e)} vs {phs(r)}"))
        elif nls(e) != nls(r):
            bad.append((k, f"newlines {nls(e)} vs {nls(r)}"))
    if missing or bad:
        problems += len(missing) + len(bad)
        print(f"{mod:<13} unique={len(en):<6} translated={len(ru):<6} MISSING={len(missing)} BAD={len(bad)}")
        for k, p in bad[:8]:
            print(f"    @{k}: {p}")
        if missing:
            print(f"    missing strrefs (e.g.): {missing[:8]}")
    else:
        print(f"{mod:<13} unique={len(en):<6} OK")

print("\n" + ("ALL CLEAN" if problems == 0 else f"{problems} issues to fix"))
