# Layer display names v0 — нейтральные z-уровни и доменные профили

**Date:** 2026-05-31  
**Status:** accepted (display names; **IDs не меняем**)  
**Parent:** [`second-signal-system-v0.md`](second-signal-system-v0.md), [`sss-multi-lattice-z-v0.md`](sss-multi-lattice-z-v0.md), [`f0-math-logical-layer-v0.md`](f0-math-logical-layer-v0.md)  
**Companion:** [`casa-glossary-v0.md`](casa-glossary-v0.md), [`agent-store-catalog-v0.md`](agent-store-catalog-v0.md), [`casa-wake-sleep-concept-v0.md`](casa-wake-sleep-concept-v0.md), [`language-acquisition-loop-v0.md`](language-acquisition-loop-v0.md), [`agent-existence-north-star-v0.md`](agent-existence-north-star-v0.md)

---

## KB (канон) → ребёнок (автономия)

**«Канон»** здесь — **KB** (clusters: `language`, `research`, `goals`, math, tech, …), не только markdown в `design/`. Design описывает **контракт субстрата**; KB — **материал цивилизации**, который ребёнок **слушает и сжимает**, а не «база для Cursor».

| Роль | Кто | Что делает |
|------|-----|------------|
| **KB / корпус / teacher** | взрослые, ingest, benches | extract claims, bundles, listen mass — **вход** |
| **Субстрат («ребёнок»)** | CASA, автономный **T-цикл** | listen → surface → critic → hippo → **sleep** → use — **своя** память на поле |
| **Lab-скрипты сегодня** | инженерия | batch L3, gate, NCA — **bootstrap и проверка**, не финальная жизнь агента |

**North star** ([`agent-existence-north-star-v0.md`](agent-existence-north-star-v0.md)): **autonomous persistence** — агент крутится **без человека в каждом шаге**; KB на диске ≠ «мысль агента», как git ≠ «я». RAG-обман для обоих: ответ из chunk ≠ понимание. Цель — структура на **T0…T3 / F0…F2**, накопленная через **Extract → Remember → Use** ([`understanding-contract-v0.md`](understanding-contract-v0.md)).

Поэтому **нейтральные z-роли** (APLF) + **профили доменов**: KB уже многообластный; сейчас lab в **языковой фазе** ([`infancy-corpus-phases-v0.md`](infancy-corpus-phases-v0.md)), но финал — ребёнок сам переваривает **весь** канон (math, tech, vis, …) в **своём** store, не через наши одноразовые `*_ingest_v0.py`.

```text
  KB (много clusters) ──listen/ingest──► цилиндр (T + F стеки)
         │                                      │
         │  teacher / correct (фазы 0–3)        │  T-loop: wake + sleep
         └──────────────────────────────────────┴──► автономия (gate, kb_watcher, probe)
```

**Не забываем:** merged preview, POS batch на T3, T9 gate — **Track A/C для нас**; для ребёнка то же должно вырасти из **surprise → Extract → run_sleep()**, иначе это только диск, не понимание.

---

## Почему «L0…L3» путаются (и что делать)

**Проблема:** буква **L** + цифра — **общий дефицитный ресурс** во всей экосистеме (KB, CIDE, CASA), не только внутри поля. «L2» без префикса может значить: лемму на решётке, **глубину загрузки KB**, **comprehension по Endsley**, **режим confirm-edits в CIDE**, shard NCA, episodic rule…

**Решение v0:** в **прозе** голый **`L0`…`L3` не использовать**. Всегда — **префикс шкалы** (K / SA / SL / T / …) или **имя роли** + literal ID в скобках.

### Карта коллизий (экосистема)

