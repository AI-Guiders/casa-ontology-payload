# Semantic memory naming (канон)

**Status:** canon — **говорим и пишем в коде так**, legacy L/F/H/T — только migrate и literal id в store  
**Date:** 2026-06-06  
**Code:** `casa/prisms/shared/memory_layer_names.py`, `lattice_names_v1.py`  
**Map:** [`lattice-id-map.v1.json`](lattice-id-map.v1.json)

---

## Правило одной строки

**В prose, логах, новом коде — semantic id (`memory.grapheme`, `episodic.surprise`).**  
**Legacy (`L2_word_07`, `F0_schema`) — только в migrate, diff store, цитатах manifest.**

---

## Жизненный цикл

| Semantic | RU | Legacy (не использовать) |
|----------|-----|--------------------------|
| `agent.wake` | бодрствует | T_wake, sn.mode=wake |
| `agent.sleep` | сон / консолидация | T_sleep, run_sleep |
| `agent.macro_tick` | шаг жизни | T, macro tick |

---

## Язык (2-я сигнальность)

| Semantic | RU | Lattice id (v1 kebab) | Legacy |
|----------|-----|----------------------|--------|
| `memory.grapheme` | буква / знак | `alphabet-ru`, `alphabet-en` | L0_*, T0 |
| `memory.grapheme.input` | VK, раскладка, punct | `keys-physical`, `layout-*`, `punct-*` | L0_vk_*, L0_layout_*, L0_punct_* |
| `memory.morph.role` *(planned)* | слот морфемы | `morph-role-ru` | — |
| `memory.logic.law` *(planned)* | открытый закон логики | `logic-laws` | — |
| `memory.math.axiom` *(planned)* | аксиоматика | `math-axiom` | — |
| `memory.math.calculus` *(planned)* | правила ∫/∂ | `math-calculus-rules` | — |
| `memory.syllable` | слог | `syllables-ru` | L1_syllable, T1 |
| `memory.lexicon` | слово | `lexicon-ru-07` | L2_word_07, T2 |
| `memory.phrase` | фраза / hub | `phrases`, `phrases-lang.word.{lo}-lang.word.{hi}` | L3_phrase, T3 |

---

## Математика (1-я сигнальность)

| Semantic | RU | Lattice id | Legacy |
|----------|-----|------------|--------|
| `memory.math.schema` | схема (+, =, op) | `schema-math` | F0_schema, F0 |
| `memory.math.compose` | сборка qty | `compose-math` | F1_compose, F1 |
| `memory.math.cardinality` | количество | `cardinal-math` | F2_quantity, F2 |

**F0 extract** в коде = «вывод math-структуры на sleep» — не «слой F0».

---

## Эпизоды (hippo, до сна)

| Semantic | RU | Lattice id | Legacy |
|----------|-----|------------|--------|
| `episodic.surprise` | удивление / mismatch | `episodic-surface` | H1_surface, H0_episode |
| `episodic.rule` | правило | `episodic-rule` | H2_rule |
| `episodic.scene` | сцена | `episodic-scene` | H3_scene |

Bind class на эпизоде (ADR-0047): `bindable_surprise`, `open_probe`, `bindable_correction`, `rule`.

---

## Control (не z-память)

| Semantic | RU | Lattice id | Legacy |
|----------|-----|------------|--------|
| `control.ontology` | долгая онтология | `control-dmn` | lattice_dmn |
| `control.salience` | салиентность | `control-salience` | lattice_sn |
| `control.working_memory` | WM задачи | `control-working-memory` | lattice_fpn_wm |
| `control.executive` | план / act | `control-executive` | lattice_cen |

---

## API

```python
from casa.prisms.shared.lattice_names_v1 import canonical_lattice_id, SYLLABLES_RU
from casa.prisms.shared.memory_layer_names import memory_layer_for_lattice_id, memory_layer_heading

lid = canonical_lattice_id("L1_syllable")  # → "syllables-ru"
layer = memory_layer_for_lattice_id(lid)  # → "memory.syllable"
heading = memory_layer_heading(layer)     # → "memory.syllable (T1 · слог)"
```

Migrate store: `python -m casa.prisms.shared.migrate_lattice_ids_v1 --store-dir agents/von-neumann`

---

## Canon immutable vs experiential

**Bootstrap** (алфавит, VK, layout, punct, символы math) — cold-boot минимум, чтобы начать; **agent_canon** — законы, которые он сам узнал и закрепил. Лексикон, диалог, примеры — **experiential**. Promote/demote agent_canon — **его решение**. Полный протокол: [`CASA-immutable-lattice-canon-v1.md`](CASA-immutable-lattice-canon-v1.md).

---

## Не путать

| Это | Не это |
|-----|--------|
| `memory.lexicon` | KB tier K2 |
| `B2` в ADR-0034 | слой памяти — **номер задачи** |
| `semantic_layer` на episode | замена `concept_id` |
