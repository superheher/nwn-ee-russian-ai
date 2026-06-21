#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
assemble_tlk.py - build the Russian dialog.tlk from OUR translations.

Takes the pristine English dialog.tlk as the base and overlays every StrRef we
have translated (context/translated/**/*.json) as CP1251 text. Untranslated
StrRefs keep their English bytes, so a partial run yields a valid, installable
tlk (English where we have not translated yet). Reuses build_tlk's verified
TLK V3.0 reader/writer.

  --check   report translation coverage only (no write)
  --out P   output path (default ../build/dialog.tlk, where install_ru reads it)
"""
import os, sys, json, glob, argparse, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import build_tlk

EN_TLK = os.path.join(HERE, "..", "backup", "english", "dialog.tlk")
TRANSLATED = os.path.join(HERE, "translated")
OUT_DEFAULT = os.path.join(HERE, "..", "build", "dialog.tlk")


def load_translations(tdir):
    """Merge every translated/**/*.json into {strref:int -> ru:str}.
    Accepts {strref:ru}, {strref:{ru:..}}, or {translations:[{strref,ru}]}."""
    merged, conflicts, files = {}, [], 0
    for p in sorted(glob.glob(os.path.join(tdir, "**", "*.json"), recursive=True)):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            print(f"  ! skip {p}: {e}"); continue
        files += 1
        pairs = []
        if isinstance(d, dict) and "translations" in d and isinstance(d["translations"], list):
            for t in d["translations"]:
                if "strref" in t and t.get("ru"):
                    pairs.append((int(t["strref"]), t["ru"]))
        elif isinstance(d, dict):
            for k, v in d.items():
                if not k.lstrip("-").isdigit():
                    continue
                ru = v.get("ru") if isinstance(v, dict) else v
                if isinstance(ru, str) and ru:
                    pairs.append((int(k), ru))
        for sr, ru in pairs:
            if sr in merged and merged[sr] != ru:
                conflicts.append((sr, p))
            merged[sr] = ru
    return merged, conflicts, files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--english-tlk", default=EN_TLK)
    ap.add_argument("--translated", default=TRANSLATED)
    args = ap.parse_args()

    trans, conflicts, files = load_translations(args.translated)
    print(f"translations: {len(trans)} strrefs from {files} files; "
          f"conflicts: {len(conflicts)}")
    if conflicts[:5]:
        for sr, p in conflicts[:5]:
            print(f"  conflict @{sr} (kept last) <- {os.path.relpath(p, HERE)}")

    if args.check or not trans:
        # coverage vs the translatable universe
        cov_path = os.path.join(HERE, "coverage.json")
        if os.path.exists(cov_path):
            cov = json.load(open(cov_path))
            tot = cov["translatable_total"]
            print(f"coverage: {len(trans)}/{tot} "
                  f"({100*len(trans)/tot:.1f}%) translatable strings")
        if args.check:
            return

    print(f"reading English base: {args.english_tlk}")
    tlk = build_tlk.parse_tlk(args.english_tlk)
    applied = skipped = 0
    for sr, ru in trans.items():
        if 0 <= sr < len(tlk.entries):
            tlk.entries[sr]["text"] = ru.encode("cp1251", "replace")
            tlk.entries[sr]["flags"] |= 0x1
            applied += 1
        else:
            skipped += 1
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    build_tlk.write_tlk(tlk, args.out)
    print(f"applied={applied} out-of-range={skipped}  ->  {args.out} "
          f"({os.path.getsize(args.out):,} bytes)")

    # verify: re-parse and spot-check that our RU round-trips through CP1251
    chk = build_tlk.parse_tlk(args.out)
    assert len(chk.entries) == len(tlk.entries), "entry count changed!"
    ok = bad = 0
    for sr, ru in list(trans.items())[:2000]:
        got = chk.entries[sr]["text"].decode("cp1251", "replace")
        if got == ru.encode("cp1251", "replace").decode("cp1251", "replace"):
            ok += 1
        else:
            bad += 1
    print(f"verify: re-parsed {len(chk.entries)} entries; "
          f"sampled round-trip ok={ok} bad={bad}")


if __name__ == "__main__":
    main()
