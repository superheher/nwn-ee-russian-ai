#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_translated.py - deterministic QA gate over translated/**/*.json.

For every translated StrRef compares the Russian against the English source in
the tlk: tag (<...>) integrity, printf placeholders, newline count, non-empty,
and a leftover-English heuristic. Prints a per-scope summary and sample issues,
and overall coverage vs the 107,745 translatable strings.

  validate_translated.py [scope-substring]   limit to files whose path contains it
"""
import os, sys, json, re, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nwn

TAG = re.compile(r"<[^>\n]+>")
PH = re.compile(r"%[-+ 0-9.]*[sdifcuxXeg%]")
CYR = re.compile(r"[А-Яа-яЁё]")
LAT = re.compile(r"[A-Za-z]{4,}")


def keep_tags(s):
    # identifier tokens must be preserved; gender-fork tokens (<man/woman>,
    # <he/she>, ...) render an English word and are meant to be replaced in RU.
    return sorted(t for t in TAG.findall(s) if "/" not in t)


def issues_for(en, ru):
    out = []
    if not ru or not ru.strip():
        return ["empty"]
    if keep_tags(en) != keep_tags(ru):
        out.append(f"tags EN{keep_tags(en)} vs RU{keep_tags(ru)}")
    if sorted(PH.findall(en)) != sorted(PH.findall(ru)):
        out.append(f"placeholders EN{PH.findall(en)} vs RU{PH.findall(ru)}")
    if en.count("\n") != ru.count("\n"):
        out.append(f"newlines EN{en.count(chr(10))} vs RU{ru.count(chr(10))}")
    if ru == en and LAT.search(en) and en != en.upper() and not CYR.search(en):
        out.append("untranslated (RU==EN)")
    return out


def main():
    scope = sys.argv[1] if len(sys.argv) > 1 else ""
    tlk = nwn.load_tlk(os.path.join(HERE, "..", "backup", "english", "dialog.tlk"))
    files = sorted(glob.glob(os.path.join(HERE, "translated", "**", "*.json"),
                             recursive=True))
    files = [f for f in files if scope in f]

    seen, bad, samples = set(), 0, []
    per_scope = {}
    for p in files:
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            print(f"  ! bad json {p}: {e}"); continue
        scope_key = os.path.relpath(os.path.dirname(p), os.path.join(HERE, "translated"))
        ps = per_scope.setdefault(scope_key, {"n": 0, "bad": 0})
        pairs = d.items() if isinstance(d, dict) else []
        for k, v in pairs:
            if not str(k).lstrip("-").isdigit():
                continue
            sr = int(k)
            ru = v.get("ru") if isinstance(v, dict) else v
            if not isinstance(ru, str):
                continue
            seen.add(sr)
            ps["n"] += 1
            en = tlk(sr)
            iss = issues_for(en, ru)
            if iss:
                bad += 1; ps["bad"] += 1
                if len(samples) < 25:
                    samples.append((sr, en[:50], ru[:50], iss[0]))

    print(f"files: {len(files)}  translated strrefs: {len(seen)}  with-issues: {bad}")
    print("\nper scope:")
    for k in sorted(per_scope):
        s = per_scope[k]
        print(f"  {k:<24} n={s['n']:<6} issues={s['bad']}")
    if samples:
        print("\nsample issues:")
        for sr, en, ru, why in samples:
            print(f"  @{sr} [{why}]  EN={en!r}  RU={ru!r}")
    cov = json.load(open(os.path.join(HERE, "coverage.json")))
    tot = cov["translatable_total"]
    print(f"\ncoverage: {len(seen)}/{tot} ({100*len(seen)/tot:.1f}%)")


if __name__ == "__main__":
    main()
