#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mine_glossary.py - build an EN->RU term base for the NWN:EE translation.

Source: the aligned bilingual corpus we already have locally -
  English  : the game's dialog.tlk          (strref N -> English text)
  Russian  : the russifier's dialog.tlk_RU.txt (line N -> Russian text, CP1251)
Line N corresponds to strref N (verified), so each pair is an exact alignment.

Outputs:
  anchors.txt        - strrefs 0..60 (EN | RU) to eyeball the class/race blocks
  core_glossary.tsv  - canonical D&D terms looked up by their exact English string
  mined_glossary.tsv - all short, clean EN->RU term pairs (broad lexicon)
"""
import os, re, struct, sys, collections

def parse_en(path):
    d = open(path, "rb").read()
    cnt = struct.unpack_from("<I", d, 12)[0]
    eo  = struct.unpack_from("<I", d, 16)[0]
    out = {}
    for i in range(cnt):
        b = 20 + i*40
        flags = struct.unpack_from("<I", d, b)[0]
        if not flags & 1:
            continue
        off = struct.unpack_from("<I", d, b+28)[0]
        sz  = struct.unpack_from("<I", d, b+32)[0]
        out[i] = d[eo+off:eo+off+sz].decode("cp1252", "replace")
    return out

def read_ru(path):
    raw = open(path, "rb").read().split(b"\r\n")
    return {i: raw[i].decode("cp1251", "replace") for i in range(len(raw))}

# A short, clean term: no tags/newlines/format specifiers, mostly a name/phrase.
TERM_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 ,'/().+\-]{0,38}$")
def is_term(en):
    if not en or len(en) > 40:
        return False
    if "\n" in en or "<" in en or "%" in en or "\\" in en:
        return False
    return bool(TERM_RE.match(en)) and any(c.isalpha() for c in en)

# Canonical NWN / D&D vocabulary to pin down with high confidence.
CORE = {
    "Ability scores": ["Strength","Dexterity","Constitution","Intelligence","Wisdom","Charisma"],
    "Classes": ["Barbarian","Bard","Cleric","Druid","Fighter","Monk","Paladin","Ranger",
                "Rogue","Sorcerer","Wizard","Arcane Archer","Assassin","Blackguard",
                "Champion of Torm","Dwarven Defender","Harper Scout","Pale Master",
                "Shadowdancer","Shifter","Weapon Master","Red Dragon Disciple"],
    "Races": ["Dwarf","Elf","Gnome","Half-Elf","Half-Orc","Halfling","Human"],
    "Alignments": ["Lawful Good","Neutral Good","Chaotic Good","Lawful Neutral",
                   "True Neutral","Chaotic Neutral","Lawful Evil","Neutral Evil","Chaotic Evil"],
    "Saves": ["Fortitude","Reflex","Will"],
    "Schools": ["Abjuration","Conjuration","Divination","Enchantment","Evocation",
                "Illusion","Necromancy","Transmutation"],
    "Skills": ["Animal Empathy","Appraise","Bluff","Concentration","Disable Trap","Discipline",
               "Heal","Hide","Intimidate","Listen","Lore","Move Silently","Open Lock","Parry",
               "Perform","Persuade","Pick Pocket","Search","Set Trap","Spellcraft","Spot",
               "Taunt","Tumble","Use Magic Device"],
    "Core terms": ["Armor Class","Hit Points","Base Attack Bonus","Saving Throw","Spell Resistance",
                   "Experience","Level","Feat","Skill","Spell","Domain","Deity","Alignment",
                   "Damage Reduction","Attack Bonus","Initiative","Encumbrance"],
}

def main():
    en_path, ru_path, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    en = parse_en(en_path)
    ru = read_ru(ru_path)
    print(f"EN strings: {len(en)}, RU lines: {len(ru)}")

    # 1) anchors 0..60
    with open(os.path.join(outdir, "anchors.txt"), "w", encoding="utf-8") as f:
        for i in range(61):
            f.write(f"{i:4d}  {en.get(i,''):28s} | {ru.get(i,'')}\n")

    # index English text -> strref (first occurrence) for exact lookups
    en_index = {}
    for i, t in en.items():
        en_index.setdefault(t, i)

    # 2) core glossary by exact English lookup
    core_rows, missing = [], []
    with open(os.path.join(outdir, "core_glossary.tsv"), "w", encoding="utf-8") as f:
        f.write("category\ten\tru\tstrref\n")
        for cat, terms in CORE.items():
            for t in terms:
                i = en_index.get(t)
                if i is not None and ru.get(i):
                    f.write(f"{cat}\t{t}\t{ru[i]}\t{i}\n")
                    core_rows.append((cat, t, ru[i]))
                else:
                    missing.append(t)

    # 3) broad mined lexicon: short clean EN -> RU, deduped by EN
    seen = {}
    for i, t in en.items():
        if is_term(t) and ru.get(i) and ru[i].strip() and ru[i] != t:
            seen.setdefault(t, ru[i])
    with open(os.path.join(outdir, "mined_glossary.tsv"), "w", encoding="utf-8") as f:
        f.write("en\tru\n")
        for t in sorted(seen, key=str.lower):
            f.write(f"{t}\t{seen[t]}\n")

    print(f"core glossary: {len(core_rows)} terms (missing exact match: {len(missing)})")
    if missing:
        print("  not found exactly:", ", ".join(missing[:20]))
    print(f"mined lexicon: {len(seen)} term pairs")
    print("\n--- core sample ---")
    for cat, t, r in core_rows[:24]:
        print(f"  [{cat:12s}] {t:22s} -> {r}")

if __name__ == "__main__":
    main()