| Шкала | Где | Что значит | **Как говорить** | Literal ID / канон |
|-------|-----|------------|------------------|-------------------|
| **KB depth** | agent-notes, SHOWCASE, router | глубина **загрузки** канона: ядро → playbook → archive → routing | **K0…K3** (KB-tier) | в KB-тексте часто «L0…L3» — тогда явно **«KB L2»** или **K2** |
| **Endsley SA** | CIDE ADR 0021, PFD | ситуационная осведомлённость: perception → comprehension → projection | **SA1…SA3** | «L1 Perception» в ADR → **SA1**, не путать с Safety |
| **CIDE Safety / IOP** | Cascade IDE, coexistence | **автономия агента в IDE**: read-only → confirm → bounded autonomous | **SL1…SL3** (Safety Level) | код/UI: `safetyLevel` `"L1"`…`"L3"` — в prose **SL2** |
| **CASA z (2-я СС)** | `casa-ontology-payload`, store | решётки знаков на цилиндре | **T0…T3** (APLF) | `L0_*`, `L2_word_*`, `L3_phrase` |
| **Bukvar** | listen curriculum | B0→B3 педагогика | **B0…B3** | → T0…T3 |
| **Hippo episodic** | `prism_hippo` | surprise до sleep | **H1…H3** | `H1_surface`, … |
| **Math (1-я СС)** | F-stack | schema → compose → quantity | **F0…F2** | `F0_schema`, … |
| **Infancy** | corpus phases | timeline взросления | **фаза 0…5** | не z_level |
| **Exp L** | Experiment L | урок concrete→abstract | **Exp L0…L4** | не lattice L3 |

**Особо коварно в CIDE:** в одном ADR (`cascade-ide/docs/adr/0021-pfd-mfd-cockpit-attention-model.md` §11 и §12) **Endsley L1–L3** и **Safety L1–L3** — **разные оси**, цифры совпадают. «L2 в кокпите» без уточнения = SA2 *или* SL2.

#### KB (K0…K3) — глубины памяти канона

См. `knowledge/SHOWCASE.md`, контракт загрузки agent-notes:

| Tier | **K*** | Смысл (кратко) |
|------|--------|----------------|
| K0 | always-on | integrity, epistemics, POST core |
| K1 | operational | status → playbook → matrix → kb по scope |
| K2 | archive | revisions, evidence, history |
| K3 | routing | semantic router, transfer boundaries |

Это **не** «слой поля CASA» и **не** «сколько агент автономен в IDE».

#### CIDE: Endsley (SA*) vs Safety (SL*)

| | **SA** (Endsley) | **SL** (Safety / IOP) |
|---|------------------|------------------------|
| **Вопрос** | «Что оператор **понимает** о ситуации?» | «Кто **действует** — человек или агент?» |
| **1** | SA1 — perception (build fail, badges) | SL1 — assistant, read-only |
| **2** | SA2 — comprehension («2 errors in PaymentService») | SL2 — confirm edits |
| **3** | SA3 — projection («если смержить — CI упадёт») | SL3 — autonomous bounded execution |

North star CASA ([`agent-existence-north-star-v0.md`](agent-existence-north-star-v0.md)): автономия **субстрата** (T-loop) **≠** SL3 в IDE — human-in-the-loop для опасных действий остаётся.

### Карта коллизий (CASA-only, было раньше)

| Если слышишь… | Это **не** то же самое, что… | **Как говорить** | **ID в коде** (если нужен) |
|---------------|-------------------------------|------------------|----------------------------|
| z-решётка памяти (2-я СС) | K2, SA2, SL2, фаза 2 | **T0…T3** (APLF) | `L0_*`, `L2_word_*`, `L3_phrase` |
| Педагогическая лестница букваря | z_level manifest | **B0…B3** | → **T0…T3** |
| Episodic (hippo) | LTM, KB archive | **H1…H3** | `H1_surface`, … |
| Логика / quantity | знаки языка | **F0…F2** | `F0_schema`, … |
| Фазы infancy | z=2 | **фаза 0…5** | [`infancy-corpus-phases-v0.md`](infancy-corpus-phases-v0.md) |
| Sidecar / prior | любой L/K tier | **не слой** — `lexicon_axes` | — |

```text
  ШКАЛЫ ЭКОСИСТЕМЫ (префикс обязателен в смешанном разговоре):

  K0──K3     KB load depth (канон на диске)              ← «KB L2» в цитатах
  SA1──SA3   CIDE Endsley (PFD: понимание ситуации)
  SL1──SL3   CIDE Safety / IOP (автономия в IDE)
  T0──T3     CASA semantic z (2-я СС)                   ← поле / ребёнок
  L0──L3     CASA lattice_id ONLY (store/nca/manifest)
  B0──B3     bukvar curriculum
  H0──H3     hippocamp episodic
  F0──F2     first signal / math
  фаза 0–5   infancy timeline
```

