# CASA-ADR-0002: память агента — KB, поле, ltm-pack и NCA (не «только model.pt»)

**Статус:** принято (lab v0, 2026-05-30)  
**Область:** SSS / agent store / поставка лексикона  
**Связано:** [`ltm-pack-v0.md`](ltm-pack-v0.md), [`memory-hierarchy-v0.md`](memory-hierarchy-v0.md), [`l2-lattice-sharding-v0.md`](l2-lattice-sharding-v0.md), [`nca-train-defaults.v0.json`](nca-train-defaults.v0.json), канон KB (`agent-notes`, `kb-one-pager-structure-and-protocols-v1.md`)

---

## Контекст

### Как устроен канон KB

База знаний в **agent-notes** — не «тонна текста в контексте», а **структура**:

| Элемент KB | Роль |
|------------|------|
| Слои **L0–L3** | что всегда в силе → оперативка по домену → архив/evidence → семантический роутинг |
| **Домен** | ось темы (Git, язык, HCI, …) |
| **Понятие** | `concept_id`, карточки, слоты |
| **Факт** | `claims` (`claim`, `rule`, `concept`, …) |
| **Связь** | `graph`: узлы и рёбра (`src`, `relation`, `dst`) |

Загрузка по контракту: **status → playbook → matrix → kb** — тяжёлое только по запросу.

**Тот же принцип на поле:** не RAG по `field_state.json`, а **смыслы на решётках** + цикл listen → babble → correct → sleep. См. [`language-acquisition-loop-v0.md`](language-acquisition-loop-v0.md) § «Смысл, не RAG», контракт [`understanding-contract-v0.md`](understanding-contract-v0.md).

### Как устроена память на поле (SSS)

Память агента в треке CASA — **та же идея, другая проекция**:

| KB | Поле (цилиндр памяти) |
|----|------------------------|
| Слои знаний | Решётки **L0…L3** на оси z (+ шардированный L2) |
| Домен / scope | bundle ingest, маршрут SN, полка `L2_word_XX` |
| Понятие | токен `C:…` на сетке |
| Факт / правило | claim в bundle → отпечаток при listen |
| Связь | рёбра графа → `E:*`, соседство на grid, **z-bridge** между уровнями |

**Память** в инженерном смысле — **пространственная связь между полями**; **элемент клетки** — токен (слово, понятие, ребро), а не абзац Markdown.

### Что пошло не так в ожиданиях

1. **`model.pt` (~2 MiB на полку)** выглядит как «вся память в нейросети» — обучение NCA действительно учит **восстанавливать поле после повреждений**, но **не хранит лексикон в весах**.
2. **`field_state.json` (~400 MiB)** — удобная лабораторная копия, но сериализация **дублирует строки токенов** в `cells[]`; это не модель данных, а артефакт JSON.
3. Путаница: маленький NCA ≠ «памяти нет»; маленький NCA = **дешёвая физика ремонта** при том, что **знание на поле** (или в компактном `ltm/`).

---

## Решение

### 1. Разделить три роли (не смешивать в одном файле)

| Артефакт | Что это | Поставка (prod) |
|----------|---------|-----------------|
| **KB / bundle** | канон: claims + graph, редактируемый источник | git / kb-public / ingest |
| **`ltm/`** | компактная **раскладка** памяти на решётках (vocab + placements) | **да** |
| **`nca/<lattice>/model.pt`** | локальное правило **repair/regrow** для этой полки | **да** |
| **`nca/rules/<rule_id>/model.pt`** | **NCA_rule**: repair/regrow **validated rule patch** (v1+; та же math, gate = Critic) | **да** (когда есть rules) |
| **`field_state.json`** | полный runtime-state (в т.ч. episodic, версии) | **лаб**, не обязателен в дистрибутиве |

Формула поставки агента с лексиконом:

```text
память (структура на поле)  =  ltm/
repair лексикона             =  nca/<lattice>/          (L0–L3, L2 shards)
repair выведенных правил     =  nca/rules/<rule_id>/    (после Critic; та же regrow-math)
канон правды                 =  KB → ingest
```

### 2. Принять **ltm-pack v0** как формат памяти для отгрузки

- Бинарник `.ltm` на решётку: словарь токенов один раз + sparse `(token_idx, x, y)`.
- `pack.manifest.json`: `l2_sharding`, реестр `nca.models`, метаданные решёток.
- Измерено на `sss-ru-lexicon-v0`: **~2,6 MiB** на весь L2 (65 решёток) против **~429 MiB** `field_state.json` при том же содержимом `cells`.

