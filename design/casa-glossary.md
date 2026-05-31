# CASA glossary v0 (термины и аббревиатуры)

**Status:** канон для design/ и кода lab  
**Date:** 2026-05-28  

Краткий словарь: **что означает**, **откуда название**, **где в репо**.  
Не биологический учебник — рабочие имена контракта, вдохновлённые large-scale brain networks (fMRI).

См. также: [`casa-layout.md`](casa-layout.md), [`casa-cosmos-mapping.md`](casa-cosmos-mapping.md), [`cen-sn-runtime.md`](cen-sn-runtime.md), [`agent-existence-north-star.md`](agent-existence-north-star.md).

---

## Существование и агентность (north star)

| Термин | Смысл |
|--------|--------|
| **Autonomous persistence** | Агент как **процесс во времени** (макро-тик **T**), не один ответ на промпт; персистентное поле + FPN. |
| **Rich medium** | Богатая среда: KB, IDE/MCP, позже embodiment (Cosmos) — по Alan Kay, не копия мозга. |
| **Агентность (engineering)** | Непрерывность, память, действие, repair, инициатива, provenance — **без** claim про квалиа. |
| **Duck test** | *If it looks like a duck and quacks like a duck, it's a duck* — наблюдаемые признаки «утки» = критерий существования агента в проекте. |
| **Квалиа** | **Вне scope** design/CASA; не блокирует roadmap. |
| **Consciousness** | **Open outcome**, not design requirement — не обещаем и не требуем. |

Канон: [`agent-existence-north-star.md`](agent-existence-north-star.md). KB: `ca-substrate-agent/agent-existence-north-star-v1.md`.

---

## Проект и стек

| Термин | Расшифровка | Смысл |
|--------|-------------|--------|
| **CASA** | *Context / CA Substrate Agent* (рабочее имя трека) | Агентный субстрат: KB → поле → SN/CEN → действие/текст. Канон: `ca-substrate-agent` в agent-notes. |
| **ca-substrate-agent** | id проекта / agent store | Lab: `casa-ontology-payload`, store: `lab/agent-stores/*`. |
| **Ontology in field** | «онтология в поле» | Смысл KB закодирован в **дискретном CA-поле** (токены), не только в векторном RAG. |
| **Payload** | `casa-ontology-payload` | Репозиторий lab: codec, NCA, import, SN/CEN. |
| **Agent store** | каталог агента | `field_state.json`, `bundles/`, checkpoints — персистентное состояние поля. |

---

## Тройка сетей (регионы поля)

Имена из нейронауки (**не** буквальная анатомия). На layout v0 — **три региона** одного поля 64×64:

```text
┌──────────────── DMN ────────────────┐
│         (память / онтология)       │
├──────────── SN ─────┬──── CEN ─────┤
│   (салиентность)   │  (план)      │
└────────────────────┴──────────────┘
     FPN v0 — вне grid или внутри CEN + IDE (см. § FPN)
```

### DMN — Default Mode Network (аналог)

| | |
|---|---|
| **Полное имя (англ.)** | Default Mode Network |
| **Роль в CASA** | **Память / онтология** — хранит bundle в виде токенов на grid, переживает damage, выдаёт **digest**. |
| **Регион layout** | `dmn_ontology` — прямоугольник x:0..31, y:0..63 |
| **Каналы (контракт)** | `tok.*` — дискретные токены; позже `emb.*` (stub) |
| **Код / артефакты** | `encode` → NCA **repair** → `decode`; `field_write.py`, `train_dmn_nca*.py` |
| **Cosmos-аналог** | **Predict** — «состояние мира», но у нас не видео, а token grid + `claims` |

**Digest** — сжатое представление после decode: список `concept_id`, рёбра, confidence — то, что уходит в SN по порту P1.

---

### SN — Salience Network (аналог)

| | |
|---|---|
| **Полное имя (англ.)** | Salience Network |
| **Роль в CASA** | **Маршрутизатор / салиентность** — что сейчас важно, открыт ли контур исполнения (**gate**), режим probe vs execute. |
| **Регион layout** | `sn_router` — x:32..63, y:0..31 |
| **Каналы** | `gate.*`, читает `digest.*` |
| **Код** | `sn_cen_runtime.sn_route()` → `GateState`, `GatedDigest` |
| **Cosmos-аналог** | часть функций **Reason** (что релевантно), но без VLM — детерминированный gate v1 |

**Не путать:** SN в CASA ≠ *Spiking Network* и ≠ *Serial Number*.

---

### CEN — Central Executive Network (аналог)

