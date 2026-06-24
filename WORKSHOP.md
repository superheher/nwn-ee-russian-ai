# Раздача перевода через Steam Workshop

Базовый перевод NWN:EE (подмена `dialog.tlk` + кириллические шрифты) **можно раздавать
через Steam Workshop** — не только заменой файлов в игре. Подтверждено живым примером
(чужой айтем «Enhanced Edition Russian Translation», id 1307199542): установка для
игрока = «просто подпишись», игра сама подхватывает наш базовый `dialog.tlk` из
подписанного воркшоп-контента и переживает обновления Steam.

## Раскладка айтема (повторяем 1-в-1 с рабочим примером)

```
<item>/
├── thumbnail.png        превью Workshop (Steam: ≤1 МБ; квадрат — делаем 512×512)
├── tags.txt             КАТЕГОРИЯ айтема, по одному тегу на строку (у нас: override)
├── override/            = Documents/Neverwinter Nights/override/
│   ├── dialog.tlk       наш перевод (CP1251)
│   └── <шрифты>         fnt_*, bitter_*, merriw_reg, mordred_bold, tnr, ...
├── ovr/                 = lang/en/data/ovr/  — те же dialog.tlk + шрифты
└── data/                (ЭКСПЕРИМЕНТ, --with-repo)
    ├── mod/repository.json    имена/описания премиум-модулей (remap U+00xx)
    └── nwm/repository.json    имена/описания кампаний       (remap U+00xx)
```

`dialog.tlk` и шрифты кладутся в **обе** папки (`override/` и `ovr/`) — подстраховка под
оба пути загрузки.

## Сборка и загрузка

```bash
# собрать каталог айтема (ограничения на ИМЯ папки --out — ниже):
python3 context/make_workshop_item.py --thumbnail "<путь к картинке>" --with-repo \
  --out "build/workshop/<имя = будущий заголовок>"
```
Затем в игре: открыть консоль клавишей `~` и ввести (путь — БЕЗ кавычек):
```
WorkshopUpload /Users/heh/games/neverwinter-russian/nwn-ee-russian-ai/build/workshop/<имя>
```
**Ограничения на ИМЯ папки/путь (проверено на macOS 2026-06-23):**
- **Путь пиши СЫРЫМ, без кавычек/экранирования.** Одинарные/двойные кавычки и `\`-экранирование
  НЕ работают; сырой путь — работает.
- **Пробелы — МОЖНО.** Папка с пробелами заливается нормально, пробелы попадают и в имя работы.
- **Квадратные скобки `[ ]` — НЕЛЬЗЯ:** консоль их молча выбрасывает → путь не находится →
  заливается ПУСТОЙ айтем на 0 байт. (В видимом ЗАГОЛОВКЕ скобки можно — он задаётся на сайте;
  нельзя именно в имени ПАПКИ, а значит и в имени, по которому идёт матчинг обновления.)
- **Кириллица / не-ASCII — НЕЛЬЗЯ:** символы становятся `?` → путь не находится → пустой айтем.
  Имя папки держи на латинице.
- Steam: на аккаунте потрачено ≥ $5. Новый айтем сперва приватный/«на авто-проверке» — норма.

### Обновление (проверено на macOS 2026-06-23)

Команда одна — `WorkshopUpload`; адресовать айтем по ID нельзя. «Обновить или создать» решается
по совпадению **имени папки с ЗАГОЛОВКОМ работы**. Обновление РАБОТАЕТ (проверено: папка с
пробелами залилась как новая работа; затем переименовал работу и папку одинаково → повторная
заливка нашла и ОБНОВИЛА нужную работу). Условия:
1. Имя папки == заголовку работы (с учётом ограничений на символы выше: пробелы можно,
   скобки/кириллицу — нельзя).
2. **ГЛАВНАЯ ловушка (потеряли на ней часы):** если заголовок работы задан на НЕСКОЛЬКИХ ЯЗЫКАХ
   (напр. заполнены и английский, и русский title), матчинг НЕ срабатывает, пока все языковые
   заголовки не СИНХРОНИЗИРОВАНЫ в одну строку. Привели и EN, и RU title к одному английскому
   названию — только тогда обновление нашло работу. Это и была причина, почему первая работа
   упорно дублировалась вместо обновления.
3. Обновление может проявиться не сразу — иногда «на следующий день» (коммент #23 в треде).

Успех в консоли: «You already have a mod on Workshop with this name. Updating your mod with new
files.» Если вместо этого «Uploading your mod: …» и появилась новая работа — имя/заголовок не
совпали (проверь символы и синхронизацию языковых заголовков).

**Итого для обновляемой работы:** заголовок (и ВСЕ его языковые версии) — латиница, можно с
пробелами, БЕЗ квадратных скобок; имя папки сборки = ровно этот заголовок. Лишние/пустые копии
удаляй на странице работы (Owner Controls / «…» → Delete).

## Категория айтема (tags.txt)

Категория **не задаётся автоматически**; основной способ — файл `tags.txt` в корне айтема:
по одному тегу на строку, без пустых строк (официальный гайд Beamdog). На странице айтема
«Изменить» тоже может быть раздел тегов — стоит проверить (тогда правится без перезаливки). Допустимы **ровно эти 15 тегов**: `module tileset hak compilation persistentworld
override singleplayer multiplayer music sound voices textures models portraits script`. Наш
случай — `override` (подмена файлов игры: `dialog.tlk` + шрифты):
```
override
```
`make_workshop_item.py` пишет `tags.txt` сам (по умолчанию `--tags "override"`). Применить
к уже опубликованному айтему: положить `tags.txt` и повторно `WorkshopUpload <путь>` (tags.txt
— часть контента, обновляется вместе с ним); если не подхватилось — страница айтема «Изменить».

«Russian» в официальный список НЕ входит: чужой айтем `2270807144` указывал его как
произвольный тег, но это не категория из браузера мастерской. Язык лучше отражать в
заголовке/описании (у нас уже «[AI] Русскоязычный…»), а не тегом.

## Эксперимент: repository.json (экран выбора кампаний)

Флаг `--with-repo` кладёт в айтем `data/{mod,nwm}/repository.json` (наши переведённые и
заремапленные имена/описания). Рабочий чужой айтем его **не вёз**, поэтому грузится ли он
через Workshop — **не проверено**. Тест: `python3 install_ru.py --uninstall` → подписаться
на свой айтем → если экран выбора кампаний по-русски, эксперимент удался; если по-английски
— пересобрать без `--with-repo`.

## Опубликованная страница (финальные тексты)

**Title (RU):** `[AI] Русскоязычный текстовой перевод`
**Title (EN):** `[AI] Russian Text Translation`

Описание (RU):
```
Переведены основная кампания и официальные дополнения (Тени Андрентайда, Орды Подземья),
а также системные тексты: диалоги, заклинания и умения, описания предметов, журнал и интерфейс.

