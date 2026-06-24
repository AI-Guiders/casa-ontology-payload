# Handoff: Concept Zone + curriculum id model (для Димы)

**Status:** scratch — **согласовано** (ответ Димы 2026-06-24); код и merge — **ещё не делали**  
**Date:** 2026-06-22 (amend 2026-06-24, порядок п.1→колготки→merge 2026-06-25)
**Audience:** Дима Ратнер + Света  
**Normative:** [0085](CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md), [0073](CASA-ADR-0073-concept-layer-lexicalization.md), [0083](CASA-ADR-0083-curriculum-ontology-agent-store.md)  
**Дима (детали миграции):** `feat/conceptual-network` → [CASA-scratch-curriculum-id-migration-map-v1.md](CASA-scratch-curriculum-id-migration-map-v1.md) *(пока на их ветке, не в `develop`)*

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

**Вывод (2026-06-22):** listen/motor + ADR на `fix/neumann-free-speech-recovery`. **Merge в `develop` — в конце**, после нашей миграции store и пилота на поле.

---

## Порядок работ (оператор — normative)

**На ветке `fix/neumann-free-speech-recovery`, без merge в `develop`.**

```text
1. МИГРАЦИЯ (мы) — store + P18
   lemma.ru/en в concept_layer; ensure_concept_built_in;
   teach base → Built-In полка @ domains.concept + agent-concept-graph

2. ПИЛОТ НА ПОЛЕ — только когда полка есть
   «Колготки» (listen-сцена) + смотрим что на поле:
   imprint, impulse trace, bind/concept hubs @ tick
   (позже — substrate dashboard 0087)

3. GATE шире
   Lalabook / G0 checklist, pytest зелёный

4. MERGE → develop

5. ДИМА — curriculum id-флип в коде (их слайс), после п.4
```

**Не наоборот:** колготки **не** прогоняем как критерий «до» concept teach — иначе на поле нечего смотреть кроме сырого listen. Lalabook — после того как полка + колготки дали картину на store.

**Дима (п.5):** их `_concept_id` / names / тесты — **после** нашего merge; **не** блокирует наш п.1–3 на ветке.

---

## Ответ Димы (2026-06-24)

### 1. `lemma.ru/en` — **да**

Согласен: `concept.*` = hub; `lemma.{ru,en}.*` = словарная единица; словоформы — parse/morph. Ложится на текущий curriculum: «столе»→«стол»→hub; стем-резолв и round-trip не ломаются, только id.

### 2. Порядок merge — **схема утверждена, выполнение позже**

Когда будем готовы: `fix/neumann-free-speech-recovery` → `develop` (**после** п.1–3 в §«Порядок работ»). Merge делаем **мы**. Димина curriculum-миграция в **их** коде — **после** merge (п.5); merge её не блокирует.

### 3. Скоуп вырос

За неделю у Димы: софт-домен (~30+10), отрицание, числа, единицы, `equivalence.py` + reality-check. Объём id-миграции **больше**, чем в §«Планируемый slice» ниже — см. [migration map](CASA-scratch-curriculum-id-migration-map-v1.md) на `feat/conceptual-network`.

### 4. Шов работ (подтверждён обеими сторонами)

| Часть | Кто |
|-------|-----|
| `_concept_id`, хардкоды `lex.*`, names-рёбра, `equivalence.py` / analogy edge-parser, ~40 curriculum-тестов | **Дима** |
| `schema-math` только в curriculum-точках (`world.py`, `demo_repl`, `glossary`, `teach`); **math L0 не трогать** | **Дима** |
| Built-In регистрация, `agent-concept-graph` @ `prism_agent`, catalog/`theories[]`, supersede-ceremony, `ensure_concept_built_in`, teach CLI | **Света** |
| P18 `concept_layer.py` → `lemma.ru/en`, mass `lang.word.*` store — **не** в этом слайсе | **Света** |

**Финальная конвенция (общая):**

```text
hub:    concept.{slug}
lemma:  lemma.ru.{slug} / lemma.en.{slug}
names:  concept.*|names|lemma.{ru,en}.*  (+ surface в metadata)
types:  food, physical_object, on|arg1|…   (JSON категории без префикса type.*)
```

**Старт curriculum-миграции (Дима):** после merge (§ п.5). Наш store teach (§ п.1) — **до** колготок.

---

## Наш slice (п.1 — на ветке, до merge)

**Разделение с Димой** — см. таблицу §4; здесь только **store / P18**.

1. **Lemma rename в P18:** `concept_layer.py`, `test_concept_layer*`, `test_concept_index*`.
2. **`ensure_concept_built_in`** + `tools/teach_curriculum_ontology.py` — idempotent teach base на `agents/von-neumann`; lattice `agent-concept-graph` @ `prism_agent`.
3. **Регистрация Built-In:** `domains.concept.theories[]`, catalog, `agent-concept-core` index.
4. **Lab vs store:** `world.py` может остаться lab-only `schema-math` (0083 §5).

**Gate п.2:** колготки + осмотр поля (imprint / impulse / concept bind на store с полкой).

### Дима / curriculum-код (п.5 — после merge)

См. [migration map](CASA-scratch-curriculum-id-migration-map-v1.md): `_concept_id`, names, equivalence, ~40 тестов.

**Вне scope обоих слайсов:**

- mass migration `lang.word.*` lexicon store;
- wide 4500 net на store (opt-in);
- `supersede_concept_theory` (P20a);
- C1 partner wire listen↔concept.

---

## Вопросы к Диме — **закрыты (2026-06-24)**

1. ~~`lemma.ru/en`~~ → **да**
2. ~~Merge order~~ → **fix/neumann → develop когда готовы; id-migration после**

---

## Ссылки для чтения (5 мин)

1. [CASA-ADR-0085](CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md) — главный
2. [CASA-DESIGN-NAVIGATOR-v1.md](CASA-DESIGN-NAVIGATOR-v1.md) — § Concept Zone vs понятийная сеть
3. [CASA-ADR-0083](CASA-ADR-0083-curriculum-ontology-agent-store.md) — teach на store, postmortem `schema-math`
4. Дима: `origin/feat/conceptual-network` → `design/CASA-scratch-curriculum-id-migration-map-v1.md`
