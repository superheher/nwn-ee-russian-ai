#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_player_reports.py - apply the Workshop bug reports back into translated/**.

A player working through Chapter 1 reported: '?' inside words, two spellings of
Cyric, English skill-check labels in reply options, "Dwarven" as the <race>
token, a male NPC speaking as a woman, and the Waterdhavian creatures reading as
deep-sea beasts. Each report turned out to be a whole class, so the fixes are
rules, not one-off edits:

  chars    non-CP1251 characters (the assembler turns them into '?')
  labels   English <StartCheck>[Persuade]</Start> style option tags
  terms    Cyric, Beggar's Nest, Waterdeep adjective, Sword Coast Boys
  strrefs  per-string edits (race tokens, Jemanie's gender, single rewrites)

Edits go into the source translations, never the built tlk, so a rebuild keeps
them. Every edit is validated: engine tokens (<FirstName>, <CUSTOM100>, ...)
must survive and the result must encode to CP1251. Re-runnable - a second run
reports nothing left to do.

The same '?' also reached the DLC layer, whose ids are module-local, so the
character rules can be pointed at those trees on their own:

  fix_player_reports.py [--dry-run] [--report PATH]
  fix_player_reports.py --tree ../dlc/cormyr_hak/translated --chars-only
"""
import os, re, sys, json, glob, argparse, collections

HERE = os.path.dirname(os.path.abspath(__file__))
TRANSLATED = os.path.join(HERE, "translated")
TOKEN = re.compile(r"<[^<>\n]{1,40}>")
START = re.compile(r"(<Start[A-Za-z]*>)(.*?)(</Start>)")


# --- 1. characters the CP1251 writer cannot encode -------------------------

CHAR_MAP = {
    "́": "",       # combining acute - the '?' the player saw mid-word
    "ó": "о",  # Latin o-acute used as a stressed Cyrillic о
    "−": "-",      # minus sign
    "κ": "к",  # Greek kappa typo'd into серокожая
    "×": "x",      # multiplication sign in "Комната 2x2"
    "о?льш": "ольш",  # the same accent, already baked in as '?' by an earlier pass
}
# junk strings we copied verbatim from English; they have no CP1251 form and no
# meaning, so drop them and let the English bytes stand.
DROP = {3127, 3128, 3129, 3134}


# --- 2. English option labels left inside <Start...> tags ------------------

LABELS = {
    "[Persuade]": "[Убеждение]",
    "Persuade": "Убеждение",
    "[Difficult Persuade]": "[Сложное убеждение]",
    "[Persuade - lie]": "[Убеждение — ложь]",
    "[Persuade - Lie]": "[Убеждение — ложь]",
    "[Persuade/Lie]": "[Убеждение — ложь]",
    "[Persuade - Intimidate]": "[Убеждение — Запугивание]",
    "[Persuade - Flirt]": "[Убеждение — флирт]",
    "Persuade: Intimidate": "Убеждение: Запугивание",
    "Persuade: Bluff": "Убеждение: Обман",
    "Persuade:Bluff": "Убеждение: Обман",
    "[Insight]": "[Проницательность]",
    "[Прозрение]": "[Проницательность]",
    "[Lie]": "[Ложь]",
    "[Солгать]": "[Ложь]",
    "[Intimidate]": "[Запугивание]",
    "Intimidate": "Запугивание",
    "[Bluff]": "[Обман]",
    "Bluff": "Обман",
    "[Lore]": "[Знание]",
    "[Intelligence]": "[Интеллект]",
    "[Dexterity]": "[Ловкость]",
    "Success": "Успех",
    "Failure": "Провал",
    "[Failed]": "[Провал]",
    "[Неудача]": "[Провал]",
    "[Teleport]": "[Телепортация]",
    "[Flirt]": "[Флирт]",
    "[hic]": "[ик]",
    "[belch]": "[рыг]",
    "[Sob]": "[Всхлип]",
    "[sob]": "[всхлип]",
    "[Sigh]": "[Вздох]",
    "[sigh]": "[вздох]",
    "[Gasp]": "[Ахает]",
    "[Blushes]": "[Краснеет]",
    "[chuckle!]": "[Хихикает!]",
    "[mutter]": "[бормочет]",
    "(hushed)": "(вполголоса)",
    "(Hold up staff)": "(Показать посох)",
    "(Hold up Journal)": "(Показать дневник)",
    "[Cast Charm Person]": "[Прочитать «Очарование личности»]",
    "[Cast Charm]": "[Прочитать «Очарование»]",
    "[Use Minor Healing Spell]": "[Применить малое исцеляющее заклинание]",
    "[Kill him.]": "[Убить его.]",
    "[Kill her.]": "[Убить её.]",
    "[Take the sword.]": "[Взять меч.]",
    "Attack": "Напасть",
    "Attack.": "Напасть.",
    "Attack the apprentice.": "Напасть на ученика.",
    "Attack the Matron.": "Напасть на матрону.",
    "Attack the medusa.": "Напасть на медузу.",
    "Attack the merchant.": "Напасть на торговца.",
    "Give him the soul gem": "Отдать ему камень душ",
    "Tell Aghaaz about the Valsharess.": "Рассказать Агхаазу о Валшаресс.",
    "Tell Ferron about the Valsharess.": "Рассказать Феррону о Валшаресс.",
    "Automatic": "Автоматически",
    "Manual": "Вручную",
}


# --- 3. terms the player saw spelled two ways ------------------------------

def _waterdeep_rules():
    """The Waterdhavian creatures. 'глубоководский' reads as deep-sea, so the
    city goes behind the noun as 'из Глубоководья'; the quest's creatures also
    settle on one noun (существо), which is safe in the plural because Russian
    plural agreement carries no gender."""
    plural = {"тварей": "существ", "созданий": "существ", "существ": "существ",
              "зверей": "существ", "зверюг": "существ", "чудищ": "существ",
              "тварях": "существах", "созданиях": "существах",
              "существах": "существах", "тварям": "существам",
              "тварями": "существами", "существами": "существами",
              "твари": "существа", "создания": "существа", "существа": "существа"}
    rules = []
    for adj in ("глубоководских", "глубоководские", "глубоководскими",
                "глубоководским", "Глубоководских", "Глубоководские"):
        for noun, sub in plural.items():
            new = sub.capitalize() if adj[0] == "Г" else sub
            rules.append((f"{adj} {noun}", f"{new} из Глубоководья"))
    # singular: создание/существо are both neuter, so the swap is free
    rules += [
        ("глубоководское существо", "существо из Глубоководья"),
        ("глубоководское создание", "существо из Глубоководья"),
        ("глубоководского существа", "существа из Глубоководья"),
        ("глубоководского создания", "существа из Глубоководья"),
        ("глубоководским существом", "существом из Глубоководья"),
        ("глубоководским созданием", "существом из Глубоководья"),
        ("глубоководского существа", "существа из Глубоководья"),
        # 'тварь' is feminine and the rest of its sentence agrees with it, so
        # only the adjective moves
        ("глубоководская тварь", "тварь из Глубоководья"),
        ("глубоководскую тварь", "тварь из Глубоководья"),
        ("глубоководский твари", "твари из Глубоководья"),      # low-INT line
        # named specimens and the city's own things
        ("Глубоководская дриада", "Дриада из Глубоководья"),
        ("Глубоководский кокатрис", "Кокатрис из Глубоководья"),
        ("Глубоководская юань-ти", "Юань-ти из Глубоководья"),
        ("глубоководской юань-ти", "юань-ти из Глубоководья"),
        ("глубоководский пожиратель разума", "пожиратель разума из Глубоководья"),
        ("глубоководского пожирателя разума", "пожирателя разума из Глубоководья"),
        ("глубоководский полурослик", "полурослик из Глубоководья"),
        ("глубоководских воинов", "воинов Глубоководья"),
        ("глубоководского ополчения", "ополчения Глубоководья"),
        ("глубоководской тюрьмы", "тюрьмы в Глубоководье"),
        ("глубоководские вещицы Арибет", "вещицы Арибет из Глубоководья"),
        ("этих глубоководских-как-их-там тварей",
         "этих тварей из Глубоко-как-его-там"),
    ]
    # longest first so 'глубоководского пожирателя разума' wins over the generic
    return sorted(rules, key=lambda r: -len(r[0]))


TERMS = [
    # Cyric: 'Кирик' in 13 strings, 'Цирик' in 20; the community lexicon is Цирик
    ("Кирику", "Цирику"), ("Кирика", "Цирика"), ("Кириком", "Цириком"),
    ("Кирик", "Цирик"),
    # Beggar's Nest: six spellings across 227 lines - one district, one name
] + [(f"{bad} {tail}", f"{good} Нищих")
     for bad, good in (("Приют", "Гнездо"), ("Приюте", "Гнезде"),
                       ("Приюта", "Гнезда"), ("Приюту", "Гнезду"),
                       ("Приютом", "Гнездом"), ("Гнездо", "Гнездо"),
                       ("Гнезде", "Гнезде"), ("Гнезда", "Гнезда"),
                       ("Гнезду", "Гнезду"), ("Гнездом", "Гнездом"))
     for tail in ("Нищих", "нищих", "Нищего", "нищего")
] + [
    ("Нищенское Гнездо", "Гнездо Нищих"), ("Нищенском Гнезде", "Гнезде Нищих"),
    ("Нищенского Гнезда", "Гнезда Нищих"), ("Нищенскому Гнезду", "Гнезду Нищих"),
    ("Нищенского квартала", "Гнезда Нищих"), ("Нищенский квартал", "Гнездо Нищих"),
    # the gang is 'Парни с Побережья Мечей' - keep the 'с' everywhere
    ("Парней Побережья Мечей", "Парней с Побережья Мечей"),
    ("Парням Побережья Мечей", "Парням с Побережья Мечей"),
    ("Парнями Побережья Мечей", "Парнями с Побережья Мечей"),
    ("Парнях Побережья Мечей", "Парнях с Побережья Мечей"),
    ("Парни Побережья Мечей", "Парни с Побережья Мечей"),
] + _waterdeep_rules()


# --- 4. single strings -----------------------------------------------------

STRREFS = {
    # racialtypes.2da ConverName/ConverNameLower - this is the <race> token an
    # NPC speaks, so it has to be a noun ("Раса: Дворф"), not an adjective
    5583: ("Дворфский", "Дворф"), 5584: ("Эльфийский", "Эльф"),
    5586: ("Полуэльфийский", "Полуэльф"), 5588: ("дворфский", "дворф"),
    5589: ("эльфийский", "эльф"), 5590: ("полуэльфийский", "полуэльф"),
    # the zombie's name, same gang as the dialogue's 'Парни с Побережья Мечей'
    63147: ("Мальчишка с Побережья Мечей", "Парень с Побережья Мечей"),
    # 'горе́' (upward) is unreadable once the accent is gone
    78899: ("вознесли его горе", "вознесли его ввысь"),
    # Jemanie is Torin's brother; his lines and the lines aimed at him were
    # written as a woman's
    23339: ("Ты точно уверена", "Ты точно уверен"),
    23359: ("ты не отдала это", "ты не отдал это"),
    23368: ("Я хотела бы помочь его найти, но не уверена",
            "Я хотел бы помочь его найти, но не уверен"),
    23373: ("буду мертва", "буду мёртв"),
    23376: ("буду мертва", "буду мёртв"),
    23388: ("Сама я мало что могу", "Сам я мало что могу"),
    23393: ("Я бы отдала его тебе, но у меня его больше нет. Я уже отдала его",
            "Я бы отдал его тебе, но у меня его больше нет. Я уже отдал его"),
    23394: ("я бы уже его нашла", "я бы уже его нашёл"),
    23396: ("я бы начала оттуда", "я бы начал оттуда"),
    23397: ("я не привыкла", "я не привык"),
    23398: ("Я просто забыла", "Я просто забыл"),
    63008: ("Я ведь отдала тебе", "Я ведь отдал тебе"),
    63009: ("Хотела бы я помочь", "Хотел бы я помочь"),
}
STRREFS_EXTRA = {63008: ("совсем голову потеряла", "совсем голову потерял")}


# --- 3b. agreement left over by rule 3 -------------------------------------

POLISH = [
    # 'тварь' was feminine, 'существо' is neuter: "одна из существ" -> "одно ..."
    (re.compile(r"\b(О|о)дна(\s+из\s+(?:[А-Яа-яЁё]+\s+)?существ)"), r"\1дно\2"),
    # "одно из существ из Глубоководья" - one 'из' is enough
    (re.compile(r"(\bиз\s+(?:[А-Яа-яЁё]+\s+)?существ\w*)\s+из\s+Глубоководья"),
     r"\1 Глубоководья"),
]


def fix_chars(text):
    for bad, good in CHAR_MAP.items():
        text = text.replace(bad, good)
    return text


def fix_labels(text):
    def sub(m):
        return m.group(1) + LABELS.get(m.group(2), m.group(2)) + m.group(3)
    return START.sub(sub, text)


def fix_terms(text):
    for old, new in TERMS:
        if old in text:
            text = text.replace(old, new)
    return text


def fix_one(strref, text, chars_only=False):
    out = fix_chars(text)
    if chars_only:
        return out
    out = fix_labels(out)
    out = fix_terms(out)
    for rx, rep in POLISH:
        out = rx.sub(rep, out)
    for table in (STRREFS, STRREFS_EXTRA):
        pair = table.get(strref)
        if pair and pair[0] in out:
            out = out.replace(*pair)
    return out


def validate(old, new):
    if sorted(TOKEN.findall(new)) != sorted(TOKEN.findall(old)):
        return "engine tokens changed"
    try:
        new.encode("cp1251")
    except UnicodeEncodeError as e:
        return f"still not CP1251: {e}"
    if not new.strip():
        return "became empty"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tree", default=TRANSLATED,
                    help="translations root (default: the base game's)")
    ap.add_argument("--chars-only", action="store_true",
                    help="only the CP1251 character rules - for the DLC trees, "
                         "whose ids are module-local and not tlk StrRefs")
    ap.add_argument("--report", default=os.path.join(HERE, "player_report_fixes.json"))
    args = ap.parse_args()

    changes, problems, dropped = [], [], []
    for path in sorted(glob.glob(os.path.join(args.tree, "**", "*.json"), recursive=True)):
        d = json.load(open(path, encoding="utf-8"))
        if not isinstance(d, dict):
            continue
        rel = os.path.relpath(path, args.tree)
        touched = False
        for key in list(d):
            if not key.lstrip("-").isdigit():
                continue
            sr = int(key)
            val = d[key]
            old = val.get("ru") if isinstance(val, dict) else val
            if not isinstance(old, str) or not old:
                continue
            if sr in DROP and not args.chars_only:
                del d[key]
                dropped.append((sr, rel, old)); touched = True
                continue
            new = fix_one(sr, old, args.chars_only)
            if new == old:
                continue
            why = validate(old, new)
            if why:
                problems.append((sr, rel, why, old, new))
                continue
            if isinstance(val, dict):
                val["ru"] = new
            else:
                d[key] = new
            changes.append((sr, rel, old, new)); touched = True
        if touched and not args.dry_run:
            with open(path, "w", encoding="utf-8") as f:   # keep the compact
                json.dump(d, f, ensure_ascii=False,           # on-disk format
                          separators=(",", ":"))

    print(f"changed {len(changes)} strings, dropped {len(dropped)}, "
          f"skipped {len(problems)}" + ("  (dry run)" if args.dry_run else ""))
    by_file = collections.Counter(c[1].split(os.sep)[0] for c in changes)
    for k, n in by_file.most_common():
        print(f"  {n:>5}  {k}")
    for sr, rel, why, old, new in problems:
        print(f"  ! {sr} {rel}: {why}\n      {old[:90]!r}\n      {new[:90]!r}")
    json.dump({"changed": [{"strref": s, "file": f, "old": o, "new": n}
                           for s, f, o, n in changes],
               "dropped": [{"strref": s, "file": f, "text": t} for s, f, t in dropped],
               "skipped": [{"strref": s, "file": f, "why": w} for s, f, w, _, _ in problems]},
              open(args.report, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"report -> {os.path.relpath(args.report, HERE)}")


if __name__ == "__main__":
    main()
