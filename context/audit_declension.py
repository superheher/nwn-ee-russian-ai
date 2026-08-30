#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_declension.py - masculine names left in the nominative after a preposition.

"поговорить с Элинвид" is wrong Russian: a male name ending in a consonant must
decline ("с Элинвидом"). A female name ending in a consonant must NOT ("с Арибет"),
so gender decides, and gender comes from the English text (he/she near the name).

  audit_declension.py [--gender-map FILE] [--out report.json]
"""
import os, re, sys, json, argparse, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tlkutil
import audit_gender as ag

# preposition -> case it governs -> ending for a masculine consonant-stem name
CASE = {"с": "inst", "со": "inst", "над": "inst", "под": "inst", "перед": "inst",
        "между": "inst", "к": "dat", "ко": "dat", "о": "prep", "об": "prep",
        "обо": "prep", "при": "prep", "у": "gen", "от": "gen", "для": "gen",
        "из": "gen", "без": "gen",
        "против": "gen", "около": "gen"}
HUSH = "жчшщц"
# low-INT "cave speech" deliberately keeps names undeclined - not a bug
CAVE = re.compile(r"\b(моя|твоя|тебя быть|твоё|евоный)\b|\bбыть\b\s|\bхотеть\b", re.I)


def decline(name, case):
    soft = name[-1] in "ьй"
    base = name[:-1] if soft else name
    if case == "gen" or case == "acc":
        return base + ("я" if soft else "а")
    if case == "dat":
        return base + ("ю" if soft else "у")
    if case == "inst":
        if soft:
            return base + "ем"
        return base + ("ем" if name[-1] in HUSH else "ом")
    if case == "prep":
        return base + "е"
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gender-map", help="json {EnglishName: 'm'|'f'} to override the "
                                         "gender guessed from the English text")
    ap.add_argument("--out", default=os.path.join(tlkutil.HERE, "audit_declension.json"))
    a = ap.parse_args()
    en, ru, ref = tlkutil.load_all()
    tags = ag.name_tags(en, ru)

    votes = collections.defaultdict(lambda: [0, 0])
    rx = re.compile(r"\b(" + "|".join(sorted(tags, key=len, reverse=True)) + r")\b")
    for i, e in enumerate(en):
        if not e:
            continue
        names = set(rx.findall(e))
        if len(names) != 1:
            continue
        n = names.pop()
        votes[n][0] += len(ag.EN_M.findall(e))
        votes[n][1] += len(ag.EN_F.findall(e))
    gender = {n: ("m" if v[0] >= 3 and v[0] > 3 * v[1] else
                  "f" if v[1] >= 3 and v[1] > 3 * v[0] else None)
              for n, v in votes.items()}
    if a.gender_map:
        gender.update(json.load(open(a.gender_map, encoding="utf-8")))

    male_names = {tags[n][0]: n for n, g in gender.items()
                  if g == "m" and n in tags and re.search(r"[бвгджзйклмнпрстфхцчшщь]$",
                                                          tags[n][0].lower())}
    if not male_names:
        print("no declinable male names identified"); return
    prep = re.compile(r"(?<![А-Яа-яЁё])((?i:" +
                      "|".join(sorted(CASE, key=len, reverse=True)) + r"))\s+(" +
                      "|".join(re.escape(t) for t in male_names) + r")(?![А-Яа-яЁё])")
    out = []
    for i, r in enumerate(ru):
        if not r:
            continue
        for m in prep.finditer(r):
            p, name = m.group(1).lower(), m.group(2)
            case = CASE[p]
            out.append({"strref": i, "en_name": male_names[name], "name": name,
                        "preposition": p, "case": case,
                        "cave_speech": bool(CAVE.search(r)),
                        "suggest": decline(name, case),
                        "en": en[i][:200], "ru": r[:240], "ru_1c": ref[i].strip()[:240]})
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    real = [d for d in out if not d["cave_speech"]]
    print(f"undeclined male names after a preposition: {len(out)} "
          f"({len(real)} outside low-INT speech) -> {a.out}")
    for d in real[:15]:
        print(f"  @{d['strref']} {d['preposition']} {d['name']} -> {d['suggest']}"
              f"   | {d['ru'][:90]}")


if __name__ == "__main__":
    main()
