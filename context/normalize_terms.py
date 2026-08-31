#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalize_terms.py - one spelling per recurring term, across the whole tlk.

Proper names are handled per name tag (audit_names.py); this covers the terms
that are phrases, adjectives or common nouns and drift the same way: the plague's
name, Aribeth's surname, the Waterdhavian adjective, the wererat.

Each rule may require an English condition, so "глубоководный" is only touched
where the English really says Waterdhavian. Output is a {strref: new line} file
for apply_fixes.py --manual, which validates every edit before writing.

  normalize_terms.py --out terms.json [--list]
"""
import os, re, sys, json, argparse, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tlkutil

B = r"(?<![А-Яа-яЁё])"

WD = {"ый": "ий", "ым": "им", "ых": "их", "ые": "ие", "ыми": "ими"}

RULES = [
    # the plague: Воющая Смерть, capitalised as the proper name it is
    {"name": "Wailing Death",
     "subs": [(B + r"([ВвСс])(?:опящ|тенающ|тонущ)(?=[а-яё]*\s+[Сс]мерт)",
               lambda m: ("В" if m.group(1) in "ВС" else "в") + "оющ"),
              (r"([Вв]оющ[а-яё]+\s+)смерт", lambda m: m.group(1) + "Смерт")]},
    # Aribeth de Tylmarande - one spelling, and the surname does not decline
    {"name": "de Tylmarande",
     "subs": [(B + r"Тил[ь]?маранд[а-яё]*", "Тильмаранд")]},
    # Waterdhavian, not deep-sea
    {"name": "Waterdhavian", "en": r"Waterdhavian",
     "subs": [(B + r"([Гг])лубоководн(ый|ым|ых|ые|ыми|ая|ой|ую|ое|ого|ому|ом)",
               lambda m: m.group(1) + "лубоководск" + WD.get(m.group(2), m.group(2)))]},
    # Waterdeep is Глубоководье here (the calque our name tags and 511 lines use)
    {"name": "Waterdeep",
     "subs": [(B + r"[ВУ]отердипа", "Глубоководья"), (B + r"[ВУ]отердипу", "Глубоководью"),
              (B + r"[ВУ]отердипом", "Глубоководьем"), (B + r"[ВУ]отердипе(?![а-яё])", "Глубоководье"),
              (B + r"[ВУ]отердип(?![а-яё])", "Глубоководье"),
              (B + r"([ВУ])отердипск", "Глубоководск"), (B + r"([ву])отердипск", "глубоководск"),
              (B + r"[ву]отердипц", "глубоководц"), (B + r"[ВУ]отердипц", "Глубоководц")]},
    # the monster is Крысооборотень in its own name string
    {"name": "Wererat",
     "subs": [(B + r"крысолюдов", "крысооборотней"), (B + r"крысолюды", "крысооборотни"),
              (B + r"крысолюдам", "крысооборотням"), (B + r"крысолюда", "крысооборотня"),
              (B + r"крысолюде", "крысооборотне"), (B + r"крысолюд", "крысооборотень"),
              (B + r"крыс[аы]-оборотн", "крысооборотн")]},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--list", action="store_true", help="print every line it would change")
    a = ap.parse_args()
    en, ru, ref = tlkutil.load_all()
    out, stat = {}, collections.Counter()
    for i, s in enumerate(ru):
        if not s:
            continue
        new = s
        touched = []
        for rule in RULES:
            if rule.get("en") and not re.search(rule["en"], en[i]):
                continue
            for pat, repl in rule["subs"]:
                new2 = re.sub(pat, repl, new)
                if new2 != new:
                    touched.append(rule["name"])
                    new = new2
        if new != s:
            out[str(i)] = new
            for t in set(touched):
                stat[t] += 1
            if a.list:
                print(f"@{i} [{', '.join(sorted(set(touched)))}]\n  - {s[:150]}\n  + {new[:150]}")
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"lines to change: {len(out)}  {dict(stat)}  -> {a.out}")


if __name__ == "__main__":
    main()
