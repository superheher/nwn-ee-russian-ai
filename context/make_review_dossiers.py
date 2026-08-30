#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_review_dossiers.py - turn the audit reports into per-character review files.

One JSON per name: our spellings with counts, plus every line the name appears
in (English, ours, and the 1C-derived reference), so a reviewer can pick the
canonical spelling and see the damage. Same for the gender audit.

  make_review_dossiers.py --names audit_names.json --gender audit_gender.json --out DIR
"""
import os, re, sys, json, argparse, difflib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tlkutil
import audit_names as an

MAX_LINES = 60


def snippet(text, form, pad=70):
    """The name in its immediate context - enough to judge, cheap to read."""
    i = text.find(form) if form else -1
    if i < 0:
        return text[:2 * pad]
    a, b = max(0, i - pad), min(len(text), i + len(form) + pad)
    return ("..." if a else "") + text[a:b] + ("..." if b < len(text) else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", required=True)
    ap.add_argument("--gender", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    en, ru, ref = tlkutil.load_all()
    names = json.load(open(args.names, encoding="utf-8"))
    gender = json.load(open(args.gender, encoding="utf-8"))
    mined = {}
    for ln in open(os.path.join(tlkutil.HERE, "..", "glossary", "mined_glossary.tsv"),
                   encoding="utf-8"):
        p = ln.rstrip("\n").split("\t")
        if len(p) == 2:
            mined.setdefault(p[0].strip(), p[1].strip())

    ndir = os.path.join(args.out, "names"); os.makedirs(ndir, exist_ok=True)
    gdir = os.path.join(args.out, "gender"); os.makedirs(gdir, exist_ok=True)

    def line(i):
        return {"strref": i, "en": en[i], "ru": ru[i], "ru_1c": ref[i].strip()}

    index = {"names": [], "gender": []}
    for n, d in names.items():
        rx = re.compile(r"\b" + re.escape(n) + r"\b")
        tag = d["tag_ru"]
        rival, canon = [], []
        for i, e in enumerate(en):
            if not e or not rx.search(e) or not ru[i]:
                continue
            forms = [c for c in tlkutil.CYR_WORD.findall(ru[i])
                     if c[:4].lower() == tag[:4].lower()
                     or (len(c) >= 5 and difflib.SequenceMatcher(
                         None, tlkutil.translit(c), n.lower()).ratio() >= 0.60)]
            if not forms:
                continue
            odd = [f for f in forms if an.stem(f) != an.stem(tag)]
            (rival if odd else canon).append((i, odd[0] if odd else forms[0]))
        payload = {"en": n, "tag_ru": tag, "tag_strref": d["tag_strref"],
                   "ru_1c_at_tag": d["ref_1c"], "mined_glossary": mined.get(n),
                   "groups": d["groups"],
                   "occurrences_other_spelling": [
                       {"strref": i, "form": f, "en": snippet(en[i], n),
                        "ru": snippet(ru[i], f), "ru_1c": snippet(ref[i].strip(), "")}
                       for i, f in rival[:MAX_LINES]],
                   "occurrences_tag_spelling": [
                       {"strref": i, "form": f, "ru": snippet(ru[i], f)}
                       for i, f in canon[:8]],
                   "n_rival_lines": len(rival), "n_tag_lines": len(canon)}
        json.dump(payload, open(os.path.join(ndir, f"{n}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        index["names"].append({"en": n, "tag_ru": tag, "rival_lines": len(rival),
                               "tag_lines": len(canon)})

    for n, d in gender.items():
        payload = {"en": n, "tag_ru": d["tag_ru"], "english_gender": d["english_gender"],
                   "en_votes": d["en_votes"],
                   "english_evidence": [line(i) for i in d["en_samples"]],
                   "own_lines_masc": [line(i) for i in d["self_m"]],
                   "own_lines_fem": [line(i) for i in d["self_f"]],
                   "about_them_masc": [line(i) for i in d["third_m"]],
                   "about_them_fem": [line(i) for i in d["third_f"]]}
        json.dump(payload, open(os.path.join(gdir, f"{n}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        index["gender"].append({"en": n, "tag_ru": d["tag_ru"],
                                "english_gender": d["english_gender"],
                                "self": [len(d["self_m"]), len(d["self_f"])],
                                "third": [len(d["third_m"]), len(d["third_f"])]})
    json.dump(index, open(os.path.join(args.out, "index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"names dossiers: {len(index['names'])}, gender dossiers: {len(index['gender'])}"
          f"  -> {args.out}")


if __name__ == "__main__":
    main()