### Три слоя имён (твой запрос: semantic / anatomical / ID)

| Слой | Для кого | Пример |
|------|----------|--------|
| **Semantic (роль)** | доки, KB, разговор с человеком | **T2 лексема**, **T3 связка/hub** |
| **Profile gloss (домен)** | когда домен ясен | **слой слова**, **слог**, **схема** (math) |
| **Anatomical (физика CASA)** | layout, cylinder, stack | **решётка** `L2_word_07`, **цилиндр** `prism_memory`, **z_bridge** T1→T2 |
| **ID (immutable)** | код, manifest, пути | `L2_word_07`, `L3_phrase` |

**Правило одной строки:** CASA смысл → **T2**; KB глубина → **K2**; кокpit понимание → **SA2**; IDE автономия → **SL2**; literal решётка → `` `L2_word_07` ``.

### Примеры «было → стало»

| Плохо (перегруз Lx) | Хорошо |
|---------------------|--------|
| «Подтяни L2 из KB» | **K2** / evidence tier; или **K1** playbook — по смыслу |
| «L2 в CIDE» | **SA2** (comprehension в PFD) *или* **SL2** (confirm edits) — уточнить |
| «На L2 лежит entity» | entity на **T3**; лемма на **T2** |
| «L3 autonomous + L3 routing» | **SL3** (IDE) + **K3** (KB router) — разные миры |
| «L3 ingest на sleep» | batch на **T3** — не hippocamp sleep |
| «Фаза 2 пишет в L2» | **фаза 2** → co-activation на **T2** |

### Когда `Lx` в тексте всё же ok

- Цитата **literal** `lattice_id` из manifest или лога.
- Таблица «display name ↔ **ID**» (как ниже).
- Refactor/coding task, где речь **только** о путях `nca/L2_word_36/`.

Во всех остальных случаях — **K / SA / SL / T / B / H / F / фаза** или слова **Примитив / Лексема / …**.

**Scope документа:** префиксы **K / SA / SL** — для смешанных диалогов KB+CIDE+CASA; детали KB — SHOWCASE; CIDE — ADR 0021 §11–12, coexistence-framework; CASA lattice — ниже по файлу.

---

## Главная идея

Сейчас lab **занят языком** — поэтому в разговоре часто слышно «буква → слог → слово → фраза». В каноне это **не универсальные имена всего CASA**, а **один профиль** на общей лестнице **z-уровней**.

| Что | Смысл |
|-----|--------|
| **z-уровень (T0…T3)** | Роль **решётки** на цилиндре: примитив → паттерн → именованная единица → связки/роли. **Домен-агностично.** |
| **Профиль домена** | Как эта роль **наполняется** в конкретной подсистеме: язык (L0…L3), логика (F0…F2), позже vis, motor… |
| **Корпус / store** | Какой **материал** вливается в тот же z (folk vs tech, RU vs EN) — [`agent-store-catalog-v0.md`](agent-store-catalog-v0.md) |

```text
  ┌─────────────────────────────────────────────────────────────┐
  │  1-я сигнальность (опыт)     │  2-я сигнальность (знаки)    │
  │  F0…F2 math, vis.*, motor…   │  L0…L3 SSS (+ z_bridge)      │
  │  f_bridge_* ────────────────►│  hub на T3 / L3               │
  └─────────────────────────────────────────────────────────────┘
           один буфер (x,y,z), разные регионы и concept_prefix
```

**Не путать:** «слог» — gloss **языкового** профиля на **T1**; «схема `M:op:add`» — gloss **math** на **F0**. Оба — z-лестницы, разные подсистемы.

---

## Правило для ID

| Статус | Правило |
|--------|---------|
| **v1 (цель)** | Осмысленные id: `alphabet-ru`, `words-en-03`, `phrases` — см. [`lattice-naming-v1.md`](lattice-naming-v1.md) |
| **v0 (сейчас в store)** | Талоны `L0_*`, `L2_word_*` — **мигрируем**, не священны |
| **Переход** | `tools/lattice_names_v1.py` — map + builders; hot path принимает оба формата |

