#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
next_chunk.py [N] - emit a manifest of the next N not-yet-translated conversations
(default 450, kept under the 1000-agent workflow cap). Idempotent: a conversation
is "done" when its output file has a non-empty RU for >= its line count. Writes
context/manifests/next.json and prints remaining totals.
"""
import os, sys, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 450
    remaining = []
    for inp in sorted(glob.glob(os.path.join(HERE, "convos", "*", "*.json"))):
        src = os.path.basename(os.path.dirname(inp))
        rr = os.path.splitext(os.path.basename(inp))[0]
        need = len(json.load(open(inp))["lines"])
        outp = os.path.join(HERE, "translated", src, f"{rr}.json")
        ok = False
        if os.path.exists(outp):
            try:
                d = json.load(open(outp))
                ok = sum(1 for v in d.values() if isinstance(v, str) and v.strip()) >= need
            except Exception:
                ok = False
        if not ok:
            remaining.append({"source": src, "resref": rr})
    chunk = remaining[:n]
    outm = os.path.join(HERE, "manifests", "next.json")
    json.dump(chunk, open(outm, "w"), ensure_ascii=False)
    print(f"remaining={len(remaining)}  next_chunk={len(chunk)}  -> {outm}")


if __name__ == "__main__":
    main()
