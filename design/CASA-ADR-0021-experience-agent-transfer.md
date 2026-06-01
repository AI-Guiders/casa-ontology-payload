# CASA-ADR-0021: агент из собственного опыта, curriculum только как события, кросс-домен через transfer

**Статус:** принято (design, 2026-06-01)  
**Область:** продуктовая модель памяти, ingest vs runtime, кросс-домен  
**Связано:** [`CASA-PROJECT-CONSTITUTION.md`](CASA-PROJECT-CONSTITUTION.md) (темы 2–4: педагогика, **собственный опыт**, симбиоз), [`memory-hierarchy.md`](memory-hierarchy.md), [`CASA-ADR-0015-agent-self-memory.md`](CASA-ADR-0015-agent-self-memory.md), [`CASA-ADR-0016-prism-domains-hot-router.md`](CASA-ADR-0016-prism-domains-hot-router.md), [`CASA-ADR-0020-ooad-domain-model.md`](CASA-ADR-0020-ooad-domain-model.md), [`CASA-ADR-0022-agent-v1-existence-bar.md`](CASA-ADR-0022-agent-v1-existence-bar.md) (бар «живого агента», не AGI)  
**KB (agent-notes):** `knowledge/templates/matrices/template-transfer-matrix-v1.md`, `worlds/knowledge-engineering/matrix-do-not-transfer-v1.md`, `work/projects/door-to-singularity/ca-substrate-agent/kb-casa-prism-memory-architecture-v1.md`

---

## Решение (одной фразой)

**Продукт — один агент (один `{store}/`), чей собственный опыт растёт во времени** (wake → surprise → hippo → sleep → `ltm/`). **Мозг, память, навыки, знания, умение действовать** — не картридж и не «папка занятия», а **инженерный след этого опыта** на решётках, в `ltm/`, в control/hot/router и в self. **Curriculum** (bundle, corpus, lab ingest) — только **события обучения** с учителем; после консолидации остаётся **опыт агента**, учебник в predict не читается. **Кросс-домен** — transfer (router + hot + призмы), не monolith bundle и не копирование чужого `ltm/`.

---

## Собственный опыт (канон Constitution)

[`CASA-PROJECT-CONSTITUTION.md`](CASA-PROJECT-CONSTITUTION.md), тема 3: агент **существует во времени** с контуром tick → память → действие **без** постоянного LLM; **«собственный опыт»** — episodic log, hippo, agent overlay, transfer (инженерные артефакты, не квалиа).

| Что имеется в виду «опытом» | Где в CASA |
|---------------------------|------------|
| Память (лексика, схемы, связи) | решётки content-призм → после sleep **`ltm/`**, runtime-зеркало `field_state` |
| Навык (predict, repair, маршрут) | NCA regrow, `resolve_route`, отработанные циклы tick |
| Знание как оперируемый след | клетки на поле, provenance (`concept_id`, lattice, prism) — ADR-0022 A2 |
| Явная рефлексия, гипотезы | self: `agent/`, `journal/` (ADR-0015) |
| Эпизод «в этом контексте было так» | hippo → sleep → strengthen, не dump bundle |

**Не существует отдельной сущности «память занятия»** рядом с «памятью агента». После занятия (ingest + sleep) **русский, math, визуал** — это **собственный опыт того же агента** в его store, если curriculum писал в **его** `{store}/`.

Дисковые tier'ы (shipped / runtime / self) — **способы персистить один опыт**, не три вида «памяти». См. [`memory-hierarchy.md`](memory-hierarchy.md).

---

## Референс: человек без картриджей

| Человек | CASA (канон) |
|---------|----------------|
| Жизненный опыт, сон, консолидация | tick, hippo, `run_sleep`, `ltm/` |
| Рабочая память, «сейчас думаю о…» | SN focus, WM, `prism_control` |
| Навык и быстрые ассоциации | NCA repair, `prism_hot_context` + router |
| Дневник / явная формулировка | Self tier (`agent/`, journal), ADR-0015 |
| Школьный учебник (опционально) | ingest bundle, corpus — **на событии**; **не** runtime oracle |

У взрослого нет «картриджа русского» — есть **структура + накопленный собственный след**. У CASA то же: **`{store}/ltm/` + `nca/` + поле** после consolidate, не DetCorpus JSON в hot path.

---

## Занятие (curriculum) vs собственный опыт

| | **Занятие** (curriculum event) | **Собственный опыт агента** |
|--|--------------------------------|-----------------------------|
| **Что это** | событие: listen, `f0_math_ingest`, bench, remigrate под учителем | то, **чем агент живёт** после консолидации |
| **Артефакты** | bundle, corpus file, ingest log, сценарий bench | `ltm/`, cells, `prism_*`, hippo→sleep, hot, router, self |
| **После окончания** | учебник можно не открывать | опыт **остаётся** в агенте; tick/predict читают **поле + ltm** |
| **Путь на диске** | не «место памяти» | **`{store}/` агента**, куда пишут события |