Причина смены: по `L2_word_47` не видно ни языка, ни роли; `words-ru-47` — читается сразу.

---

## Нейтральные роли (ось z_level, 2-я СС / SSS)

Общая мнемоника для **любого** знакового стека:

```text
  T3 Frame   — связи, роли, entity, grammar, dialog
     ↑ bind
  T2 Lexeme  — именованные единицы в словаре домена
     ↑ compose
  T1 Pattern — локальная композиция примитивов
     ↑ compose
  T0 Atom    — минимальный знак домена (ввод, stroke, code unit)
```

| z | **Роль RU** | EN | Что абстрактно |
|---|-------------|-----|----------------|
| **0** | **Примитив** | **Atom** | атом ввода / кода / штриха |
| **1** | **Паттерн** | **Pattern** | короткая композиция (слог, digram, stroke-seq) |
| **2** | **Лексема** | **Lexeme** | устойчое имя в словаре (lemma, command, id) |
| **3** | **Связка** | **Frame** | hub, POS, taxonomy, collocation, turn |

**Мнемоника:** *«ППЛС»* / EN **APLF** (Atom → Pattern → Lexeme → Frame).

---

## Профиль: язык (SSS, IDs `L0…L3`)

Текущий lab — **language profile** поверх T0…T3:

| z | ID (канон) | Нейтрально | **Язык RU** | **Язык EN** | concept_prefix (типично) |
|---|------------|------------|-------------|-------------|---------------------------|
| 0 | `L0_*` | Примитив | **Знак** | Sign | `grapheme.*`, `vk.*`, `layout.*`, `punct.*` |
| 1 | `L1_syllable` | Паттерн | **Слог** | Syllable | `syllable.*` |
| 2 | `L2_word_*` | Лексема | **Слово** | Word | `lang.word.*` |
| 3 | `L3_phrase` | Связка | **Фраза** | Phrase / discourse | `entity.*`, `pos.*`, `ru.dialog.*` |

Кратко для **только языкового** контекста: **ЗССФ** / **SSWP** (Sign → Syllable → Word → Phrase) — **синонимы T0…T3**, не отдельная ось.

### Подслои L0 (семейства на T0, не отдельный z)

| ID | Язык RU | EN | Роль |
|----|---------|-----|------|
| `L0_grapheme_cyrl` / `_latn` | Алфавит | Alphabet | immutable буквы |
| `L0_vk_physical` | Клавиши | Keys / VK | физические key codes |
| `L0_layout_*` | Раскладка | Keyboard layout | key → grapheme |
| `L0_punct_*` | Пунктуация | Punctuation | `.`, `,`, `?` … |

В тексте: «на **T0 / примитиве**, решётка **раскладка**» или «на **слое знака**» — оба ок.

### Корпус ≠ z-уровень

`sss-ru-general-v0`, `sss-en-folk-v0`, `sss-*-tech-v0` — **разные stores**, один и тот же **T2 / L2** (лексемы). Оси `lexicon_axes` (ipm, era) — sidecar для **T2**, не «L2.5».

---

## Профиль: логика / math (1-я СС, IDs `F0…F2`)

Отдельный стек **первой сигнальности** — не «слоги и фразы»:

| z | ID | **Имя RU** | EN | Пример |
|---|-----|------------|-----|--------|
| 0 | `F0_schema` | **Схема** | Schema | `M:sym:two`, `M:op:add` |
| 1 | `F1_compose` | **Композиция** | Compose | `M:inst:cow@a`, `M:inst:cow@b` |
| 2 | `F2_quantity` | **Количество** | Quantity | `M:qty:2×cow` |

Мосты `f_bridge_*` связывают **F2 ↔ T2 (слово) ↔ vis** через hub, не merge решёток. См. [`f0-math-logical-layer-v0.md`](f0-math-logical-layer-v0.md).

**Пример «корова + корова»:** картинка / `M:unit:cow` — **F**; «корова», «две» — **T2 языка**; entity `Animal/COW` на **T3** — общий hub для disambiguation и sleep ingest.

---

