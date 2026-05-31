# Naming: CASA lattice axes — semantic registry v1

**Статус:** living note (align with CIDE [naming-layers-v1.md](../../cascade-ide/docs/design/naming-layers-v1.md) §6)  
**Дата:** 2026-05-31  
**Связано:** [prism-layout-and-naming-v1.md](prism-layout-and-naming-v1.md), [CASA-ADR-0002-agent-memory-ltm-nca.md](CASA-ADR-0002-agent-memory-ltm-nca.md), [sss-layer-names-v0.md](sss-layer-names-v0.md)

## Зачем

В CASA несколько **независимых осей** с буквой+цифрой: **L**, **F**, **B**, **H**, **A**, **V**, **S**, **T** (APLF). Голые «F2», «B0», «H1» в prose **не использовать** — только **semantic id** + physical `lattice_id` в скобках.

**Physical id (v1):** `lexicon-ru-07` = shelf 7 of Russian lexicon; **not** a linguistic class. POS / entity → **`phrases`**, not `lexicon-ru-nouns`.

**Two axes (do not merge):**

| Axis | Question | Example ids |
|------|----------|-------------|
| **Shard (capacity)** | Where does `lang.word.*` surface fit + NCA repair? | `lexicon-ru-07` |
| **Attribution (semantics)** | What POS / type / meta links to that word? | `phrases` + `E:lang.word.мама\|has_pos\|pos.noun` |

Prose: ✓ «shard 7 of `memory.lexicon` (`lexicon-ru-07`)» · ✗ «words-ru-07 lattice type».

Machine-readable stacks: [`design/prisms/*/stack.v0.json`](prisms/).

---

## 1. Second signal — `memory.*` (legacy **L0…L3**, **T0…T3**, **B0…B3**)

| Semantic id | Legacy lattice | Curriculum (bukvar) | APLF (T*) | Role |
|-------------|----------------|---------------------|-----------|------|
| `memory.grapheme` | `L0_grapheme_*` | **B0** | T0 | grapheme / letter |
| `memory.syllable` | `L1_syllable` | **B1** | T1 | syllable |
| `memory.lexicon` | `L2_word`, `L2_word_*`, `lexicon-{locale}-{shard}` | **B2** | T2 | lexicon shard (capacity bins, not POS) |
| `memory.phrase` | `L3_phrase`, **`phrases`** | **B3** | T3 | phrase hub — **POS, entity, meta** via `E:` edges |

**B0…B3** — **педагогическая** лестница ([`bukvar-text-modality-v0.md`](bukvar-text-modality-v0.md)), не отдельные решётки. В новых доках: «ступень **B0** → слой `memory.grapheme`», не «решётка B0».

**T0…T3** — нейтральные имена той же z-оси ([`sss-layer-names-v0.md`](sss-layer-names-v0.md)); канон prose = **`memory.*`**.

---

## 2. First signal — math — `memory.math.*` (legacy **F0…F2**)

Подсистема `first_signal_math` в **`prism_memory`** ([`f0-math-logical-layer-v0.md`](f0-math-logical-layer-v0.md)).

| Semantic id | Legacy lattice | Canonical v1 `lattice_id` | Role |
|-------------|----------------|---------------------------|------|
| `memory.math.schema` | `F0_schema` | `schema-math` | symbols, operators, `\| \|\|` sticks |
| `memory.math.compose` | `F1_compose` | `compose-math` | instance slots, homogeneous merge |
| `memory.math.cardinal` | `F2_quantity` | `cardinal-math` | bound cardinality `M:qty:*` |

Prose: ✓ «`memory.math.cardinal` (`cardinal-math`)» · ✗ «F2» / «F2_quantity» без domain.

Stack: [`prisms/math/stack.v0.json`](prisms/math/stack.v0.json).

---

## 3. Episodic — `episodic.*` (legacy **H0…H3**)

**`prism_hippo`**, не z памяти LTM.