| | |
|---|---|
| **Полное имя (англ.)** | Central Executive Network (часто в паре с FPN — frontoparietal) |
| **Роль в CASA** | **Планировщик / исполнитель** — по digest и запросу пользователя выбирает **действие**: открыть KB, код, ответ из памяти, уточнить. |
| **Регион layout** | `cen_planner` — x:32..63, y:32..63 |
| **Каналы** | `task.*` — полоса задачи (intent, action, confidence) |
| **Код** | `sn_cen_runtime.cen_plan()` → `TaskEmit` / JSON `cen` в `sn_cen_infer.py` |
| **Cosmos-аналог** | **Reason** — план и решение «что делать дальше» |

**Арбитр:** в разговоре «арбитр = CEN» — верно для **политики действия**; SN **гейтит** вход в CEN (см. ниже).

В литературе CEN часто **пересекается** с FPN; в lab v0 мы **не выделяли** FPN отдельным регионом на grid.

---

### FPN — Fronto-Parietal Network (аналог)

| | |
|---|---|
| **Полное имя (англ.)** | Fronto-Parietal Network (task-positive control) |
| **Роль в нейронауке** | Удержание **задачи** в рабочей памяти, переключение правил, top-down внимание, многошаговый контур «что делаем сейчас» — не то же самое, что долговременная семантика (DMN). |
| **В CASA v0** | **Нет отдельного региона** в `layout.json`. Функции **частично** у CEN (`task.*`, `task_band`, multi-turn query) и **частично вне поля** — см. ниже. |
| **Статус** | **Gap / proposed** — явно назвать и при необходимости вынести в v1 layout или в agent session layer. |

**Где FPN уже «живёт» без имени:**

| Слой | FPN-подобная функция |
|------|---------------------|
| **CEN + `task.*`** | текущий intent/action, confidence, `query_to_dmn` |
| **SN + modules** | top-down: какие парцеллы/концепты активны под запрос |
| **Agent session** *(вне grid)* | многоход чат, активная цель, «о чём диалог» |
| **IDE** *(Cascade)* | chord/intent, PFD/MFD, активный файл — **исполнительный контур UI**, не DMN |
| **Будущая articulation MoE** | удержание режима ответа (grammar vs code vs cite) |

**Чего не хватает для «полного» FPN:**

- **Сквозное состояние задачи** между тиками **T** (не только один вызов `cen_plan`).
- **Стек подцелей** (plan → act → verify → replan), запись в поле или в session store.
- **Явный порт** «рабочая память задачи» (отличный от digest DMN).

**Варианты v1 (design, не реализовано):**

| Вариант | Идея |
|---------|------|
| **A. FPN ⊂ CEN** | Оставить один регион; расширить `task.*` + session API — минимальный diff. |
| **B. 4-й регион `fpn_control`** | Узкая полоса или угол grid: `wm.*` channels, читает/пишет CEN и SN. |
| **C. FPN вне CA** | `agent_session.json` + IDE; поле только DMN/SN/CEN; FPN = orchestration layer в cascade-ide / agent loop. |

**Рекомендация north star (2026-05-30):** **control lattice stack** — DMN/SN/FPN/CEN как отдельные решётки + `control_bridge` (см. [`control-lattice-stack.md`](control-lattice-stack.md)). Полосы на одном grid — [`fpn-control-region.md`](fpn-control-region.md) (historical). Session/IDE — зеркало на `lattice_fpn_wm`.

**Cosmos-аналог:** у Reason есть long-context и chain-of-thought; FPN ≈ **удержание плана рассуждения** между шагами, не генерация мира (Predict).

---

## Порты (мосты между регионами)

| Порт | Направление | Что несёт |
|------|-------------|-----------|
| **P1** | DMN → SN | **digest** — concept_ids, confidence |
| **P2** | SN → CEN | **gate** — режим, какие порты открыты (`p2_sn_to_cen`) |
| **P3** | CEN → DMN | запрос к памяти (опционально, future) — `query_to_dmn` |

В JSON infer: `sn.ports`, `digest`, `cen.targets`.

---

## Поршень и фазы (ось z)

| Символ | Значение |
|--------|----------|
| **x, y** | клетка на grid 64×64 |
| **z** | **фаза** пайплайна (encode → repair → digest → gate) — «сечение поршня» |
| **t** | микро-шаги CA внутри одной z |
| **T** | макро-тик агента (вне lab) |

См. [`layered-ca-pipeline.md`](layered-ca-pipeline.md).

---

## Поле, codec, bundle

