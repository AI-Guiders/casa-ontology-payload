# Handoff: Concept Zone + curriculum id model (для Димы)

**Status:** scratch — согласование до кода  
**Date:** 2026-06-22  
**Audience:** Дима Ратнер + Света  
**Normative:** [0085](CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md), [0073](CASA-ADR-0073-concept-layer-lexicalization.md), [0083](CASA-ADR-0083-curriculum-ontology-agent-store.md)

---

## Одна строка

Concept Zone = **Built-In `concept.*`** (твоя понятийная сеть @ T=0) + **Self-Earned**; словарные единицы — **`lemma.ru.*` / `lemma.en.*`** (не hub `lex.*`); словоформы — parse/morph; граф типов — **`agent-concept-graph` @ `prism_agent`**, не `schema-math`.

---

## Что уже в доках (без кода)

| Решение | Было (lab / P18) | Стало (normative) |
|---------|------------------|-------------------|
| Hub смысла | `lex.apple`, `lex.table` | `concept.apple`, `concept.table` |
| RU/EN словарная единица | `lex.ru.*` / `lex.en.*` (путалось с hub) | **`lemma.ru.*` / `lemma.en.*`** |
| Имена в графе | `concept\|names\|lang.word.{surface}` | `concept.*\|names\|lemma.{ru,en}.*` + surface в metadata |
| Curriculum lattice | `schema-math` (lab `world.py`) | `agent-concept-graph` @ `prism_agent` |
| Species prior tier | «не catalog, чтобы не earned» (0083 §7 стар.) | **Built-In** @ `domains.concept` + `theory_id=species-concept-bootstrap-v1` |
| Ошибка в Built-In | operator-only | агент: **supersede** с gate (0085 §4, позже) |

**Код пока не трогали** — только ADR/таблицы. На `develop` / в твоём `concept_net.py` по-прежнему `_concept_id → lex.{en}` и тесты на `lex.apple`.

---

## Сверка с `develop` (2026-06-22)

```
git fetch origin
git log origin/develop..fix/neumann-free-speech-recovery   # 19 коммитов — мы впереди
git log fix/neumann-free-speech-recovery..origin/develop   # пусто — не отстали
```

- **`origin/develop`** — без новых коммитов относительно merge-base с нашей веткой `fix/neumann-free-speech-recovery`.
- **`origin/feat/conceptual-network`**, **`origin/feat/auto-curriculum`** — не ушли вперёд от `develop`.
- **`backup/develop`** (GitLab) — тоже без дельты вперёд.

**Вывод:** не отстаём от Диминого `develop`; наоборот — listen/motor track + ADR 0083–0085 + sensory 0027 только у нас, **ещё не влиты в `develop`**.

---

## Планируемый slice реализации (после согласования)

**Один PR / логические коммиты:**

1. **Lemma rename в коде:** `LEX_RU_PREFIX` → `LEMMA_RU_PREFIX`, `lex_for_locale` → `lemma_for_locale` (или оставить имя API с новыми id), P18 bootstrap `SPECIES_CONCEPT_BOOTSTRAP`, тесты `test_concept_layer*`.
2. **Hub rename в curriculum:** `concept_net._concept_id` → `concept.{slug}`; `glossary.py` / sleep teach — hub `concept.*`; **names edges** (сейчас `concept|names|lang.word.{surface}` в `translate.py`, `parse.py`, `concept_net.names_of`) → наш teach/read под `lemma.{ru,en}.*` (clean cut, без dual-read — store ещё не залит).
3. **`ensure_concept_built_in`** + `tools/teach_curriculum_ontology.py` — idempotent teach base (~280) на agent store; lattice `agent-concept-graph`.
4. **Регистрация Built-In:** `domains.concept.theories[]`, `catalog`, `agent-concept-core` index.
5. **Lab harness:** `world.py` lattice — отдельный refactor или явный «lab-only schema-math» комментарий (не модель store).
6. **JSON:** `concept-net-base-v1.json` — **без смены id категорий** (`food`, `physical_object`, … как у Димы); меняется только hub leaf: `lex.apple` → `concept.apple` при teach.

**Вне scope этого slice:**

- mass migration `lang.word.*` lexicon store;
- wide 4500 net на store (opt-in);
- `supersede_concept_theory` (P20a);
- C1 partner wire listen↔concept.

---

## Вопросы к Диме

1. **Ок ли `lemma.ru/en` вместо `lex.ru/en`** для словарной единицы, чтобы `lex.*` в графе больше не было hub identity?
2. **Merge order:** влить `fix/neumann-free-speech-recovery` → `develop` до id migration, или ты хочешь сначала review ADR 0085?

**Не спрашиваем (наша работа после merge):** формат glossary names edges, teach API, lattice id — адаптируем его семантику (пары, isa, affords) под ADR 0085; JSON категорий не трогаем.

---

## Ссылки для чтения (5 мин)

1. [CASA-ADR-0085](CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md) — главный
2. [CASA-DESIGN-NAVIGATOR-v1.md](CASA-DESIGN-NAVIGATOR-v1.md) — § Concept Zone vs понятийная сеть
3. [CASA-ADR-0083](CASA-ADR-0083-curriculum-ontology-agent-store.md) — teach на store, postmortem `schema-math`
