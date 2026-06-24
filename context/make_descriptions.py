#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_descriptions.py - write RU + EN Steam Workshop descriptions (solid lines,
not hard-wrapped) into each item folder as description_ru.txt / description_en.txt.
NWN WorkshopUpload does NOT read these (only thumbnail.png); paste them into the
item's Steam page, or use them with a steamcmd content-builder VDF. Run standalone
or via build_all_workshop.py."""
import os
HERE=os.path.dirname(os.path.abspath(__file__)); PROOT=os.path.dirname(HERE)
WS = os.path.join(PROOT, "build", "workshop")

# folder -> (english DLC/title name, required DLC or None, extra note RU, extra note EN)
ITEMS = {
    "AI Russian Text Translation": ("base", None, "", ""),
    "AI Russian Text Darkness over Daggerford": ("Darkness over Daggerford", "Darkness over Daggerford", "", ""),
    "AI Russian Text Doom of Icewind Dale": ("Doom of Icewind Dale", "Doom of Icewind Dale", "", ""),
    "AI Russian Text Tyrants of the Moonsea": ("Tyrants of the Moonsea", "Tyrants of the Moonsea", "", ""),
    "AI Russian Text Dark Dreams of Furiae": ("Dark Dreams of Furiae", "Dark Dreams of Furiae", "", ""),
    "AI Russian Text Pirates of the Sword Coast": ("Pirates of the Sword Coast", "Pirates of the Sword Coast", "", ""),
    "AI Russian Text Infinite Dungeons": ("Infinite Dungeons", "Infinite Dungeons", "", ""),
    "AI Russian Text Wyvern Crown of Cormyr": ("Wyvern Crown of Cormyr", "Wyvern Crown of Cormyr", "", ""),
    "AI Russian Text Heroes of Neverwinter": ("Kingmaker", "Kingmaker",
        " Айтем покрывает все три приключения набора Kingmaker: Kingmaker, ShadowGuard и Witch's Wake.",
        " This item covers all three adventures of the Kingmaker pack: Kingmaker, ShadowGuard and Witch's Wake."),
}

def ru(name, req, note):
    if name == "base":
        return (
"Русскоязычный AI-перевод текста для Neverwinter Nights: Enhanced Edition — основная игра и официальные кампании (оригинальная кампания, Shadows of Undrentide, Hordes of the Underdark, а также бесплатные бонус-модули).\n\n"
"Переведён весь отображаемый текст: диалоги, журналы заданий, названия и описания предметов, существ, заклинаний и областей, реплики и сообщения интерфейса. Перевод выполнен с учётом контекста, терминологии Forgotten Realms и речевого регистра персонажей.\n\n"
"Установка: просто подпишитесь — перевод подгрузится автоматически при следующем запуске игры. Кириллические шрифты входят в подписку, настраивать ничего не нужно.\n\n"
"Перевод только текстовый — озвучка остаётся английской. Экран выбора кампаний в лаунчере может оставаться английским (техническое ограничение Workshop, на сам перевод не влияет).\n\n"
"Перевод сгенерирован нейросетью (AI), не является официальным и основан на оригинальном контенте Beamdog/BioWare.")
    return (
f"Русскоязычный AI-перевод текста для дополнения «{name}» (Neverwinter Nights: Enhanced Edition).{note}\n\n"
"Переведён весь отображаемый текст: диалоги, журналы заданий, названия и описания предметов, существ и областей, реплики катсцен, всплывающие сообщения и боевой фидбэк. Перевод выполнен с учётом контекста, терминологии Forgotten Realms и речевого регистра персонажей.\n\n"
"Установка: просто подпишитесь — перевод подгрузится автоматически при следующем запуске игры. Кириллические шрифты входят в подписку, настраивать ничего не нужно.\n\n"
f"Требуется оригинальное дополнение «{req}» — Steam отдаёт перевод только его владельцам. Перевод только текстовый, озвучка остаётся английской.\n\n"
"Перевод сгенерирован нейросетью (AI), не является официальным и основан на оригинальном контенте Beamdog/BioWare.")

def en(name, req, note):
    if name == "base":
        return (
"Russian AI text translation for Neverwinter Nights: Enhanced Edition — the base game and official campaigns (Original Campaign, Shadows of Undrentide, Hordes of the Underdark) plus the free bonus modules.\n\n"
"Translates all in-game text: dialogue, journal and quest entries, item, creature, spell and area names and descriptions, and interface messages. Translated with context, Forgotten Realms terminology and each character's voice in mind.\n\n"
"Installation: just subscribe — the translation loads automatically the next time you launch the game. Cyrillic fonts are bundled, no setup required.\n\n"
"Text only — the voice-over stays in English. The campaign-selection screen in the launcher may remain in English (a Workshop technical limitation that does not affect the translation itself).\n\n"
"This translation is AI-generated, unofficial, and based on the original Beamdog/BioWare content.")
    return (
f"Russian AI text translation for the \"{name}\" expansion (Neverwinter Nights: Enhanced Edition).{note}\n\n"
"Translates all in-game text: dialogue, journal and quest entries, item, creature and area names and descriptions, cutscene lines, floating messages and combat feedback. Translated with context, Forgotten Realms terminology and each character's voice in mind.\n\n"
"Installation: just subscribe — the translation loads automatically the next time you launch the game. Cyrillic fonts are bundled, no setup required.\n\n"
f"Requires the original \"{req}\" DLC — Steam delivers this item only to its owners. Text only; the voice-over stays in English.\n\n"
"This translation is AI-generated, unofficial, and based on the original Beamdog/BioWare content.")

def main():
    for folder, (name, req, note_ru, note_en) in ITEMS.items():
        d = os.path.join(WS, folder)
        if not os.path.isdir(d):
            continue
        open(os.path.join(d, "description_ru.txt"), "w", encoding="utf-8").write(ru(name, req, note_ru) + "\n")
        open(os.path.join(d, "description_en.txt"), "w", encoding="utf-8").write(en(name, req, note_en) + "\n")
    print(f"  wrote RU+EN descriptions into {len(ITEMS)} item folders")


if __name__ == "__main__":
    main()