| Термин | Смысл |
|--------|--------|
| **Bundle** | JSON: `graph` + `claims` + `concept_index` — единица знания перед кодированием. |
| **Claim** | Атом смысла: `text`, `concept_id`, `doc_path`, `section`, опционально `code_anchors`. |
| **concept_id** | Стабильный id (`ru.grammar.*`, `casa.goal.*`) → токен `C:...` на поле. |
| **Codec v3** | Правила укладки токенов: `C:` concept, `N:` doc, `E:` edge, `S:` section hub. |
| **field_state.json** | Снимок агента: grid, `claims_nav`, `field_version`, fingerprint. |
| **claims_nav** | Навигационный индекс для IDE/CEN: concept → doc, section, text. |
| **Union field** | Один grid из всех bundles в store (`rebuild_union_field`). |
| **NCA** | Neural Cellular Automata — локальное правило восстановления grid после damage. |
| **Damage / repair** | Патчи-дыры в DMN → rollout NCA → метрики F1 / recovery. |
| **Tile / window** | Подпрямоугольник DMN (напр. 32×32); NCA учится/чинит на **crop** с ghost-полосой. |
| **Ghost (margin)** | 1–2 клетки контекста вокруг тайла для 3×3 stencil; в loss не входят. |
| **Field planner v0** | `FieldPlannerV0` — очередь тайлов по плотности токенов (train sample / repair order). |
| **windows_per_batch** | Сколько crop'ов в одном GPU-forward за шаг (auto ≈48 на 8GB при canvas 36×36). |

Канон: [`windowed-field-and-planner.md`](windowed-field-and-planner.md). Код: `field_window.py`, `field_planner.py`, `train_dmn_nca_windowed.py`.

---

## Runtime SN/CEN (выходы)

| Поле JSON | Смысл |
|-----------|--------|
| **intent** | `query` \| `probe` \| `summarize` |
| **action** | `open_kb` \| `open_code` \| `answer_from_memory` \| `emit_digest` \| … |
| **targets[]** | Куда перейти: `kind` kb/code, paths, lines. |
| **answer_blocks[]** | Топ claims (текст, section, score) — Experiment J. |
| **answer_text** | Связная реплика: `articulation_grammar` (шаблон из claims), без LLM на hot path. |
| **query_to_dmn** | Запрос обратно в память при низкой уверенности. |
| **task_band** | Числовая полоса `task.*` для будущей записи в поле. |
| **llm_probe** | Заглушка внешнего LM — **не** hot path, не память. |

**Hot path:** `sn_cen_infer.py --from-field` — decode grid без NCA repair, **~7–12 ms** типично (p95 цель &lt;50 ms с букварём). NCA/LLM — не в hot path.

---

## Кластеры, модули, эксперименты

| Термин | Смысл |
|--------|--------|
| **Cluster** | Группа bundles для train (`goals`, `research`, `language`, …) — `kb-clusters.json`. |
| **Module** | Парцелла `(doc, section)` на grid — fMRI ROI analogy, `kb-modules.json`. |
| **Experiment G** | Tiered train: easy/hard bundles. |
| **Experiment K** | Code emit: KB → `Program.cs` → build/run; «угадай число» — [`experiment-k-code-emit.md`](experiment-k-code-emit.md) |
| **Experiment H** | Dual checkpoint infer (train vs hard model). |
| **Experiment J** | RU language KB + `answer_blocks` + bench answer@k. |
| **Experiment L** | Concrete→abstract: `math.*` schemas, `vis.*` images, букварь — [`experiment-l-concrete-to-abstract.md`](experiment-l-concrete-to-abstract.md). Логический стек F0…F2: [`f0-math-logical-layer.md`](f0-math-logical-layer.md). |
| **ССС (SSS)** | *Second signal system* — подсистема знаков; **стек решёток** по `z_level` + `z_bridge`. [`second-signal-system.md`](second-signal-system.md), [`sss-multi-lattice-z.md`](sss-multi-lattice-z.md). |
| **z_level** | CASA: индекс решётки по z — в prose **T0…T3** (APLF); ID `L0…L3`. **Не путать:** **K0…K3** (KB depth), **SA1…SA3** (CIDE Endsley), **SL1…SL3** (CIDE Safety) — [`sss-layer-names.md`](sss-layer-names.md) § коллизий. |
| **z_phase** | Фаза поршня **внутри** одной решётки (encode / repair / digest). |
| **z_bridge** | Пространственная связь между соседними `z_level` (compose, correct). |
| **Von Neumann (mapping)** | Перекладка классики (память/шина/CU/ALU/I/O) на CASA — [`von-neumann-casa-mapping.md`](von-neumann-casa-mapping.md). |
| **Prism blocks** (`prism_*`) | `prism_memory` + `prism_hippo` + `prism_control` в `prisms`; квадратные решётки по z — [`multi-cylinder-memory.md`](multi-cylinder-memory.md). |
| **Sleep** | `T_consolidate`: hippo → memory, без I/O — [`multi-cylinder-memory.md`](multi-cylinder-memory.md) § Sleep. |

