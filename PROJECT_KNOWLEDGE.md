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
| **Скрипт-катсцены/барки** | ~1 797 уник. строк (см. §5) | **пилот доказан, фаза не начата** |

Маунт `/Volumes/twitch/nwn` — полностью русский (база + все 8 DLC), кроме скриптовых
катсцен/барков. Furiae дополнительно отгружен в Steam Workshop.

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
- Перевод-Workflow — паттерн в `wf_module.js` (батчи + глоссарий + код-валидация + repair).
- Глоссарий — `context/glossary_active.json` (термины FR/D&D, имена). Обязателен в переводе.
- `tools/nwnsc` — компилятор NSS→NCS (для скрипт-фазы).

RU-переводы закоммичены: `dlc/*/translated`, `dlc/*_hak/translated`. Англ. исходники +
derived-бинари (`*.nwm/*.mod/*.hak`, batches, index, override, tools/) — в `.gitignore`.

---

## 5. ДАННЫЕ ПО ТОКЕНАМ + ОЦЕНКА СКРИПТ-ФАЗЫ

**Факт по завершённым прогонам (subagent-токены):**
- Hak-перевод #1: 182 батча → 10.86M токенов (~59.6K/батч ≈ 90 строк).
- Hak-перевод #2: 165 батчей → 10.36M (~62.8K/батч).
- → **~60K токенов на батч (~90 строк) ≈ ~670 токенов/строку** (доминирует чтение глоссария
  каждым агентом). GFF+хаки суммарно (66 226 строк ≈ 736 батчей, с ретраями из-за API-сбоев) —
  порядка **~40–45M токенов**.

**ОЦЕНКА СКРИПТ-ФАЗЫ (следующая сессия):**
- Замер: **~1 797 уникальных** display-строк, **67 949 символов** (~17K токенов исходника).
- С учётом недосчёта (куски конкатенаций ловятся не полностью, редкие display-функции) реально
  **~2 000–3 000 уник. строк**.
- Перевод: ~2 000–3 000 строк ÷ 90 ≈ **22–33 батча × ~60K = ~1.3–2.0M токенов**.
- Плюс постройка тулинга (`nss_prep/nss_apply`), отладка перекомпиляции по модулям, верификация —
  ещё ~1–3M.
- **ИТОГО скрипт-фаза ≈ 2–5M токенов** — заметно ДЕШЕВЛЕ GFF/хак-фаз. Дорогое тут не токены, а
  аккуратность (не сломать логику) и перекомпиляция, а не объём текста (он маленький).

Объём display-текста по модулям (замер): Pirates 380, Cormyr 370, Daggerford 333, Moonsea 191,
WitchsWake 156, InfDungeons 139, ShadowGuard 107, Kingmaker 67, Furiae 63, DoID 46.

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

**Доки в `nwn_ru_mac/`:** `PROJECT_KNOWLEDGE.md` (этот), `WORKSHOP_PREMIUM.md` (Workshop/премиум-
доставка), `SCRIPT_TRANSLATION_PLAN.md` (фаза скриптов — план), `WORKSHOP.md` (заливка айтемов),
`TRANSLATION_HANDOFF.md` + `README.md` (база). 

**Память проекта:** `nwn-premium-dlc-campaign` (кампания DLC, скрипт-пилот), `nwn-ddf-dlc-translation`
(Furiae+Workshop-development/), `nwn-premium-dlc-distribution-legitimate` (права/required-DLC),
`nwn-ee-workshop-distribution`, `nwn-own-translation-project`, `nwn-translation-copyright-provenance`,
`nwn-doid-dlc-translation`, `nwn-ee-russifier-mac-port`.

**Следующий шаг:** скрипт-фаза по `SCRIPT_TRANSLATION_PLAN.md` (Cormyr целиком → все, ~2–5M токенов).
