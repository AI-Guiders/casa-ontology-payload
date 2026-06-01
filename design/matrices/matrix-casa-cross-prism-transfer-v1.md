# Transfer matrix — CASA cross-prism (runtime) v1

**Статус:** draft (design; bootstrap routes в ADR-0016)  
**Родитель:** [`CASA-ADR-0021-experience-agent-transfer.md`](../CASA-ADR-0021-experience-agent-transfer.md)  
**KB шаблон:** `agent-notes/knowledge/templates/matrices/template-transfer-matrix-v1.md`  
**Do-not-transfer:** `agent-notes/knowledge/worlds/knowledge-engineering/matrix-do-not-transfer-v1.md`

## Purpose

Маршрутизация **кросс-доменных** запросов между content-призмами (`prism_memory`, `prism_math`, `prism_visual`, …) без копирования чужого `ltm/` и без bundle-oracle.

## Transfer contract

- Переносить **маршрут и salience** (router + hot), не merge lexicon между призмами.
- Перед импортом чужого corpus в призму: sleep + critic; см. do-not-transfer (культура, локаль, «похоже»).
- Ingest bundle — **lab curriculum only**; runtime facts только с поля после consolidate.

## Fast symptom router

| Симптом / modality | Route (`prism_id`) | Lattice hint | Не делать |
|--------------------|--------------------|--------------|-----------|
| `t9`, `ru`, cyrillic cue | `prism_memory` / `prism_lang_ru` | L2 shard via `word_index` | читать Afan JSON на tick |
| `schema`, `||`, math frame | `prism_math` | `schema-math` | L2 monolith для F0 |
| `vis`, image, `vis.*` | `prism_visual` | `V1_object` / stack | PNG bytes on L2 |
| control / SN / value | `prism_control` / `prism_control_exec` | CU stack | encyclopedia в control |
| relay / arousal / sleep gate | `prism_control_thalamus` | thal relay → SN | не подменять `prism_router` |
| episodic cue only | hippo → sleep | — | dump hippo в `ltm/` tar |

## Matrix (детально)

| Источник | Переносимое | Целевой runtime | Boundary |
|----------|-------------|-----------------|----------|
| Surprise в domain A | hot edge `A→B` | promote после sleep | не auto-write B cells |
| Cue в lexicon RU | `resolve_route` + L2 shard | `route_l2_lattice` | не L3 monolith |
| Validated rule | R: token на L3 + NCA_rule | critic pass | не journal-only as profile |
| Lab bundle math | ingest job | `prism_math` ltm after sleep | не runtime oracle |

## Anti-patterns

- «Скопировать `ltm/` math в memory» как cross-domain.
- DetCorpus cartridge как единственный источник фактов на wake.
- Новая content-призма на каждый shard L2 (shard ≠ prism, ADR-0017).

*Версия: v1.0 draft · 2026-06-01*
