#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_remaining.py - filter a dialog manifest to conversations not yet fully
translated, for idempotent re-runs after rate-limit failures.

A conversation counts as done if its output file exists and has a non-empty RU
string for at least as many strrefs as the source has lines. Writes
manifests/<name>_remaining.json.

Usage:  make_remaining.py context/manifests/g1.json
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    man = sys.argv[1]
    work = json.load(open(man))
    remaining, done = [], 0
    for w in work:
        src, rr = w["source"], w["resref"]
        outp = os.path.join(HERE, "translated", src, f"{rr}.json")
        inp = os.path.join(HERE, "convos", src, f"{rr}.json")
        need = len(json.load(open(inp))["lines"]) if os.path.exists(inp) else 1
        ok = False
        if os.path.exists(outp):
            try:
                d = json.load(open(outp))
                got = sum(1 for v in d.values() if isinstance(v, str) and v.strip())
                ok = got >= need and need > 0
            except Exception:
                ok = False
        if ok:
            done += 1
        else:
            remaining.append(w)
    base = os.path.splitext(os.path.basename(man))[0]
    outm = os.path.join(HERE, "manifests", f"{base}_remaining.json")
    json.dump(remaining, open(outm, "w"), ensure_ascii=False)
    print(f"{base}: done={done} remaining={len(remaining)} -> {outm}")


if __name__ == "__main__":
    main()