— Перевод с учётом контекста диалогов.
— Терминология в духе настольной D&D (Воин, Следопыт, Класс защиты).

Что не переведено:
— DLC-модули (Kingmaker, Тираны Лунного моря и др.) — переведены только их названия;
  собственный текст этих модулей лежит в отдельных файлах и в перевод не входит.
— Часть кнопок нового интерфейса EE (например Storage, Close) — заданы в разметке UI,
  а не в текстовой таблице, поэтому остаются английскими.
— "Нечеловеческая" речь (драконий, язык дроу, бормотание монстров) — намеренно оставлена
  как есть: она и в оригинале не на английском.

Возможны единичные неточности и стилистические шероховатости — пишите в комментарии, поправлю.
```

Описание (EN):
```
The original campaign and the official expansions (Shadows of Undrentide, Hordes of the
Underdark) are translated, along with the system text: dialogue, spells and feats, item
descriptions, the journal, and the interface.

— Translated with full conversation context.
— Terminology in the spirit of tabletop D&D (Fighter, Ranger, Armor Class).

What's not translated:
— DLC modules (Kingmaker, Tyrants of the Moonsea, etc.) — only their titles are translated;
  these modules' own text is stored in separate files and isn't part of this translation.
— Some buttons in the new EE interface (e.g. Storage, Close) are defined in the UI markup
  rather than the text table, so they remain in English.
— "Non-human" speech (Draconic, the Drow language, monster gibberish) is intentionally left
  as-is: it isn't English in the original either.

There may be occasional inaccuracies or stylistic rough edges — leave a comment and I'll fix it.
```

Канонические имена (используем эти): Тени Андрентайда = *Shadows of Undrentide*,
Орды Подземья = *Hordes of the Underdark*, Тираны Лунного моря = *Tyrants of the Moonsea*.

## Авторские права — почему НЕ заявляем «1C-copyright free»

Официальный русский перевод NWN принадлежит **1С** (заброшен ~1.61, база 1.66); народные
русификаторы EE — производные от него. Наши **фразы** сгенерированы заново с английского
(не копия 1С), но **терминология** подогнана под привычный лексикон, извлечённый из
1С-производного русификатора ZoG (`glossary/mined_glossary.tsv`). Плюс сам текст игры —
IP Beamdog/WotC. Поэтому «copyright-free» некорректно и рискованно — в описании копирайт-
claim не ставим; хватает тега `[AI]`. Подробности — handoff и память проекта.

## Заметка для треда Beamdog (EN) — все факты проверены на macOS 2026-06-23

Текст ниже опубликован/предназначен для треда «How to upload files to the Steam Workshop».

```
macOS notes for WorkshopUpload (path handling + updating), in case it saves someone the
hours it cost me. All of this was tested on macOS — Windows seems more forgiving (people
clearly have brackets in their titles there).

Path / folder-name rules:
- Write the path RAW after the command. Single quotes, double quotes, and backslash-escaping
  all failed for me; only the unquoted path worked.
- Spaces in the folder name are FINE on macOS — they upload and even carry into the item name.
- Square brackets [ ] in the FOLDER name are silently stripped, so the path no longer resolves
  and you get a 0-byte empty item. (Brackets in the visible title are fine — set the title on
  the website; just keep them out of the upload folder name.)
- Non-Latin characters (e.g. Cyrillic) in the folder name become "?" -> bad path -> empty item.
  Keep the folder name ASCII.

Updating an existing item (this DOES work on macOS):
- Re-upload from a folder whose name exactly matches the item's title. Success message:
  "You already have a mod on Workshop with this name. Updating your mod with new files."
  If instead you see "Uploading your mod: ..." and a new item appears, the names didn't match.
- The gotcha that cost me hours: if your item has a localized title in more than one language
  (e.g. you filled in both an English and a Russian title), the name-match for updates FAILS
  until ALL localized titles are set to the same string. Once I made every language's title
  identical, the update finally landed on the existing item instead of creating duplicates.

So on macOS, for an item you intend to keep updating: the title (in every language) should be
ASCII, spaces are OK, no square brackets; and name your upload folder exactly that title.
```
