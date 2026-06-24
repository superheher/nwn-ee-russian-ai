# NWN:EE русификация — сводная база знаний

Мастер-документ: всё durable-знание проекта в одном месте, чтобы ничего не потерялось.
Детали — в специализированных доках и в памяти проекта (ссылки в конце).

---

## 1. СТАТУС — что переведено и где (на 2026-06-24)

| Слой | Объём | Состояние |
|---|---|---|
| Базовый `dialog.tlk` | 106 496 строк (95% RU) | задеплоен на маунт + Workshop-айтем |
| 14 `.nwm/.mod` (встроенные LocStrings) | 35 282 уник. строки | переведены, задеплоены |
| 6 контент-хаков (диалоги/предметы/существа) | 30 944 уник. строки | переведены, задеплоены |
| UI-формулировки (tlk-оверрайды) | 3 строки | поправлены |
| **Скрипт-катсцены/барки/feedback** | 2 666 уник. строк, 13 модулей; 2 643 (99.1%) живут | **переведены, перекомпилированы/пропатчены, задеплоены (§5)** |

Маунт `/Volumes/twitch/nwn` — полностью русский (база + все 8 DLC), включая скриптовый
слой (катсцены/барки/feedback) — 99% строк. Ossian-фреймворк `hf_*` (Daggerford/Moonsea/DoID),
который раньше блокировал перекомпиляцию, обойдён патчером байткода `ncs.py` (§5). Остаток
~1% — мёртвый/include-код, в игре не виден. Furiae дополнительно отгружен в Steam Workshop.

---

## 2. ПОЛНАЯ ИНВЕНТАРИЗАЦИЯ DLC

**8 платных премиум-DLC**, файлы на маунте `data/{nwm,mod,hk}`:

