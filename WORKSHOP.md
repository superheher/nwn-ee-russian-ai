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
# собрать каталог айтема из build/dialog.tlk + шрифтов (+ опц. repository.json):
python3 context/make_workshop_item.py --thumbnail "<путь к картинке>" --with-repo \
  --out "build/workshop/[AI] Russian Text Translation"
# имя --out ДОЛЖНО точно совпадать с ЗАГОЛОВКОМ айтема в Workshop, иначе повторная
# загрузка создаст дубликат (см. «Обновление и дубликаты» ниже).
```
Затем в игре: открыть консоль клавишей `~` и ввести (путь с пробелами поддерживается):
```
WorkshopUpload /Users/heh/Downloads/neverwi/nwn_ru_mac/build/workshop/[AI] Russian Text Translation
```
- Требование Steam: на аккаунте должно быть потрачено ≥ $5.
- Новый айтем сперва приватный и «на авто-проверке контента» — это норма; публичным
  делается на странице айтема (Видимость → Public).

### Обновление и дубликаты (важно!)

`WorkshopUpload` находит «тот же» айтем по совпадению **имени папки с ЗАГОЛОВКОМ айтема**
(офиц. гайд: «name of your mod == name of the directory»), а НЕ просто по пути/папке.
Поэтому если заголовок на Steam переименован (напр. в «[AI] Russian Text Translation») и
уже не равен имени папки `nwn_ru_own` — повторная загрузка не находит совпадения и создаёт
**ДУБЛИКАТ** (так и случилось 2026-06-23: вышло две работы). Правила:
- `WorkshopUpload` запускать только когда **заголовок айтема == имя папки** (`nwn_ru_own`).
- Заголовок/описание/видимость правь на **странице айтема** — это НЕ требует повторной
  загрузки и дубликат не создаёт.
- Нужно залить новый КОНТЕНТ после смены заголовка? Временно верни заголовок = `nwn_ru_own`
  → `WorkshopUpload` → верни красивый заголовок обратно.
- Лишние копии удаляй на странице айтема: Owner Controls / меню «…» → Delete.

## Категория айтема (tags.txt)

Категория **не задаётся автоматически и не выбирается на сайте** — её определяет файл
`tags.txt` в корне айтема: по одному тегу на строку, без пустых строк (официальный гайд
Beamdog). Допустимы **ровно эти 15 тегов**: `module tileset hak compilation persistentworld
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