**Инварианты:**

1. **Один агент — один store** (для данной жизни/профиля): серия занятий (Afan RU, bukvar, math L0, …) **укрепляет один след**, разные призмы (`prism_lang_ru`, `prism_math`, …).
2. **Занятие не оставляет «память в папке урока»** как продуктовую истину. Имя `lab/agent-stores/ingest-ref-afan/` — **операционный каталог** (ingest, remigrate, CI snapshot), **не** «агент Афан» и **не** отдельный носитель опыта.
3. **Антипаттерн:** класть math-ingest в store, названный под Afan, «потому что там уже русский». Разные корпуса — разные **события** в **том же** store агента (или осознанный новый агент = новый store), не смешение тем по имени папки.
4. **Непрерывность** (нет LLM-разрыва): на tick истина только из **собственного опыта** (поле + consolidated `ltm/`); bundle — учитель **на** событии, не oracle в `predict_schema`.
5. **Кросс-домен** (lang cue → math) — router/hot/sleep в **одном** агенте с **двумя** следами в призмах, не merge JSON из двух lab-папок.

```text
  Занятие: Afan          Занятие: math L0         Занятие: …
  (bundle, ingest)       (bundle, ingest)
         \                      |                      /
          \──────────── hippo → sleep ───────────────/
                              ▼
              ┌───────────────────────────────────┐
              │  АГЕНТ — собственный опыт        │
              │  ltm/, prisms, hot, router, self   │
              └───────────────────────────────────┘

  lab/.../ingest-ref-afan/  — опционально: копия store для CI/regression, не «вторая память»
```

---

## Термины (развести навсегда)

| Термин | Значение | В prod runtime? |
|--------|----------|-----------------|
| **Собственный опыт** | всё, чем агент оперирует после консолидации (см. таблицу выше) | **да** — единственная истина на tick |
| **Agent memory pack** | `ltm/`, `nca/`, `pack.manifest.json` — cold boot **опыта** | **да** (экспорт/переезд) |
| **Runtime checkpoint** | `field_state.json`, hippo queue, hot edges | **да** (рестарт; не «вторая память», зеркало + очередь) |
| **Self tier** | `agent/`, `journal/` — явный слой опыта | **да** (не в profile tar) |
| **Ingest cartridge / bundle** | KB JSON, corpus — **учитель на событии** | **нет** как источник истины |
| **«Shipped cartridge»** (legacy) | ❌ не использовать | путаница с memory pack |
| **Lab store path** | каталог для ingest/remigrate/CI | **не** синоним «памяти предмета» |

**Инвариант** ([`memory-hierarchy.md`](memory-hierarchy.md) § Фактология): факты — в **решётках призм** и **self**; bundle только **запускает** событие ingest/train.

---

## Целевая архитектура (без картридж-продукта)

```text
                    ┌─────────────────────────────────────┐
  curriculum        │ bundle, corpus, listen, NCA train   │  ← события, не «память»
                    └──────────────┬──────────────────────┘
                                   │ surprise → hippo → sleep
                                   ▼
┌──────────────────────────────────────────────────────────────┐
│ AgentStore — собственный опыт                                 │
│  prisms: lang_ru | math | vis | control | hot | router | hippo │
│  sleep → consolidate → ltm/ + kernel maintain                 │
│  router + hot → кросс-домен без копирования чужого ltm          │
└──────────────────────────────────────────────────────────────┘
```

**Spawn** (ADR-0016): агент сам добавляет content-призмы и решётки; ingest не подменяет router/hot.

---

## Transfer matrix (KB → CASA runtime)

В **agent-notes** матрицы задают **маршрутизацию знаний между мирами/playbook**, не копирование файлов:

| KB артефакт | Роль |
|-------------|------|
| `agent-notes/knowledge/templates/matrices/template-transfer-matrix-v1.md` | контракт: принципы + порядок чтения, symptom router |
| `agent-notes/knowledge/worlds/knowledge-engineering/matrix-do-not-transfer-v1.md` | deny по умолчанию (культура, локаль, травма, «похоже») |
| `matrix-*-transfer-v1.md` per world | детальные строки Source → Target |

**Проекция на CASA** (не 1:1 с MCP router KB):