| DLC | Модуль-файл | Где ТЕКСТ | Контент-хак |
|---|---|---|---|
| Darkness over Daggerford | `nwm/…Daggerford.nwm` | в .nwm | — (dodee_* = ассеты) |
| Doom of Icewind Dale | `nwm/…Dale.nwm` | в .nwm | — (doiwd.hak=0) |
| Infinite Dungeons | `nwm/…Infinite Dungeons.nwm` | **в хаке** | `hk/id_resources.hak` |
| Pirates of the Sword Coast | `nwm/…Pirates….nwm` | **в хаке** | `hk/potsc_top.hak` |
| Tyrants of the Moonsea | `nwm/…Moonsea.nwm` | в .nwm | — (tm_* = ассеты) |
| Wyvern Crown of Cormyr | `nwm/…Cormyr.nwm` | **в хаке** | `hk/wc_top.hak` |
| Kingmaker (пак) | `mod/Kingmaker.mod` | **в хаке** | `hk/km_resources.hak` |
| ↳ ShadowGuard | `mod/ShadowGuard.mod` | **в хаке** | `hk/sg_resources.hak` |
| ↳ Witch's Wake | `mod/Witch's Wake.mod` | **в хаке** | `hk/ww_resources.hak` |
| Dark Dreams of Furiae | `nwm/…Furiae.nwm` | в .nwm | — (ddf.hak=0) |
| Мелкие .mod (бонусы) | `mod/{Neverwinter Chess, Contest Of Champions 0492, The Dark Ranger's Treasure, The Winds of Eremor, To Heir is Human}.mod` | в .mod | — |

**КЛЮЧЕВОЕ:** 6 модулей хранят основной текст в ХАКЕ, а не в `.nwm` (мало встроенного в
самом модуле). СКРИПТЫ (NSS/NCS) — почти всегда в `.nwm/.mod`, не в хаке. `_resources/_dev/
art/sound/tile/2da`-хаки — ассеты, текста 0.

**Steam Workshop-айтемы (аккаунт юзера):** `3750140362` (базовый перевод: dialog.tlk+шрифты+
repository.json), `3750222088` (Furiae: пересобран на `development/`-раскладку). Голосовой
пак 1С `2270807144` (чужой).

---

## 3. КЛЮЧЕВЫЕ ТЕХНИЧЕСКИЕ НАХОДКИ

### 3.1 Где хранится текст (4 разных места)
1. **`dialog.tlk`** (общий) — база + UI + те DLC, что ссылаются по `strref`. Override-able.
2. **Встроенные `CExoLocString`** (`strref=-1`) внутри GFF-ресурсов `.nwm/.mod` — текст инлайн.
3. **GFF-ресурсы внутри контент-ХАКА** — у 6 модулей диалоги/предметы там (не в .nwm).
4. **Хардкод-литералы в СКРИПТАХ** (NSS→NCS) — катсцены на движке, барки. Не в tlk/GFF.

### 3.2 Доставка перевода через Steam Workshop — `development/` (ПРОРЫВ)
Workshop монтирует подпапки айтема в одноимённые resman-алиасы ПО ИМЕНИ, без бело-листа.
Приоритеты (верх→низ): `development/`(71M) > hak(31/30M) > **модуль/.nwm(~20M)** > `override/`
(12M) > база. Значит:
- `override/` (12M) НЕ достаёт внутренности загруженного `.nwm` → база/PRC работают, премиум нет.
- **`development/` (71M) ПЕРЕБИВАЕТ внутренности модуля** → перевод премиум-модуля доставляется
  по подписке. Проверено в игре + на твоём айтеме. `data/nwm/` в айтеме НЕ монтируется.
- Раздача ЛЕГИТИМНА: айтему ставится флаг required-DLC → Steam отдаёт только владельцам DLC.
Подробно — `WORKSHOP_PREMIUM.md`. Сборка айтема — `context/make_ddf_workshop.py`. Правила
заливки (`WorkshopUpload`, латиница в имени папки, без скобок) — `WORKSHOP.md`.

### 3.3 Экран выбора кампаний (`repository.json`) — Workshop НЕ может
Названия/описания глав в лаунчере — из `<install>/data/{mod,nwm}/repository.json` (gamedata,
литералы). Лаунчер = 4 группы (Официальные=gamedata / Сообщество=workshop / Премиум / Локальные);
workshop-контент в «Сообщество», не поверх «Официальных». Проверено исчерпывающе (10 раскладок).
Локальный фикс — `patch_repo.py` (в Steam Launch Options `python3 patch_repo.py && %command%`).

### 3.4 Скрипт-перевод (катсцены/барки) — `nwnsc`-перекомпиляция (ПИЛОТ ДОКАЗАН)
Хардкод-строки в скриптах → перекомпилировать NSS→NCS. Тулчейн: `tools/nwnsc` (niv v1.1.5,
macOS universal). Команда: `nwnsc -n "<install>" -i "<NSS-папка>" -r out.ncs script.nss`. ГРАБЛИ:
include'ы с незакрытым `/*` (идиома Bioware) ломают парсер → закрывать лексером. CP1251 в литералы
ТОЛЬКО Python'ом (Edit-тул=UTF-8, нельзя). Вписывать NCS в модуль через `erf`. Род в конкатенациях
с именем игрока обходить безглагольно. ПОЛНЫЙ ПЛАН ФАЗЫ — `SCRIPT_TRANSLATION_PLAN.md`.

### 3.5 Рендер CP1251
Весь русский — CP1251 (1 байт/символ). Кириллические шрифты на маунте в `lang/en/data/ovr/`
(стоят). Имена цветовых/токен-тегов `<…>` сохранять точь-в-точь; гендер-форки `<he/she>` —
заменять на естественный русский.

---

## 4. ТУЛИНГ (карта, всё в `context/`, доказано)

- `erf.py` — read/write ERF (`.nwm/.mod/.hak`, принимает все магии), round-trip байт-в-байт.
- `gff.py` — lossless GFF V3.2 read/write (встроенные LocString'и).
- `ddf_prep.py` — извлечь встроенные строки модуля → батчи+index (для перевода).
- `ddf_apply.py` — вписать RU (CP1251) в GFF, перепаковать ERF (`--nwm/--translated/--index/--out`).
- `ddf_override.py` — выгрузить переведённые ресурсы как loose-файлы (для `development/`).
- `make_ddf_workshop.py` — собрать Workshop-айтем (`development/`+шрифты+thumbnail+tags).
- `patch_repo.py` — пропатчить установочный `repository.json` (экран кампаний), кросс-платформ.
- `tlk_fix.py` + `tlk_overrides.json` — точечные правки UI-строк в `dialog.tlk`.
- `validate_dlc.py` — код-валидация переводов (теги/плейсхолдеры/переносы; исключает `<<коммент>>`).
- Перевод-Workflow — паттерн в `wf_module.js`/`wf_nss.js` (батчи + глоссарий + код-валидация + repair).
- Глоссарий — `context/glossary_active.json` (термины FR/D&D, имена). Обязателен в переводе.
- `tools/nwnsc` — компилятор NSS→NCS (для скрипт-фазы).
- **Скрипт-фаза:** `nss_lex.py` (лексер + авто-детект display-обёрток), `nss_prep.py`/`nss_apply.py`
  (извлечь→перевести→перекомпилировать/пропатчить→вписать→деплой), `nss_run.py`+`nss_modules.json`
  (драйвер по модулям). См. §5.
- **`ncs.py`** — патчер байткода NCS (строки + релокация прыжков) для нерекомпилируемых скриптов.
- **`audit_english.py`** — МОДЕЛЬ-НЕЗАВИСИМЫЙ аудит остаточного английского в задеплоенном байткоде
  (QA-гейт перед релизом); `ncs_worklist.py`/`ncs_patch.py` — перевод+патч найденного аудитом.
- **`build_all_workshop.py`** + `make_dlc_override.py` + `make_descriptions.py` — сборка 9
  Workshop-айтемов (база+8 DLC) с описаниями RU+EN. См. `WORKSHOP_ITEMS.md`.

RU-переводы закоммичены: `dlc/*/translated`, `dlc/*_hak/translated`. Англ. исходники +
derived-бинари (`*.nwm/*.mod/*.hak`, batches, index, override, tools/) — в `.gitignore`.

---

## 5. СКРИПТ-ФАЗА — ЗАВЕРШЕНА (2026-06-24)

**Тулинг (всё в `context/`, доказано):**
- `nss_lex.py` — лексер NWScript + извлечение display-строк. Токенайзер (комментарии везде —
  grep НЕЛЬЗЯ); `discover_display_slots()` авто-находит display-ОБЁРТКИ (любая функция,
  пробрасывающая строковый параметр в известный display-слот — ловит `SceneSpeak`/`PartyGotEntry`/
  `cs_*`/`csll_*`/`SpeakWrapper` без хардкода; debug-обёртки `Debug/Log/Test/Report` исключены).
  Конкатенации → шаблон `{0}` + код-куски (apply пересобирает выражение целиком). `fix_comments`
  чинит висячие `/*` (идиома Bioware).
- `nss_prep.py` — извлечь → батчи (формат wf) + `index.json` (id→en, id→occ со span/codes).
- `nss_apply.py` — вписать RU (CP1251; inside-quote для простых, whole-expr для конкатенаций),
  граф include'ов → перекомпиляция ТОЛЬКО затронутых entrypoint-скриптов (`nwnsc`, БЕЗ `-o`,
  совпадает со стоком 4580б; 2-проход: strict, затем `-s` для warts вроде `x2_inc_cutscene`),
  вписать NCS в `_ru`-модуль, деплой. Идемпотентно (всегда от чистых англ. исходников).
- `nss_run.py` + `nss_modules.json` — драйвер по всем модулям (prep/apply/stat).
- `wf_nss.js` — Workflow перевода (глоссарий + код-валидация {N}/«»/\\n + repair; обход рода
  в конкатенациях с именем игрока).
- **`ncs.py` — ПАТЧЕР БАЙТКОДА NCS (ключевое, решает hf-проблему!).** Патчит строковые
  константы прямо в скомпилированном NCS БЕЗ перекомпиляции (для скриптов на недоступном
  `hf_*`). Релокация прыжков обязательна (меняется длина строки → сдвиги). ВАЛИДАЦИЯ: парсер
  round-trip байт-в-байт на ВСЕХ 14 830 стоковых NCS (опкод-таблица верна); прыжки относительны
  старта инструкции — проверено 1 740 400 прыжков, все на границах; `STORE_STATE` (DelayCommand/
  AssignCommand) — операнды = РАЗМЕРЫ стека (макс 116), НЕ код-офсеты (релокации не требуют), за
  ним всегда JMP. patch_strings: правит строки, релоцирует JMP/JSR/JZ/JNZ (отн. int32), чинит
  заголовок-размер, верифицирует (round-trip + все прыжки на границах) или НЕ патчит. Интегрирован
  в `nss_apply` как фолбэк: что не перекомпилилось — патчим стоковый NCS.

**ФАКТ-РЕЗУЛЬТАТ:** 2 306 уник. display-строк, 13 модулей. Валидатор чист (0 проблем на 2306).
Перевод — Workflow (2 прогона: первый 1582, затем +724 после dataflow-фикса извлечения).
**DATAFLOW-ФИКС (важно):** первый экстрактор брал литералы только из переменных с «говорящими»
именами (`sLine`/`sText`); пропускал именованные константы вида `const string S_NARRATION_1=".."`,
уходящие в показ (`cs_SpeakString(o,S_NARRATION_1)`). Решение — `discover` + проброс: берём литерал,
если переменная попадает в display-слот (любой), МИНУС сравниваемые (`==`) и код-подобные (`_is_codey`:
camelCase/snake/resref/ALLCAPS/`foo(`). Это вскрыло +724 пропущенных строки (описания локаций,
закадровая озвучка, боевой/скилловый фидбэк, реплики). Урок: ловить ОБА паттерна (имя-эвристика +
dataflow var→display).
**Перекомпиляция/деплой:** 9 модулей — 100% (cormyr 907 NCS, furiae, pirates, dungeons, kingmaker,
shadowguard, witchswake, chess, treasure). 3 Ossian-модуля — частично (исходники include-фреймворка
`hf_*` НЕ поставлялись → перекомпиляция зависимых скриптов невозможна, те строки остаются англ.):
Daggerford 179/275 скриптов, Moonsea 62/126, DoID 44/51. Contest 1/2 (proto-mismatch `inc_module`,
`-s` не лечит). Все провалы → стоковый англ. NCS (логика цела). `_scr`-модули задеплоены на маунт
(бэкап англ. `.orig` цел). СКРИПТЫ ЖИВУТ ТОЛЬКО в `.nwm/.mod` (контент-хаки — 0 скриптов).
**ИТОГ ПО СТРОКАМ (замер по байтам в задеплоенных NCS): 2 643 / 2 666 = 99.1% живут по-русски.**
hf-ПОТОЛОК СНЯТ байткод-патчером `ncs.py`. Объём вырос 1582→2666 (три находки юзера в игре, каждая
вскрыла слой извлечения — см. ниже §extract). По модулям: Pirates/Chess/Treasure/Moonsea/DoID 100%,
ShadowGuard 297/299, Dungeons 257/260, Cormyr 388/392, Daggerford 636/640, Kingmaker 75/76,
WitchsWake 124/125, Furiae 167/173, Contest 12/14. Остаток ~23 = DEAD/include-код + значения
`SetLocalString` (намеренно НЕ трогаем — могут сравниваться). Эффективное игровое покрытие ~100%.

**§extract — ЭВОЛЮЦИЯ ИЗВЛЕЧЕНИЯ (важно для будущих модулей):** display-обёртки ловятся 4 способами,
все в `discover_display_slots`: (1) dataflow — функция пробрасывает строковый ПАРАМЕТР в display-слот,
ПРЯМО или как операнд КОНКАТЕНАЦИИ (`SpeakString("["+GetName(o)+"] "+s)` → SceneSpeak); (2) data-driven —
НЕопределённая в исходниках функция (тело в неотгруженном include), вызванная с ≥2 display-похожими
литералами, ≥60% (ловит `CutSpeakString` из base `x2_inc_cutscene`); (3) цвет-форматтеры — тело
возвращает `"<c..>"+s+"</c>"` (`MakeTextRed`); (4) именованные cutscene-переменные. ИСКЛЮЧЕНИЯ: debug
(`_DEBUG_FN` вкл. test/print), tag/resref/key-функции (`_NONDISPLAY`), код-литералы (`_is_codey`:
camelCase/snake/ALLCAPS/`foo(`), `SetLocalString`-значения (логика). Юзер-находки: `S_NARRATION_1`
(named const→show, dataflow), Daggerford `mv_*` (hf→патчер), Kingmaker `CutSpeakString` (#2).

**`hf_*`-ПРОБЛЕМА И ЕЁ РЕШЕНИЕ:** Ossian (Daggerford/Moonsea/DoID) компилировали `hf_in_*` в каждый
скрипт при сборке, но ИСХОДНИКИ не отгрузили (нет ни `.nss`, ни отдельного `.ncs`; нет в `-n`-базе;
нет публично — проверено) → перекомпиляция зависимых скриптов невозможна. РЕШЕНО патчером байткода
`ncs.py` (см. выше): правим строки прямо в стоковом NCS без компилятора, минуя hf полностью. Так же
добито Contest (`inc_module` proto-mismatch). Триггер находки — юзер увидел англ. катсцену в Daggerford
(`mv_*` все include'ят `hf_in_cutscene`).

**Объём display по модулям (после авто-обёрток):** Daggerford 525, Cormyr 287, Pirates 195, Moonsea
181, Dungeons 99, ShadowGuard 83, Furiae 77, DoID 47, Kingmaker 46, WitchsWake 15, Chess 13,
Treasure 12, Contest 2; Eremor/ToHeir 0.

---

## 6. СОСТОЯНИЕ МАУНТА + БЭКАПЫ

- `/Volumes/twitch/nwn` — GOG-Windows-шар (юзера), сетевой маунт (может отваливаться — был случай).
  Стоят все 8 DLC. Все переведённые `_ru`-модули/хаки + переведённый `dialog.tlk` задеплоены.
- **Бэкапы (англ. эталоны):** `<файл>.orig` рядом с каждым тронутым (`.nwm/.mod/.hak/dialog.tlk`).
  Откат любого — копией `.orig` обратно.
- Mac-Steam установка — английская (кроме шрифтов+repo в `~/Documents/.../development` тест-наборы
  убраны). Перевод на МАУНТЕ, не на Mac-Steam.

---

## 7. ПОЙНТЕРЫ (доки + память)

**Доки в `nwn-ee-russian-ai/`:** `PROJECT_KNOWLEDGE.md` (этот), `WORKSHOP_PREMIUM.md` (Workshop/премиум-
доставка), `SCRIPT_TRANSLATION_PLAN.md` (фаза скриптов — план), `WORKSHOP.md` (заливка айтемов),
`TRANSLATION_HANDOFF.md` + `README.md` (база). 

**Память проекта:** `nwn-premium-dlc-campaign` (кампания DLC, скрипт-пилот), `nwn-ddf-dlc-translation`
(Furiae+Workshop-development/), `nwn-premium-dlc-distribution-legitimate` (права/required-DLC),
`nwn-ee-workshop-distribution`, `nwn-own-translation-project`, `nwn-translation-copyright-provenance`,
`nwn-doid-dlc-translation`, `nwn-ee-russifier-mac-port`.

**Следующий шаг:** скрипт-фаза по `SCRIPT_TRANSLATION_PLAN.md` (Cormyr целиком → все, ~2–5M токенов).
