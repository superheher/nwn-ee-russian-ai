#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
finalize_workshop.py - thumbnails, tags and descriptions for the hak-based Workshop items.

WorkshopUpload itself only reads thumbnail.png; the description texts are written next to
the item so they can be pasted into the item's Steam page.
"""
import os, sys, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PROOT = os.path.dirname(HERE)
OLD = os.path.join(PROOT, "build", "workshop")     # previous items - reuse thumbnails
NEW = os.path.join(PROOT, "build", "workshop2")

JOURNALS = "AI Russian Text Journals"
BASE = "AI Russian Text Translation"

# item -> (DLC name for the description, required DLC, extra RU note, extra EN note)
DLC = {
    "AI Russian Text Darkness over Daggerford": ("Darkness over Daggerford", "", ""),
    "AI Russian Text Doom of Icewind Dale": ("Doom of Icewind Dale", "", ""),
    "AI Russian Text Tyrants of the Moonsea": ("Tyrants of the Moonsea", "", ""),
    "AI Russian Text Dark Dreams of Furiae": ("Dark Dreams of Furiae", "", ""),
    "AI Russian Text Pirates of the Sword Coast": ("Pirates of the Sword Coast", "", ""),
    "AI Russian Text Infinite Dungeons": ("Infinite Dungeons", "", ""),
    "AI Russian Text Wyvern Crown of Cormyr": ("Wyvern Crown of Cormyr", "", ""),
    "AI Russian Text Heroes of Neverwinter": (
        "Kingmaker",
        " Айтем покрывает все три приключения набора Kingmaker: Kingmaker, ShadowGuard и Witch's Wake.",
        " This item covers all three adventures of the Kingmaker pack: Kingmaker, ShadowGuard and Witch's Wake."),
}

DLC_RU = """Русскоязычный AI-перевод текста для дополнения «{name}» (Neverwinter Nights: Enhanced Edition).

Переведён весь отображаемый текст: диалоги, журнал заданий, названия и описания предметов, существ и областей, реплики катсцен, всплывающие сообщения и боевой фидбэк. Перевод выполнен с учётом контекста, терминологии Forgotten Realms и речевого регистра персонажей.{note}

Перевод доставляется внутрь хак-пака самого дополнения и применяется только к нему: оригинальная кампания и другие модули не затрагиваются. Запускайте приключение как обычно — из раздела «Премиум».

Требуется DLC «{name}». Перевод не является официальным и основан на оригинальном контенте Beamdog/BioWare."""

DLC_EN = """Russian AI text translation for the «{name}» adventure (Neverwinter Nights: Enhanced Edition).

Everything the player sees is translated: dialogue, quest journal, names and descriptions of items, creatures and areas, cutscene lines, floating text and combat feedback.{note}

The translation is delivered inside the adventure's own hakpak and applies to it alone - the original campaign and other modules are untouched. Launch the adventure as usual, from the Premium tab.

Requires the «{name}» DLC. Unofficial translation, based on original content by Beamdog/BioWare."""

BASE_RU = """Русскоязычный AI-перевод текста для Neverwinter Nights: Enhanced Edition — основная игра и официальные кампании (оригинальная кампания, Shadows of Undrentide, Hordes of the Underdark), интерфейс, а также бесплатные бонус-модули, входящие в игру.

Переведено: диалоги, журнал заданий, названия и описания предметов, заклинаний, классов, существ и областей, интерфейс, всплывающие сообщения и боевой фидбэк.

Примечание: в трёх бесплатных бонус-модулях («Сокровище Тёмного следопыта», «Ветра Эремора», «To Heir is Human») журнал заданий остаётся английским. Так устроен движок: журнал в NWN можно подменить только глобально, а это ломает журнал в пользовательских модулях. Кому нужен и он — есть отдельный айтем «AI Russian Text Journals», обязательно прочитайте предупреждение в его описании.

Переводы платных дополнений — отдельными айтемами. Перевод не является официальным и основан на оригинальном контенте Beamdog/BioWare."""

BASE_EN = """Russian AI text translation for Neverwinter Nights: Enhanced Edition - the base game and official campaigns (Original Campaign, Shadows of Undrentide, Hordes of the Underdark), the interface, and the free bonus modules that ship with the game.

Translated: dialogue, quest journal, names and descriptions of items, spells, classes, creatures and areas, UI, floating text and combat feedback.