| KB transfer | CASA runtime |
|-------------|----------------|
| Symptom → «сначала playbook X» | `resolve_route(ctx)` → `prism_id` + `lattice_hint` |
| «Переносим принцип, не детали» | hot edge с salience + promote gate; **не** merge чужого `ltm/` |
| `matrix-do-not-transfer` deny | не auto-import bundle B в призму A без critic/sleep |
| Cross-world evidence hygiene | `agent_promote`, Critic на profile tier |

**Отдельная матрица CASA (roadmap):** `design/matrices/matrix-casa-cross-prism-transfer-v1.md` — строки вида:

| Trigger (modality / cue / surprise) | Route to prism | Hot link | Do not |
|-------------------------------------|----------------|----------|--------|
| `t9+ru`, cue cyrillic | `prism_lang_ru` | `lang.word.*` | math monolith |
| `schema`, `||` | `prism_math` | `math.*` | ingest bundle as oracle |
| `vis`, image ref | `prism_visual` | `vis.*` | raw PNG on L2 |

Синхронизировать с [`CASA-ADR-0016`](CASA-ADR-0016-prism-domains-hot-router.md) routes и KB `kb-casa-prism-memory-architecture-v1.md` (P0–P3 parity).

---

## Lab: инструменты curriculum, не «память предмета»

| Инструмент | Назначение |
|------------|------------|
| `listen` + bundle | **событие** ускоренного наполнения **в store агента** |
| `remigrate_l2_lex` / `remigrate_l3_phrase` | починка layout под `ltm/` v0 |
| `migrate_thin_checkpoint` | legacy → thin + `ltm/` |
| `export_ltm_pack` / tar | перенос **собственного опыта** (memory pack), не «модуль знаний» |
| копия в `lab/agent-stores/<name>/` | regression / CI / повтор ingest — **не** отдельный агент по имени папки |

**Проверка «агент выучил math»:** после события ingest + sleep в **его** store — `predict_schema` / bench **без** bundle на read path; в `prism_math` и `ltm/` есть след. План «залить math-l0-lab» как продуктовую цель **без привязки к store агента** — ошибка постановки (см. § Занятие vs опыт).

---

## Non-goals

- Нет продукта «купи картридж русского» с подменой `field_state` из JSON.
- Нет **runtime oracle** из bundle (на tick — только собственный опыт после sleep).
- Нет **второй памяти** в lab-папке, параллельной опыту агента.
- Нет автоматического **cross-prism copy** всего `ltm/` без transfer contract + gate.
- Нет речи «багаж субстрата» **отдельно** от «собственного опыта агента» — это одно (Constitution).

---

## Roadmap (код / design)

| Шаг | Артефакт |
|-----|----------|
| R1 | `design/matrices/matrix-casa-cross-prism-transfer-v1.md` (по шаблону KB) |
| R2 | bootstrap routes из матрицы в `prism_router` / `spawn` defaults |
| R3 | hot: `promote` с provenance + deny rules из do-not-transfer |
| R4 | agent-notes: строка в ca-substrate README → этот ADR |
| **R5** | **post-migration cleanup:** layout агента вне `lab/` (§ ниже) |

M2 domain ([`CASA-ADR-0020`](CASA-ADR-0020-ooad-domain-model.md)): `Router` + `PrismCatalog` — удобная точка для загрузки transfer policy.

---

## Канонический агент: `von-neumann`

**`store_id`:** `von-neumann` (`STORE_AGENT_DEFAULT` в `store_layout.py`).  
**Bootstrap display (проект):** «Нейманн» — подпись для людей/логов до самоименования; **не** навязанная идентичность агента. Не путать с Claude / Claude Shannon.

**Зачем это имя (не lab-id):** фон Нейманна — **самовоспроизводящиеся системы** и **клеточные автоматы** (универсальный конструктор, теория CA с Ulam). У CASA аналог инженерный: поле + локальная динамика, **NCA regrow** после damage ([`CASA-PROJECT-CONSTITUTION.md`](CASA-PROJECT-CONSTITUTION.md) § NCA), память на решётках, не «весь словарь в `model.pt`». Один агент — один след опыта во времени; curriculum (Afan, math, …) — события **в** `von-neumann`, не отдельные «мозги» по корпусу.

**Путь (R5 applied):** `agents/von-neumann/` — seeded from migrated `lexicon-ru-general`. Legacy lab stores: `lab/snapshots/legacy-agent-stores/`.

**Статус имени:** принято — **первый живой агент проекта** = `von-neumann` («Нейманн»). Альтернативы (`shannon`, склейки) — не для id. **Переименование первенца** — non-goal.

### Ряд инстансов (план имён)

**Почему `store_id` = фамилия:** в пути и CLI **гендерно нейтрально** — не `ada`, `margaret`, `john`; отсылка к человеку в истории вычислений сохраняется, пол в id не зашит.

