#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_fixes.py - apply reviewed consistency fixes back into translated/**.json.

Reads the decision files a review pass produced (name normalisation, gender
fixes, UI labels, Prelude sweep, plus the verifiers' rejections) and edits the
source translations - never the built tlk, so a rebuild keeps the fixes.

Every edit is validated first: engine tokens (<FirstName> ...) must survive, the
text must be CP1251-encodable, a full-line replacement must stay close to the
original, and a name form must really be there. Anything that fails is reported
and skipped.

  apply_fixes.py --decisions DIR [--manual FILE] [--dry-run] [--report PATH]
"""
import os, re, sys, json, glob, argparse, difflib, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tlkutil

TOKEN = re.compile(r"<[^<>\n]{1,40}>")
MIN_SIMILARITY = 0.55


def tokens(t):
    return sorted(TOKEN.findall(t))


def validate(old, new, source, full_line):
    """-> (new_text, problem or None); may repair whitespace the reviewer dropped."""
    if new == old:
        return None, "no change"
    if tokens(new) != tokens(old):
        return None, f"engine tokens changed: {tokens(old)} -> {tokens(new)}"
    try:
        new.encode("cp1251")
    except UnicodeEncodeError as e:
        return None, f"not CP1251-encodable: {e}"
    lead = len(old) - len(old.lstrip()), len(new) - len(new.lstrip())
    if lead[0] and not lead[1]:
        new = old[:lead[0]] + new
    tail_old = old[len(old.rstrip()):]
    if tail_old and not new.endswith(tail_old):
        new = new.rstrip() + tail_old
    if full_line and difflib.SequenceMatcher(None, old, new).ratio() < MIN_SIMILARITY:
        return None, "rewrites the line instead of fixing it"
    return new, None


def load_decisions(ddir):
    """-> (full_line changes, name form changes, rejections)"""
    full, names = [], []
    reject_strrefs, reject_forms = set(), set()

    v = os.path.join(ddir, "verdict_rest.json")
    if os.path.exists(v):
        for r in json.load(open(v, encoding="utf-8")).get("rejected", []):
            if isinstance(r, dict) and r.get("strref") is not None:
                reject_strrefs.add(int(r["strref"]))
    v = os.path.join(ddir, "verdict_names.json")
    if os.path.exists(v):
        for r in json.load(open(v, encoding="utf-8")).get("rejected", []):
            if not isinstance(r, dict):
                continue
            for sr in (r.get("strrefs") or [None]):
                reject_forms.add((r.get("en"), r.get("from"), sr))

    for p in sorted(glob.glob(os.path.join(ddir, "names_*.json"))):
        for d in json.load(open(p, encoding="utf-8")).get("decisions", []):
            if d.get("verdict") != "fix" or not d.get("form_map"):
                continue
            fmap = [(f["from"], f["to"]) for f in d["form_map"]
                    if f.get("from") and f.get("to")]
            for sr in d.get("strrefs", []):
                names.append({"strref": int(sr), "en": d["en"], "map": fmap,
                              "source": os.path.basename(p), "why": d.get("note", "")})
            if d.get("change_tag") and d.get("canon_ru"):
                names.append({"strref": int(d["tag_strref"]) if d.get("tag_strref") else None,
                              "en": d["en"], "map": fmap, "tag": d["canon_ru"],
                              "source": os.path.basename(p), "why": "name tag"})

    for p in sorted(glob.glob(os.path.join(ddir, "gender_*.json"))):
        for c in json.load(open(p, encoding="utf-8")).get("characters", []):
            for f in c.get("fixes", []):
                full.append({"strref": int(f["strref"]), "new": f["new_ru"],
                             "source": os.path.basename(p),
                             "why": f"{c['en']}: {f.get('why', '')}"})
    p = os.path.join(ddir, "ui.json")
    if os.path.exists(p):
        for f in json.load(open(p, encoding="utf-8")).get("fixes", []):
            full.append({"strref": int(f["strref"]), "new": f["new_ru"],
                         "source": "ui.json", "why": f.get("why", "")})
    for p in sorted(glob.glob(os.path.join(ddir, "prelude_*.json"))):
        for f in json.load(open(p, encoding="utf-8")).get("findings", []):
            if f.get("new_ru"):
                full.append({"strref": int(f["strref"]), "new": f["new_ru"],
                             "source": os.path.basename(p),
                             "why": f"{f.get('kind')}: {f.get('why', '')}"})
    p = os.path.join(ddir, "manual.json")
    if os.path.exists(p):
        for sr, new in json.load(open(p, encoding="utf-8")).items():
            full.append({"strref": int(sr), "new": new, "source": "manual.json",
                         "why": "hand fix"})
    return full, names, reject_strrefs, reject_forms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions", required=True)
    ap.add_argument("--manual")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", default=os.path.join(tlkutil.HERE, "fix_report.json"))
    a = ap.parse_args()

    en, ru, ref = tlkutil.load_all()
    owner = tlkutil.strref_owner()
    full, names, rej_sr, rej_forms = load_decisions(a.decisions)
    if a.manual:
        for sr, new in json.load(open(a.manual, encoding="utf-8")).items():
            full.append({"strref": int(sr), "new": new, "source": os.path.basename(a.manual),
                         "why": "hand fix"})

    text = {}                                   # strref -> current working text
    applied, skipped = [], []

    def current(sr):
        return text.get(sr, ru[sr] if 0 <= sr < len(ru) else None)

    for ch in full:                              # whole-line edits first
        sr = ch["strref"]
        old = current(sr)
        if old is None:
            skipped.append({**ch, "why_skipped": "unknown strref"}); continue
        if sr in rej_sr:
            skipped.append({**ch, "why_skipped": "rejected by verifier"}); continue
        new, problem = validate(old, ch["new"], ch["source"], full_line=True)
        if problem:
            skipped.append({**ch, "why_skipped": problem, "old": old}); continue
        text[sr] = new
        applied.append({"strref": sr, "old": old, "new": new, "source": ch["source"],
                        "why": ch["why"], "kind": "line"})

    for ch in names:                             # then surgical name replacements
        sr = ch["strref"]
        if sr is None:
            continue
        old = current(sr)
        if old is None:
            skipped.append({**ch, "why_skipped": "unknown strref"}); continue
        new = old
        used = []
        for frm, to in ch["map"]:
            if (ch["en"], frm, sr) in rej_forms or (ch["en"], frm, None) in rej_forms:
                continue
            rx = re.compile(r"(?<![А-Яа-яЁёA-Za-z])" + re.escape(frm) +
                            r"(?![А-Яа-яЁёA-Za-z])")
            if rx.search(new):
                new = rx.sub(to, new)
                used.append(f"{frm}->{to}")
        if not used:
            skipped.append({**ch, "why_skipped": "no listed form found", "old": old})
            continue
        new2, problem = validate(old, new, ch["source"], full_line=False)
        if problem:
            skipped.append({**ch, "why_skipped": problem, "old": old}); continue
        text[sr] = new2
        applied.append({"strref": sr, "old": old, "new": new2, "source": ch["source"],
                        "why": f"{ch['en']}: {', '.join(used)}", "kind": "name"})

    by_file = collections.defaultdict(dict)
    orphans = []
    for sr, new in text.items():
        p = owner.get(sr)
        if p:
            by_file[p][sr] = new
        else:
            orphans.append(sr)
    print(f"edits: {len(text)} strings in {len(by_file)} files "
          f"({len(applied)} applied, {len(skipped)} skipped)")
    if orphans:
        print(f"  ! {len(orphans)} strings have no source json: {orphans[:10]}")

    if not a.dry_run:
        for p, upd in by_file.items():
            d = json.load(open(p, encoding="utf-8"))
            if isinstance(d, dict) and isinstance(d.get("translations"), list):
                for t in d["translations"]:
                    if int(t.get("strref", -1)) in upd:
                        t["ru"] = upd[int(t["strref"])]
            else:
                for sr, new in upd.items():
                    k = str(sr)
                    if isinstance(d.get(k), dict):
                        d[k]["ru"] = new
                    else:
                        d[k] = new
            json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False,
                      separators=(",", ":"))
        print(f"written: {len(by_file)} translated json files")

    json.dump({"applied": applied, "skipped": skipped,
               "files": {os.path.relpath(p, tlkutil.HERE): len(u) for p, u in by_file.items()}},
              open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"report -> {a.report}")


if __name__ == "__main__":
    main()
