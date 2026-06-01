# CASA-ADR-0021: агент из опыта, картриджи только lab, кросс-домен через transfer

**Статус:** принято (design, 2026-06-01)  
**Область:** продуктовая модель памяти, ingest vs runtime, кросс-домен  
**Связано:** [`CASA-PROJECT-CONSTITUTION.md`](CASA-PROJECT-CONSTITUTION.md) (тема 4 — симбиоз и опыт), [`memory-hierarchy.md`](memory-hierarchy.md), [`CASA-ADR-0015-agent-self-memory.md`](CASA-ADR-0015-agent-self-memory.md), [`CASA-ADR-0016-prism-domains-hot-router.md`](CASA-ADR-0016-prism-domains-hot-router.md), [`CASA-ADR-0020-ooad-domain-model.md`](CASA-ADR-0020-ooad-domain-model.md), [`CASA-ADR-0022-agent-v1-existence-bar.md`](CASA-ADR-0022-agent-v1-existence-bar.md) (критерии «живого агента», не AGI)  
**KB (agent-notes):** `knowledge/templates/matrices/template-transfer-matrix-v1.md`, `worlds/knowledge-engineering/matrix-do-not-transfer-v1.md`, `work/projects/door-to-singularity/ca-substrate-agent/kb-casa-prism-memory-architecture-v1.md`

---

## Решение (одной фразой)

**Продукт — один agent store, который накапливает опыт** (wake → surprise → sleep → `ltm/`). **Ingest-картриджи** — не «память для продажи», а **lab/curriculum pipeline** (как учебник ребёнку). **Кросс-домен** — через **transfer matrix** (принципы + маршрут), реализованный в runtime как **router + hot-context + призмы**, не как новый monolith bundle.

---

## Референс: человек без картриджей

| Человек | CASA (канон) |
|---------|----------------|
| Жизненный опыт, сон, консолидация | tick, hippo, `run_sleep`, `ltm/` |
| Рабочая память, «сейчас думаю о…» | SN focus, WM, `prism_control` |
| Быстрые ассоциации («это как в math») | `prism_hot_context` + router |
| Дневник / явная формулировка | Self tier (`agent/`, journal), ADR-0015 |
| Школьный учебник (опционально) | ingest bundle, corpus, **не** runtime oracle |

У взрослого нет «картриджа русского языка» — есть **структура мозга + накопленный след**. У CASA аналог shipped tier — **`{store}/ltm/` + `nca/`** после consolidate, а не DetCorpus JSON в hot path.

---

## Термины (развести навсегда)

| Термин | Значение | В prod runtime? |
|--------|----------|-----------------|
| **Agent memory pack** | `ltm/`, `nca/`, `pack.manifest.json` — cold boot профиля | **да** (экспорт/переезд store) |
| **Runtime checkpoint** | `field_state.json`, hippo queue, hot edges | **да** (рестарт процесса) |
| **Self tier** | `agent/`, `journal/` | **да** (не в profile tar) |
| **Ingest cartridge / bundle** | KB JSON, Afan corpus, `listen` batch | **нет** как источник истины; только **заливка** в поле |
| **«Shipped cartridge»** (legacy речь) | ❌ не использовать | путаница с memory pack |

**Инвариант** (из [`memory-hierarchy.md`](memory-hierarchy.md) § Фактология): факты живут в **решётках призм** и в **self**; bundle только **запускает** ingest/train.

---

## Целевая архитектура (без картридж-продукта)

```text
                    ┌─────────────────────────────────────┐
  lab (опционально) │ ingest bundle, remigrate, NCA train │
                    └──────────────┬──────────────────────┘
                                   │ заливка / ускорение детства
                                   ▼
┌──────────────────────────────────────────────────────────────┐
│ AgentStore (единственный организм)                            │
│  prisms: memory | math | vis | control | hot | router | hippo │
│  sleep → consolidate → ltm/ + kernel maintain (L2/L3 shards)  │
│  router + hot → кросс-домен без копирования чужого ltm         │
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

## Что остаётся от «картриджей» в lab

| Инструмент | Назначение |
|------------|------------|
| `listen` + bundle | ускоренное наполнение store (Afan, bukvar, math seed) |
| `remigrate_l2_lex` / `remigrate_l3_phrase` | починка layout под `ltm/` v0 |
| `migrate_thin_checkpoint` | legacy → thin + `ltm/` |
| `export_ltm_pack` / tar | **переезд** memory pack, не «модуль знаний» |

Lab store (`ingest-ref-afan`) = **выросшее детство**; prod agent может стартовать с пустого store + curriculum только через опыт.

---

## Non-goals

- Нет отдельного **продукта** «купи картридж русского» с подменой `field_state` из JSON.
- Нет **runtime oracle** из bundle (факты только с поля после sleep).
- Нет автоматического **cross-prism copy** всего `ltm/` без transfer contract + gate.

---

## Roadmap (код / design)

| Шаг | Артефакт |
|-----|----------|
| R1 | `design/matrices/matrix-casa-cross-prism-transfer-v1.md` (по шаблону KB) |
| R2 | bootstrap routes из матрицы в `prism_router` / `spawn` defaults |
| R3 | hot: `promote` с provenance + deny rules из do-not-transfer |
| R4 | agent-notes: строка в ca-substrate README → этот ADR |

M2 domain ([`CASA-ADR-0020`](CASA-ADR-0020-ooad-domain-model.md)): `Router` + `PrismCatalog` — удобная точка для загрузки transfer policy.

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-06-01 | ADR-0021: experience-first agent, cartridges lab-only, KB transfer projection |