## Roadmap: другие области (не язык)

| Область | Подсистема | z / stack | Gloss на T0…T3 или свой F |
|---------|------------|-----------|---------------------------|
| **Язык** (folk, tech, archaic) | 2-я СС | `L0…L3` | Знак → Слог → Слово → Фраза |
| **Math / quantity** | 1-я СС | `F0…F2` | Схема → Compose → Quantity |
| **Vision** (roadmap) | 1-я СС | `vis.*`, Exp L | образ / сцена — не в SSS |
| **Motor / write** (roadmap) | 1-я СС + мост | stroke → compose | ADR-0005 |
| **Tech lexicon** | 2-я СС, **тот же L2** | `sss-*-tech-v0` | T2 = команды IDE/KB, T3 = entity/rules |

**x (домен) на layout:** отдельный регион цилиндра для другой 1-й СС (`F0_vis`, …) — [`bukvar-text-modality-v0.md`](bukvar-text-modality-v0.md). Имена **T0…T3** остаются; меняется **профиль** и `concept_prefix`.

---

## Hippo (episodic) — отдельная ось, не T0–T3

Цилиндр **`prism_hippo`**, не z_level долговременной памяти:

| ID | Имя RU | EN | Кристаллизует на sleep в… |
|----|--------|-----|---------------------------|
| `H1_surface` | Surface-эпизод | Surface episode | **T2 / Слово** (L2) |
| `H2_rule` | Правило | Rule episode | **T3 / Фраза** (L3) |
| `H3_scene` | Сцена | Scene episode | **T3 / Фраза** (L3) |
| `H0_episode` | *(legacy)* | — | monolith до split H1–H3 |

Кратко: **«эпизод на hippocamp»**, не «L4».

---

## Control stack (не z памяти)

| ID | Имя | Роль |
|----|-----|------|
| `lattice_dmn_digest` | **DMN** | digest, listen encode |
| `lattice_sn_gate` | **SN** | salience / gate |
| `lattice_fpn_wm` | **FPN** | рабочая память между тиками |
| `lattice_cen_act` | **CEN** | act / articulate |

См. [`control-lattice-stack-v0.md`](control-lattice-stack-v0.md).

---

## Как писать в новых доках

**Узко (только язык, ok в BiT9/T9 doc):**
> **Знак** → **Слово** (T9) → **Фраза** (entity hub)

**Широко (канон, несколько областей):**
> **T2 лексема** (RU `корова`, EN `cow`) + **T3 entity** (`Animal/COW`) + **F2 quantity** (`2×cow`) — через hub, не одна ячейка

**Было (рябит ID):**
> L0/L1 script → L2 T9 → L3 entity hub на L3_phrase

**Стало:**
> **T0 раскладка** → **T2** (T9) → **T3** (entity hub)  
> *(IDs: L0 layout + L2_word_* + L3_phrase)*

| Имя | ID | Содержимое |
|-----|-----|------------|
| Оси частоты (не слой!) | `lexicon_axes` sidecar | ipm, era — prior для **T2** |
| Понятийный граф | **T3** `L3_phrase` | entity, POS, taxonomy |
| Эпизод surprise | **hippo** `H1_*` | Extract → sleep → **T2/T3** |

---

## Sidecar `lexicon_axes` — не уровень z

**Не называть** «L2.5» или «L4». Метаданные леммы для **T2**, см. [`lexicon-usage-axes-v0.md`](lexicon-usage-axes-v0.md).

---

## Roadmap (опционально, не v0)

| Идея | Риск |
|------|------|
| `display_name` + `profile: language|math` в `sss-lattice-stack.v0.toml` | низкий |
| Alias map в `sss_stack_v0.py` для логов (T0 + profile gloss) | низкий |
| Rename `L2_word` → `LexemeLattice` в ID | **высокий** — major version |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-31 | v0: Знак / Слог / Слово / Фраза + подслои L0 + hippo/control |
| 2026-05-31 | v0.1: нейтральные T0…T3 (APLF), язык как профиль; F0…F2 и roadmap областей |
| 2026-05-31 | v0.5: lattice v1 names — [`lattice-naming-v1.md`](lattice-naming-v1.md); migrate off L talons |