---

## Продукция с поля (surface) — **не «лепет»**

**Канон с 2026-05-30:** инженерный термин — **`surface`** (modality / фаза UC).  
**`babble` / «лепет»** — **удалено** (2026-05-30); см. **`surface`**.

| Термин | Смысл | Код / modality |
|--------|--------|----------------|
| **predict** | **Читает** поле → конкурирующие якоря / гипотеза (`anchors[]`, T9, segment, schema) | `predictor`, `modality=t9` … |
| **surface** | **Синтезирует** строку **из digest** (черновик до critic) — «что поле *выдаёт* наружу» | `modality=surface`, `surface.py`, `bukvar_surface.py` |
| **articulate** | **Финальная реплика** после SN/CEN (pass critic, compose слотов) | CEN / `articulation_*` |
| **realize** | Связная фраза из слотов *(legacy naming)* — ближе к **articulate**, не к surface | realize v0 docs |

```text
  cue → PREDICT (anchors, внутреннее ожидание)
           → SURFACE (digest → черновик строки, self-test)
           → CRITIC (pass | surprise)
           → ARTICULATE (наружу пользователю / act)
```

| Hippo | Смысл |
|-------|--------|
| **`H1_surface`** | episodic: **неверный surface** → teacher correct → sleep → L1/L2 |
| `episode_kind=surface` | не `babble_wrong` в новом коде |

**Русский в prose:** «**вывод с поля**», «**surface-черновик**» — не «лепет» (путается с шумом и с детской метафорой).

См. [`understanding-contract.md`](understanding-contract.md), [`predictor.md`](predictor.md) § modalities, [`language-acquisition-loop.md`](language-acquisition-loop.md).

---

## Артикуляция и MoE (proposed)

| Термин | Смысл |
|--------|--------|
| **Articulation layer** | «Кора речи» — сборка **текста** из digest/claims; не DMN. |
| **MoE (в CASA)** | Явные **эксперты** compose (grammar, cite, code, dialogue), роутер у CEN/SN — не обязательно один transformer. |

---

## IDE и внешние аналоги

| Термин | Смысл |
|--------|--------|
| **CasaField.Core** | C# decode + SN/CEN для MCP `casa_field_infer`. |
| **CRS** | Correspondence Surface в IDE (ADR 0156) — doc↔code; дополняет, не заменяет SN/CEN. |
| **Cosmos Predict / Transfer / Reason** | NVIDIA WFMs для Physical AI — см. [`casa-cosmos-mapping.md`](casa-cosmos-mapping.md). |

---

## Частые путаницы

| Неправильно | Правильно |
|-------------|-----------|
| «SN = spike neural network» | **Salience Network** (контекст CASA) |
| «CEN генерирует весь текст как GPT» | CEN выбирает **действие**; текст — **answer_blocks** / будущая articulation |
| «CEN = FPN» | CEN — **момент решения**; FPN — **удержание задачи во времени** (v0 частично вне grid) |
| «DMN = LLM» | DMN = **поле + KB**; LLM только опционально вне hot path |
| «Поле = embeddings only» | Сначала **дискретные токены** + provenance; `emb_*` — опциональный слой |
| «babble / лепет = вся речь агента» | **`surface`** = черновик с digest; **`articulate`** = наружу; **`predict`** = якоря до critic |
| «babble = predict» | predict **читает** конкуренцию; surface **собирает** строку из digest |

---

## Input modality (keyboard / layout)

| Термин | Смысл |
|--------|--------|
| **PhysicalKeyEvent** | Layout-neutral key down/up; канон `key_id` = W3C `KeyboardEvent.code`. |
| **Layout decode** | `layout.qwerty_us` / `layout.jcuken_ru` — таблицы на **`L0_vk_map`** (рёбра к grapheme). |
| **Layout parity** | Dual decode + segment bias (prose → RU, `/command` → EN). |
| **core ltm** | Immutable ship pack (`L0_vk_map` + `L0_grapheme`); boot → field RAM. |

Канон: [`input-modality-vk-layout.md`](input-modality-vk-layout.md), ADR-0008.

---

## Файлы-якоря

| Тема | Путь |
|------|------|
| Input modality VK | `design/input-modality-vk-layout.md`, `tools/vk_decode.py` |
| FPN (layout B) | `design/fpn-control-region.md` |
| SN/CEN контракт | `design/cen-sn-runtime.md`, `tools/sn_cen_runtime.py` |
| Infer CLI | `tools/sn_cen_infer.py` |
| Cosmos mapping | `design/casa-cosmos-mapping.md` |
| Existence / duck test | `design/agent-existence-north-star.md` |
| fMRI modules | `design/modules-fmri-analogy.md` |
