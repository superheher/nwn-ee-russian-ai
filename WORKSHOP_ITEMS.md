# Steam Workshop — 10 айтемов русского AI-перевода

Собраны в `build/workshop2/`: `context/build_workshop_haks.py` (DLC),
`context/build_workshop_base.py` (база), `context/build_mega_jrl.py` (журналы),
`context/finalize_workshop.py` (обложки, теги, описания). Каждый айтем — готовая
папка для заливки `WorkshopUpload`.

Раскладка `build/workshop/` (первая версия, всё через `development/`) — устарела и
опасна: `module.jrl` оттуда ломал журнал оригинальной кампании. См. `WORKSHOP_PREMIUM.md` §4b.

## Раскладка айтема
- **DLC-айтемы (8):** `hak/<первый хак модуля>.hak` — полная копия хака, который модуль
  уже подключает в `Mod_HakList`, с влитыми переводами (включая `module.jrl`). Хак (31M)
  перебивает модуль (20M) и грузится ТОЛЬКО своим модулем → кампания и чужие модули
  не затронуты. `override/`+`ovr/` — кириллические шрифты. `thumbnail.png` (512×512),
  `tags.txt`=`override`.
  Вес: Cormyr 42 МБ, Pirates 46, Daggerford 52, Moonsea 66, Kingmaker-пак 125,
  Infinite Dungeons 233, DoID 384, DDF 744 (хак несётся целиком — userdir-хак подменяет
  установочный, а не дополняет).
- **Базовый айтем:** `override/`+`ovr/` с переведённым `dialog.tlk` + шрифты; `development/`
  с бонус-модулями (Chess, Contest, Treasure, Eremor, To Heir is Human) — БЕЗ `module.jrl`
  и без ресурсов, чьи имена есть в базовой игре (иначе подменяют контент кампании).
- **«AI Russian Text Journals» (opt-in, видимость: скрытый):** `development/module.jrl` —
  объединённый журнал всего официального контента (597 категорий). Даёт русский журнал
  трём бонус-модулям, но ломает журнал во ВСЕХ пользовательских модулях. Ссылка на него —
  только из описания базового айтема.

## Заливка (в игре, консоль `~`)
Путь СЫРОЙ, без кавычек (пробелы — ОК, скобки/кириллица в пути — НЕЛЬЗЯ; у нас латиница):
```
WorkshopUpload /Users/heh/games/neverwinter-russian/nwn-ee-russian-ai/build/workshop/AI Russian Text Wyvern Crown of Cormyr
```
Имя папки = заголовок айтема. Если айтем уже есть (база `3750140362`, Furiae `3750222088`) —
совпадение имени папки с заголовком обновит его; иначе создаст новый. Заголовок/описание/
видимость — на странице работы.

## Описания (RU + EN)
В каждой папке айтема лежат `description_ru.txt` и `description_en.txt` (сплошные строки, без
переносов). Генератор — `context/make_descriptions.py` (вызывается из `build_all_workshop.py`).

**Авто-заливка описания — НЕЛЬЗЯ через штатный загрузчик.** Официально (Beamdog/Steam) `WorkshopUpload`
читает из папки ТОЛЬКО `thumbnail.png`/`.jpg`; заголовок и описание вводятся ВРУЧНУЮ на странице работы
в Steam после заливки. То есть `description_*.txt` — для копипаста на страницу. Единственный
потенциальный авто-путь — `steamcmd +workshop_build_item <vdf>` (поля `title`/`description`/`previewfile`/
`publishedfileid`/`contentfolder`), но это НЕ проверено на NWN (704450 — кастомный загрузчик Beamdog),
сложнее и требует логина steamcmd. Надёжно — `WorkshopUpload` + вставить описание руками.

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