| Semantic id | Legacy lattice | Notes |
|-------------|----------------|-------|
| `episodic.io` | `H0_io` | listen buffer; **≠** monolith `H0_episode` |
| `episodic.surface` | `H1_surface` | babble / surface episodes; **`H0_episode` → alias** |
| `episodic.rule` | `H2_rule` | segment / rule episodes |
| `episodic.scene` | `H3_scene` | dialogue / spatiotemporal scene |
| `episodic.replay_queue` | `H_replay_queue` | scheduler, not a lattice |

Prose: ✓ «append to `episodic.surface`» · ✗ «H1 LTM» · ✗ «H0 episode lattice» без уточнения (monolith vs `H0_io`).

Stack: [`prisms/hippo/stack.v0.json`](prisms/hippo/stack.v0.json).

---

## 4. Sensory — `sensory.*` (legacy **A** / **V** / **S**)

| Namespace | Legacy prefix | Stack |
|-----------|---------------|-------|
| `sensory.audio.*` | `A0…A2` | [`prisms/auditory/stack.v0.json`](prisms/auditory/stack.v0.json) |
| `sensory.vis.*` | `V0…V2` | [`prisms/visual/stack.v0.json`](prisms/visual/stack.v0.json) |
| `sensory.spatial.*` | `S0…S2` | [`prisms/spatial/stack.v0.json`](prisms/spatial/stack.v0.json) |

Примеры: `sensory.audio.phoneme` (`A1_phon`), `sensory.spatial.disparity` (`S0_disparity`).

---

## 5. Control — `control.*` (legacy `lattice_*`)

Не путать с F/B/H — executive stack в **`prism_control`**.

| Semantic id | Legacy lattice |
|-------------|----------------|
| `control.dmn` | `lattice_dmn` |
| `control.salience` | `lattice_sn` |
| `control.working_memory` | `lattice_fpn_wm` |
| `control.executive` | `lattice_cen` |
| `control.predict` | `lattice_predict` |
| `control.attention_topdown` | `lattice_dan` |
| `control.value` | `lattice_value` |

Stack: [`prisms/control/stack.v0.json`](prisms/control/stack.v0.json).

---

## 6. Curriculum / experiment ids (не lattice_id)

| Legacy | Semantic (prose) | Meaning |
|--------|------------------|---------|
| **B0…B3** | maps → `memory.grapheme` … `memory.phrase` | bukvar listen steps |
| **Exp L0…L4** | `curriculum.concrete.level_*` | concrete→abstract lessons ([`experiment-l-concrete-to-abstract-v0.md`](experiment-l-concrete-to-abstract-v0.md)) |
| **фаза 0…5** | `infancy.phase_*` | corpus timeline ([`infancy-corpus-phases-v0.md`](infancy-corpus-phases-v0.md)) |

---

## Prose rules (summary)

| ✓ | ✗ |
|---|---|
| shard `memory.lexicon` (`words-ru-07`) | «L2 shard» без domain |
| `memory.math.schema` + палочки Exp L0 | «F0 lattice» в ADR prose |
| `episodic.surface` after babble | «H0» (= io buffer **or** legacy monolith) |
| bukvar step B0 → `memory.grapheme` | «B0 решётка» |
| `control.predict` surprise | math tokens inside `control.dmn` (lab only) |

---

## Migration (code / manifest)

| Step | Action |
|------|--------|
| M0 | This doc + `design/prisms/{math,hippo}/*.json` |
| M1 | `memory_manifest.json`: optional `semantic_id` per lattice entry |
| M2 | New prose/ADR/UI — semantic only; grep `F0_`/`B0`/`H0_` in **new** docs |
| M3 | Routing/SN fields: `active_semantic_lattice` alias (physical id unchanged) |

Gate: [`CASA-ADR-0012-cide-parity-fieldbus-and-migration.md`](CASA-ADR-0012-cide-parity-fieldbus-and-migration.md) M0–M4.

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-05-31 | v0: L + hippo H1–H3; cross-ref CIDE |
| 2026-05-31 | v1: F→memory.math.*, B→curriculum/map, H0_io vs H0_episode, A/V/S + control table; prism stacks |