Инструменты: `export_ltm_pack_v0.py`, `import_ltm_pack_v0.py` — см. [`ltm-pack-v0.md`](ltm-pack-v0.md).

### 3. NCA — «иммунитет поля», не энциклопедия (v0)

- Обучение: целевой тензор `[K,H,W]` с полки после listen/remigrate; loss — вернуть паттерн после damage.
- Размер мал, потому что в весах **динамика CA**, а не 42k лемм.
- Обучение по канону: [`nca-train-defaults.v0.json`](nca-train-defaults.v0.json), режим **windowed** по умолчанию для шардов L2.

**v1 (roadmap, не отменяет v0):** **`NCA_rule`** — **тот же** damage→regrow, что lexicon repair, но на **patch правила** (`H2` / `L3` rule region / `F2`). Обучается **только** на snapshot после pass **Critic** (Predict → validate). Без validate — правило не получает regrow-weights. См. [`understanding-contract-v0.md`](understanding-contract-v0.md) § «Два NCA repair».

```text
nca/
  L2_word_07/model.pt              # NCA_repair (v0, есть)
  rules/ru.case.dative.after_soglasno/model.pt   # NCA_rule (v1, roadmap)
```

### 4. Выровнять дорожную карту с моделью KB

**Сейчас (v0):** KB/bundle → listen/import → `field_state` → export → **`ltm/`** + train → **`nca/`**.

**Цель (v1, не блокирует v0):** KB bundle (claims + graph) → **прямая проекция** в `ltm/` без промежуточного монстра JSON; `field_state` только в RAM на время tick/sleep.

---

## Обоснование

| Альтернатива | Почему отклонена |
|--------------|------------------|
| Поставка **только `model.pt`** | NCA не знает, *что* восстанавливать, без раскладки на поле |
| Поставка **только `field_state.json`** | раздувает дистрибутив и путает сериализацию с моделью памяти |
| Хранить лексикон **внутри весов NCA** | потребовало бы порядка весов как у LLM; противоречит «ontology in field» |
| Один монолит **L2_word** без шардов | NCA по `k` каналам неподъёмен на одной решётке (~41k слов) |

Принятое решение сохраняет **модель «память = связи на полях»** и **дух KB** (структура, не простыня), и даёт **лёгкую поставку** (~3 MiB ltm + ~130 MiB nca на полный RU-лексикон — оценка по числу полок).

---

## Последствия

### Плюсы

- Дистрибутив и бэкапы разумного размера.
- Ясная семантика для команды: память = поле, repair = NCA.
- Round-trip `export → import` проверен на `cells` (lab).

### Минусы / долг

- Рантайм должен уметь **грузить `ltm/`** без обязательного `field_state.json` (сейчас import пишет в state — нужен loader в hot path).
- Episodic (`cyl_hippo`), `field_version`, sleep-история — **вне** v0 pack; отдельный контур или tier B.
- Прямой **bundle → ltm** ещё не реализован (ADR фиксирует направление).

### Что не меняется

- KB остаётся **источником правды** для фактов и графа.
- Имя корпуса (Afan, bukvar) **не** задаёт структуру store (`sss-ru-lexicon-v0`, не `sss-afan-*` в layout).

---

## Проверка (критерии принятия v0)

- [x] Export L2 → `ltm/` ≤ 5 MiB при ~42k слов (факт: ~2,6 MiB).
- [x] Round-trip `L2_word_00.cells` идентичен.
- [x] NCA windowed по умолчанию; дефолты в `nca-train-defaults.v0.json`.
- [ ] Runtime: agent store стартует из `ltm/` + `nca/` без `field_state.json` на диске.
- [ ] Документирован tier поставки в [`examples/agent-stores/INDEX.md`](../examples/agent-stores/INDEX.md) (частично).

---

## Связанные решения и документы

| Документ | Роль |
|----------|------|
| `examples/kb/casa-adr-0001.payload.json` / ADR-0001 в agent-notes | трек CA-субстрата (отдельно) |
| [`ltm-pack-v0.md`](ltm-pack-v0.md) | спецификация формата и команд |
| [`nca-train-core-v0.md`](nca-train-core-v0.md) | общий цикл обучения NCA |
| KB `kb-one-pager-structure-and-protocols-v1.md` | слои L0–L3, домены, роутинг |

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-05-30 | Первая версия: ltm-pack v0, разделение память / repair / KB |
