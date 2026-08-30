#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_gender.py - find characters whose Russian gender contradicts itself.

Evidence per character:
  english     he/she words in English lines that mention only that name
  self        the character's own lines (conversation bound to the name by an
              "I am <Name>" / "my name is <Name>" line) using "я ... -л/-ла",
              "рад(а)", "должен/должна" and friends
  third       our Russian next to the name: a past-tense verb or a gendered noun
              within a few words of the name form

A character is reported when these disagree. Output feeds a review pass.

  audit_gender.py [--out report.json]
"""
import os, re, sys, json, glob, argparse, difflib, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tlkutil

EN_M = re.compile(r"\b(he|him|his|himself|brother|son|father|lord|sir|husband|"
                  r"king|uncle|nephew|guy|fellow)\b", re.I)
EN_F = re.compile(r"\b(she|her|hers|herself|sister|daughter|mother|lady|madam|"
                  r"wife|queen|aunt|niece|girl)\b", re.I)

BLOCK = r"(?:ты|вы|тебе|вам|он|она|оно|они|кто|каждый|любой|никто|тот|та)"
SELF_F = re.compile(r"\bя\s+(?:[а-яё]+\s+){0,2}[а-яё]{3,}ла\b|"
                    r"\b(рада|готова|должна|уверена|сама)\b")
SELF_M = re.compile(r"\bя\s+(?:[а-яё]+\s+){0,2}[а-яё]{3,}(?<![аеиоуыэюяьл])л\b|"
                    r"\b(рад|готов|должен|уверен|сам)\b(?!\w)")
THIRD_F = re.compile(r"\b([а-яё]{3,}ла|она|её|ей|сестра|дочь|мать|госпожа|жена|"
                     r"королева|женщина|леди|дева|жрица|чародейка|воительница)\b")
THIRD_M = re.compile(r"\b([а-яё]{3,}(?<![аеиоуыэюяьл])л|он|его|ему|брат|сын|отец|"
                     r"господин|муж|король|мужчина|лорд|сэр|жрец|воин|старик)\b")
WORD = re.compile(r"[А-Яа-яЁё]+")


def unblocked(text, m):
    """Drop a first-person marker that is really addressed at someone else
    ("ты должен")."""
    before = [w.strip(",.!?«»\"'-") for w in
              text[max(0, m.start() - 60):m.start()].lower().split()][-3:]
    return not any(re.fullmatch(BLOCK, w) for w in before)


def self_gender(text):
    g = set()
    for rx, tag in ((SELF_F, "f"), (SELF_M, "m")):
        for m in rx.finditer(text.lower()):
            if unblocked(text.lower(), m):
                g.add(tag)
                break
    return g


def name_tags(en, ru):
    lowercase = set()
    for s in en:
        for m in re.finditer(r"[A-Za-z][a-z']+", s):
            if m.group(0)[0].islower():
                lowercase.add(m.group(0))
    tags = {}
    for i, s in enumerate(en):
        t = s.strip()
        if (re.fullmatch(r"[A-Z][a-z]{2,15}", t) and t.lower() not in lowercase
                and re.fullmatch(r"[А-ЯЁ][а-яё\-]{2,18}", ru[i].strip())):
            tags.setdefault(t, (ru[i].strip(), i))
    return tags


def bind_conversations(en):
    """conversation resref -> the name the speaker gives ("I am X")."""
    intro = re.compile(r"\b(?:I am|my name is|I'm)\s+([A-Z][a-z]{2,15})\b")
    bound = {}
    for p in sorted(glob.glob(os.path.join(tlkutil.HERE, "dialogs", "*.json"))):
        for c in json.load(open(p, encoding="utf-8")).get("conversations", []):
            refs = [int(m.group(1)) for m in
                    re.finditer(r"\[NPC @(-?\d+)\]", c.get("script", ""))]
            names = collections.Counter()
            for sr in refs:
                if 0 <= sr < len(en):
                    for m in intro.finditer(en[sr]):
                        names[m.group(1)] += 1
            if names:
                bound[c["resref"]] = (names.most_common(1)[0][0],
                                      [r for r in dict.fromkeys(refs) if r >= 0])
    return bound


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(tlkutil.HERE, "audit_gender.json"))
    args = ap.parse_args()
    en, ru, ref = tlkutil.load_all()
    tags = name_tags(en, ru)
    rx = re.compile(r"\b(" + "|".join(sorted(tags, key=len, reverse=True)) + r")\b")

    dossier = collections.defaultdict(lambda: {
        "en_m": 0, "en_f": 0, "en_samples": [], "third_m": [], "third_f": [],
        "self_m": [], "self_f": []})

    # --- English truth + third-person Russian near the name --------------------
    for i, e in enumerate(en):
        if not e:
            continue
        names = set(rx.findall(e))
        if len(names) != 1:
            continue
        n = names.pop()
        d = dossier[n]
        m_hits, f_hits = EN_M.findall(e), EN_F.findall(e)
        d["en_m"] += len(m_hits); d["en_f"] += len(f_hits)
        if (m_hits or f_hits) and len(d["en_samples"]) < 6:
            d["en_samples"].append(i)
        r = ru[i]
        if not r:
            continue
        tag = tags[n][0]
        words = list(WORD.finditer(r))
        for k, w in enumerate(words):
            c = w.group(0)
            if not (c[:4].lower() == tag[:4].lower() or
                    (len(c) >= 5 and difflib.SequenceMatcher(
                        None, tlkutil.translit(c), n.lower()).ratio() >= 0.60)):
                continue
            near = " ".join(x.group(0).lower() for x in words[max(0, k - 2):k + 3])
            if THIRD_F.search(near) and len(d["third_f"]) < 8:
                d["third_f"].append(i)
            if THIRD_M.search(near) and len(d["third_m"]) < 8:
                d["third_m"].append(i)
            break

    # --- the character's own voice ---------------------------------------------
    for resref, (name, refs) in bind_conversations(en).items():
        if name not in dossier and name not in tags:
            continue
        d = dossier[name]
        for sr in refs:
            g = self_gender(ru[sr]) if sr < len(ru) else set()
            if "f" in g and len(d["self_f"]) < 10:
                d["self_f"].append(sr)
            if "m" in g and len(d["self_m"]) < 10:
                d["self_m"].append(sr)

    out = {}
    for n, d in dossier.items():
        en_g = ("m" if d["en_m"] >= 3 and d["en_f"] == 0 else
                "f" if d["en_f"] >= 3 and d["en_m"] == 0 else None)
        ru_m = bool(d["third_m"]) or bool(d["self_m"])
        ru_f = bool(d["third_f"]) or bool(d["self_f"])
        clash = ((ru_m and ru_f) or (en_g == "m" and ru_f and not ru_m)
                 or (en_g == "f" and ru_m and not ru_f))
        if not clash:
            continue
        out[n] = {"en": n, "tag_ru": tags.get(n, ("?", -1))[0],
                  "english_gender": en_g, "en_votes": [d["en_m"], d["en_f"]],
                  "en_samples": d["en_samples"], **{k: d[k] for k in
                  ("third_m", "third_f", "self_m", "self_f")}}
    out = dict(sorted(out.items(),
                      key=lambda kv: -(len(kv[1]["third_m"]) + len(kv[1]["third_f"])
                                       + len(kv[1]["self_m"]) + len(kv[1]["self_f"]))))
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"characters with contradictory gender evidence: {len(out)} -> {args.out}")
    for n, d in list(out.items())[:12]:
        print(f"  {n:14} tag={d['tag_ru']:14} EN={d['english_gender']} "
              f"self m/f={len(d['self_m'])}/{len(d['self_f'])} "
              f"3rd m/f={len(d['third_m'])}/{len(d['third_f'])}")


if __name__ == "__main__":
    main()
