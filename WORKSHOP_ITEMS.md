# Steam Workshop — 9 айтемов русского AI-перевода

Собраны скриптом `context/build_all_workshop.py` в `build/workshop/`. Каждый айтем —
готовая папка для заливки `WorkshopUpload`.

## Раскладка айтема
- **DLC-айтемы (8):** `development/` (переведённые ресурсы модуля+хака: GFF-диалоги/
  предметы/существа + русские NCS-скрипты; БЕЗ базовых resref'ов `nw_/x2_…` и без
  `module.ifo`) → приоритет 71M, перебивает загруженный модуль/хак. `override/`+`ovr/` —
  кириллические шрифты (чтобы текст рендерился у подписчика без базового айтема).
  `thumbnail.png` (512×512, <1 МБ), `tags.txt`=`override`.
- **Базовый айтем:** `override/`+`ovr/` с переведённым `dialog.tlk` + шрифты; `development/`
  с бонус-модулями (Chess, Contest, Treasure, Eremor, To Heir is Human).

## Заливка (в игре, консоль `~`)
Путь СЫРОЙ, без кавычек (пробелы — ОК, скобки/кириллица в пути — НЕЛЬЗЯ; у нас латиница):
```
WorkshopUpload /Users/heh/Downloads/neverwi/nwn_ru_mac/build/workshop/AI Russian Text Wyvern Crown of Cormyr
```
Имя папки = заголовок айтема. Если айтем уже есть (база `3750140362`, Furiae `3750222088`) —
совпадение имени папки с заголовком обновит его; иначе создаст новый. Заголовок/описание/
видимость — на странице работы.

## Айтем → флаг required-DLC (ставишь на странице каждой работы)
| Айтем | Требует DLC |
|---|---|
| AI Russian Text Translation | — (база, бесплатно) |
| AI Russian Text Darkness over Daggerford | Darkness over Daggerford |
| AI Russian Text Doom of Icewind Dale | Doom of Icewind Dale |
| AI Russian Text Tyrants of the Moonsea | Tyrants of the Moonsea |
| AI Russian Text Dark Dreams of Furiae | Dark Dreams of Furiae |
| AI Russian Text Pirates of the Sword Coast | Pirates of the Sword Coast |
| AI Russian Text Infinite Dungeons | Infinite Dungeons |
| AI Russian Text Wyvern Crown of Cormyr | Wyvern Crown of Cormyr |
| AI Russian Text Heroes of Neverwinter | Kingmaker |

required-DLC = Steam отдаёт айтем ТОЛЬКО владельцам нужной DLC → контент за пейволом, раздача
легитимна.

## Что проверить в игре после подписки (важно!)
1. **GFF (диалоги/предметы/существа)** через `development/` — ДОКАЗАНО на Furiae. Должно быть RU.
2. **NCS-скрипты (катсцены/барки/фидбэк)** через `development/` — НЕ протестировано в игре
   (механизм родной — это штатная папка тулсета для тест-скриптов, уверенность высокая, но
   проверить). Если скрипты НЕ перебьются — диалоги всё равно русские, просто катсцены англ.
   (downside нет, только upside). Глянь катсцену в подписанном модуле.

## Известные ограничения
- **Экран выбора кампаний** (`repository.json`) остаётся английским — через Workshop не
  доставить (gamedata-only). Локальный фикс — `patch_repo.py` в Launch Options. Косметика.
- **~71 базовый скрипт на модуль** (resref `nw_/x2_…`, кастомизированные модулем) НЕ кладём в
  `development/` (иначе перебили бы базовую игру глобально) → эти строки в Workshop-версии
  останутся англ. (мелочь; при ПРЯМОМ деплое на маунт они русские). Безопасность > полнота.
- Размеры айтемов 36–68 МБ (loose-ресурсы) — для Workshop ок.

Пересборка: `python3 context/build_all_workshop.py` (читает `_scr`-модули/`_ru`-хаки + англ.
`.orig` с маунта + обложки из `/Users/heh/Downloads/nwn_thumbs`).