Note: in three free bonus modules (The Dark Ranger's Treasure, The Winds of Eremor, To Heir is Human) the quest journal stays English. That is an engine limitation - a module's journal can only be overridden globally, which breaks the journal in user modules. If you want it anyway, there is a separate «AI Russian Text Journals» item; please read the warning in its description.

Paid DLC translations are separate items. Unofficial translation, based on original content by Beamdog/BioWare."""

JRL_RU = """ВНИМАНИЕ: этот айтем ломает журнал заданий в пользовательских модулях. Читайте до конца.

Что он даёт: русский журнал заданий в бесплатных бонус-модулях — The Dark Ranger's Treasure, The Winds of Eremor, To Heir is Human. Никаким другим способом их журнал перевести нельзя.

Почему так: файл журнала в NWN называется одинаково у всех модулей (module.jrl), и подменить его можно только глобально — для всех сразу. Поэтому айтем содержит объединённый журнал всего официального контента: оригинальная кампания, Shadows of Undrentide, Hordes of the Underdark, все восемь платных дополнений и бонус-модули — 597 категорий заданий.

ЦЕНА: пока вы подписаны, в любом ПОЛЬЗОВАТЕЛЬСКОМ модуле (Steam Workshop, Neverwinter Vault, в том числе кураторские — Aielund Saga, Eye of the Beholder, Siege of Shadowdale и прочие) журнал заданий будет писать «ERROR, blank journal entry». Отпишитесь перед тем, как играть в них.

Мелочь: в 16 записях официальные кампании используют одинаковые номера заданий (например, Wyvern Crown of Cormyr и The Winds of Eremor оба зовут главный квест MainPlot). В таких записях показаны оба варианта с подписью, к какой кампании относится — читайте свою.

Перевод не является официальным и основан на оригинальном контенте Beamdog/BioWare."""

JRL_EN = """WARNING: this item breaks the quest journal in user modules. Please read to the end.

What it gives you: a Russian quest journal in the free bonus modules - The Dark Ranger's Treasure, The Winds of Eremor, To Heir is Human. There is no other way to translate their journal.

Why: every module's journal file has the same name (module.jrl), so it can only be overridden globally - for all modules at once. Hence this item ships a merged journal of all official content: the Original Campaign, Shadows of Undrentide, Hordes of the Underdark, all eight paid adventures and the bonus modules - 597 quest categories.

THE COST: while you are subscribed, ANY user module (Steam Workshop, Neverwinter Vault, including curated ones - Aielund Saga, Eye of the Beholder, Siege of Shadowdale and others) will show "ERROR, blank journal entry" in the journal. Unsubscribe before playing them.

Detail: in 16 entries the official campaigns reuse the same quest IDs (Cormyr and The Winds of Eremor both call their main quest MainPlot). Those entries show both versions, each labelled with the campaign it belongs to - read your own.

Unofficial translation, based on original content by Beamdog/BioWare."""


def main():
    for item in sorted(os.listdir(NEW)):
        src, dst = os.path.join(OLD, item), os.path.join(NEW, item)
        if not os.path.isdir(dst):
            continue
        open(os.path.join(dst, "tags.txt"), "w").write("override\n")

        # hand-made cover (assets/thumbs) wins; then the previous item's; then the base one
        custom = os.path.join(PROOT, "assets", "thumbs", item + ".png")
        thumb = next((p for p in (custom, os.path.join(src, "thumbnail.png"),
                                  os.path.join(OLD, BASE, "thumbnail.png")) if os.path.exists(p)), None)
        if thumb:
            out = os.path.join(dst, "thumbnail.png")
            subprocess.run(["sips", "-Z", "512", "-s", "format", "png", thumb, "--out", out],
                           check=True, capture_output=True)

        # the base item's description is hand-written (full module-by-module breakdown) - keep it
        if item == BASE and os.path.exists(os.path.join(dst, "description_ru.txt")):
            sz = sum(os.path.getsize(os.path.join(r, f)) for r, _d, fs in os.walk(dst) for f in fs)
            print(f"{item:<46} {'development/':<14} {sz/1e6:>7.0f} MB  (описание не трогаю)")
            continue

        if item == BASE:
            ru, en = BASE_RU, BASE_EN
        elif item == JOURNALS:
            ru, en = JRL_RU, JRL_EN
        elif item in DLC:
            name, nru, nen = DLC[item]
            ru = DLC_RU.format(name=name, note=nru)
            en = DLC_EN.format(name=name, note=nen)
        else:
            print(f"!! {item}: no description template")
            continue
        open(os.path.join(dst, "description_ru.txt"), "w").write(ru + "\n")
        open(os.path.join(dst, "description_en.txt"), "w").write(en + "\n")

        sz = sum(os.path.getsize(os.path.join(r, f)) for r, _d, fs in os.walk(dst) for f in fs)
        payload = "hak/" if os.path.isdir(os.path.join(dst, "hak")) else "development/"
        print(f"{item:<46} {payload:<14} {sz/1e6:>7.0f} MB")


if __name__ == "__main__":
    main()
