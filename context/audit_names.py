#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_names.py - find proper names our translation spells more than one way.

A name gets a StrRef of its own in the tlk (the NPC/place name tag the player
sees). Every line whose English text mentions that name is then checked: which
Cyrillic word did we use there? Forms are grouped by stem, so declension is not
mistaken for drift; a name with two or more groups is a drift candidate.

  audit_names.py [--out report.json] [--min-lines 1]
"""
import os, re, sys, json, argparse, difflib, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tlkutil

ENDINGS = ("ами", "ями", "ому", "его", "ого", "ей", "ой", "ом", "ем", "ах",
           "ях", "ов", "ев", "ии", "ие", "ый", "ий", "ая", "ую", "а", "у",
           "ы", "е", "и", "о", "я", "ю", "ь")


def stem(word):
    w = word.lower()
    for e in ENDINGS:
        if len(w) - len(e) >= 3 and w.endswith(e):
            return w[:-len(e)]
    return w


def common_russian_words(ru, floor=5):
    """Lowercase words our own translation uses freely - a capitalised match on
    one of them is a sentence start, not a name."""
    c = collections.Counter()
    for s in ru:
        for m in re.finditer(r"[а-яё]{4,}", s):
            c[m.group(0)] += 1
    return {w for w, n in c.items() if n >= floor}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(tlkutil.HERE, "audit_names.json"))
    ap.add_argument("--min-lines", type=int, default=1)
    args = ap.parse_args()

    en, ru, ref = tlkutil.load_all()

    # words that also occur lowercase are common nouns, not names
    lowercase = set()
    for s in en:
        for m in re.finditer(r"[A-Za-z][a-z']+", s):
            if m.group(0)[0].islower():
                lowercase.add(m.group(0))

    tags = {}                                   # EN name -> (ru_tag, strref)
    for i, s in enumerate(en):
        t = s.strip()
        if (re.fullmatch(r"[A-Z][a-z]{2,15}", t) and t.lower() not in lowercase
                and re.fullmatch(r"[А-ЯЁ][а-яё\-]{2,18}", ru[i].strip())):
            tags.setdefault(t, (ru[i].strip(), i))
    print(f"name tags: {len(tags)}")

    common = common_russian_words(ru)
    rx = re.compile(r"\b(" + "|".join(sorted(tags, key=len, reverse=True)) + r")\b")
    seen = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    where = collections.defaultdict(lambda: collections.defaultdict(list))
    silent = collections.Counter()               # EN has the name, RU has no form of it
    for i, e in enumerate(en):
        if not e:
            continue
        names = set(rx.findall(e))
        if not names:
            continue
        r = ru[i]
        if not r or not re.search(r"[А-Яа-я]", r):
            continue
        cands = tlkutil.CYR_WORD.findall(r)
        for n in names:
            tag = tags[n][0]
            hit = False
            for c in cands:
                if c.lower() in common:
                    continue
                near_tag = len(c) >= 4 and c[:4].lower() == tag[:4].lower()
                near_en = (len(c) >= 5 and
                           difflib.SequenceMatcher(None, tlkutil.translit(c),
                                                   n.lower()).ratio() >= 0.60)
                if near_tag or near_en:
                    seen[n][stem(c)][c] += 1
                    if len(where[n][stem(c)]) < 6:
                        where[n][stem(c)].append(i)
                    hit = True
            if not hit:
                silent[n] += 1

    for n, groups in seen.items():                     # merge prefix-related stems
        stems = sorted(groups, key=len)
        for i, short in enumerate(stems):
            if short not in groups:
                continue
            for long in stems[i + 1:]:
                if long in groups and long.startswith(short) and len(long) - len(short) <= 3:
                    groups[short].update(groups.pop(long))
                    where[n][short] += where[n].pop(long, [])

    other_tags = {stem(t[0]): en_name for en_name, t in tags.items()}

    out = {}
    for n, groups in seen.items():
        tag, tag_ref = tags[n]
        total = sum(sum(c.values()) for c in groups.values())
        rivals = [st for st in groups
                  if st != stem(tag) and other_tags.get(st) in (None, n)]
        if not rivals or total < args.min_lines:
            continue
        out[n] = {
            "en": n,
            "tag_ru": tag,
            "tag_strref": tag_ref,
            "ref_1c": ref[tag_ref].strip(),
            "lines_without_the_name": silent[n],
            "groups": [
                {"stem": st,
                 "forms": dict(sorted(f.items(), key=lambda kv: -kv[1])),
                 "count": sum(f.values()),
                 "is_tag_spelling": st == stem(tag),
                 "is_another_name": other_tags.get(st) if other_tags.get(st) not in (None, n) else None,
                 "sample_strrefs": where[n][st]}
                for st, f in sorted(groups.items(), key=lambda kv: -sum(kv[1].values()))
            ],
        }
    out = dict(sorted(out.items(), key=lambda kv: -sum(g["count"] for g in kv[1]["groups"])))
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"names spelled more than one way: {len(out)}  -> {args.out}")
    for n, d in list(out.items())[:15]:
        print(f"  {n:14} tag={d['tag_ru']:14} " +
              " | ".join(f"{g['stem']}×{g['count']}" for g in d["groups"][:4]))


if __name__ == "__main__":
    main()