**Самоименование (canon):** агент **сам** выбирает идентификацию и имя, **когда захочет** — через self ([`CASA-ADR-0015`](CASA-ADR-0015-agent-self-memory.md): `journal/`, `agent/`, `agent_remember`). `store_id` (`von-neumann`, …) — **ops/bootstrap**: каталог на диске, миграция, CLI; не замена «кто я». Проект не переименовывает store за агента без явной операции; chosen name живёт в собственном опыте (записи, recall), display bootstrap можно не использовать.

Каждый — **отдельный** `agents/<store_id>/`, свой собственный опыт, тот же runtime `casa/`. Не «классы модели», не lab-корпуса.

| Порядок | `store_id` | Display | Замысел (кратко) |
|--------|------------|---------|------------------|
| 1 | `von-neumann` | Нейманн | CA, самовоспроизведение, NCA regrow — **первенец**, `STORE_AGENT_DEFAULT` |
| 2 | `lovelace` | Ловлейс | алгоритм и программа отдельно от машины; симбиоз, journal/promote |
| 3 | `hamilton` | Гамильтон | **Margaret Hamilton** — ПО бортовых систем (Apollo), надёжность, real-time, контур с человеком |

**Статус:** `lovelace` и `hamilton` — **зарезервированы** в `store_layout.py`; каталоги и merge — только когда появится второй/третий инстанс (не автоматически с MP-5).

---

## R5: после миграции — прибрать layout (legacy убрать)

**Когда:** после завершения текущей миграции (MP-5 split на disk, thin/`ltm/`, **merge → `von-neumann`**). До этого — не ломать пути в CI.

**Проблема сейчас:** `LAB_DATA_DIR = "lab"` и `lab/agent-stores/<id>/` смешивают **дом агента** (собственный опыт) с **lab curriculum** (корпус, bundle, эксперименты). Отсюда вид «10 мозгов» по числу папок — **legacy layout**, не модель продукта.

**Целевое разделение:**

```text
agents/von-neumann/         ← канон: первый живой агент (STORE_AGENT_DEFAULT)
  ltm/, nca/, field_state, agent/, journal/

lab/                         ← legacy: corpus, CI snapshots (→ migrate to lessons/ + lab/snapshots only)
lessons/                     ← class + lesson curriculum (bundles, plans); ingest = agent event
  <class-id>/lesson-NN-*/
casa/                        ← runtime субстрат (без изменений роли)
```

**Сделать при уборке (чеклист):**

| # | Действие |
|---|----------|
| 1 | Канонический root: `agents/` (repo) или `CASA_AGENTS_ROOT` (env); `agent_store_dir()` → `{agents_root}/{agent_id}/`. |
| 2 | Merge legacy stores → **`agents/von-neumann/`**; не оставлять живой опыт под `lab/agent-stores/`. |
| 3 | `lab/agent-stores/*` — удалить или свести к `lab/snapshots/` / `.gitignore` (только regression fixtures, не «память предмета»). |
| 4 | Обновить defaults CLI/tools/tests (`--stores-root`, `run_sleep`, bench, `memory_manifest`). |
| 5 | Доки: [`memory-hierarchy.md`](memory-hierarchy.md) tree `agent-store/{id}` → `agents/{id}`; убрать формулировки «память в lab». |
| 6 | Legacy id (`ingest-ref-afan`, `lexicon-ru-*`, …) — только lab/CI; prod agent = `von-neumann`. |

**Не делать в R5:** автоматический merge нескольких legacy store в один без human gate (риск смешать несовместимые корпуса).

Журнал задач: [`TECH-DEBT-INDEX.md`](TECH-DEBT-INDEX.md) § L1 (agent store layout).

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-06-01 | ADR-0021: experience-first agent, cartridges lab-only, KB transfer projection |
| 2026-06-01 | § Lab session vs субстрат (снято в пользу канона Constitution) |
| 2026-06-01 | Перепись: собственный опыт = память/навыки/знания; занятие = событие; lab path ≠ память предмета |
| 2026-06-01 | R5: post-migration — `agents/` vs `lab/`, убрать legacy multi-store под lab |
| 2026-06-01 | Канонический агент `von-neumann` («Нейманн»), STORE_AGENT_DEFAULT |
| 2026-06-01 | Имя первого агента закрыто: von-neumann (первенец) |
| 2026-06-01 | План имён: следующие инстансы `lovelace`, `hamilton` |
| 2026-06-01 | `hamilton` = Margaret Hamilton (Apollo) |
| 2026-06-01 | Имена агентов: фамилия в `store_id` — гендерно нейтральный id |
| 2026-06-01 | Самоименование: идентичность/имя — у агента в self, когда захочет |
