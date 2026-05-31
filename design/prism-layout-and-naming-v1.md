# Prism layout & semantic naming v1

**Статус:** proposed (структура репо + namespace; **физические id и paths store — legacy alias** до миграции)  
**Дата:** 2026-05-31  
**Связано:** [naming-memory-layers-v0.md](naming-memory-layers-v0.md), [CASA-ADR-0011-sensory-modalities-audio-video-v0.md](CASA-ADR-0011-sensory-modalities-audio-video-v0.md), CIDE [naming-layers-v1.md](../../cascade-ide/docs/design/naming-layers-v1.md) §6

---

## Зачем

1. **Плоский `tools/`** — ~200 скриптов; `sss_*`, `lattice_*`, control и sensory смешаны → через полгода не найти, где auditory NCA.
2. **`sss` в именах** — временный scaffold ([`second-signal-system-v0.md`](second-signal-system-v0.md)); в prose и новом коде — **semantic namespace**, не «SSS как префикс файла».
3. **Призмы — разные жанры:** control ≠ memory ≠ spatial; у каждой свой stack JSON, свой подкаталог, свои `lattice_*` id.

**Правило:** в `field_state` / store paths **legacy id сохраняем** (`L2_word_07`, `ltm/l2/`); новая иерархия — **рядом**, с manifest alias (как CIDE `memory.lexicon` ↔ `L2_word_07`).

---

## Канон имён (prism id)

| Prism id (`field_state`) | Semantic namespace | Роль |
|--------------------------|-------------------|------|
| `prism_control` | `control.lattice.*` | CU: DMN, SN, FPN, CEN, predict, DAN, value |
| `prism_memory` | `memory.*` | 2-я СС: grapheme → phrase (+ F0 math hub) |
| `prism_auditory` | `sensory.audio.*` | слух, phoneme, localization |
| `prism_visual` | `sensory.vis.*` | ventral: object, scene |
| `prism_spatial` | `sensory.spatial.*` | dorsal: depth, pose, ego |
| `prism_hippo` | `episodic.*` | fast write, consolidate |
| `prism_sensor` | `io.buffer.*` | rolling frame (не LTM) |

**Не путать:** `z_level` на решётке — индекс **внутри** призмы; `S2_depth` — **spatial** prism, не «z=2 на vis».

---

## Дерево репо (целевое)

```text
design/prisms/                          # machine-readable stacks (SSOT)
  control/stack.v0.json
  memory/stack.v0.json                  # бывш. sss-lattice-stack
  auditory/stack.v0.json
  visual/stack.v0.json
  spatial/stack.v0.json
  hippo/stack.v0.json
  math/stack.v0.json                    # F0…F2 logical
  hippo/stack.v0.json                   # episodic H*

casa/                                   # P2: пакет (сейчас — roadmap; код ещё в tools/)
  prisms/
    control/
      lattices/                         # digest bricks, predict, dan, value
      bridges/                          # P1…P13 encode/decode helpers
      migrate_control_stack_v0.py       # → migrate.py (alias)
    memory/                             # бывш. sss_* (2-я СС)
      sign/                             # memory.grapheme (L0)
      lexicon/                          # memory.lexicon shards (L2)
      phrase/                           # memory.phrase (L3)
      surface/                          # sign.surface (бывш. sss_surface)
      prisms.py                         # ensure_prisms (бывш. sss_cylinders)
    auditory/
      lattices/
      codec/                            # wav → A0 tokens
    visual/
      lattices/
      codec/
    spatial/
      lattices/                         # S0 disparity, S1 surface, S2 pose
      stereo/                           # binocular / binaural glue
    hippo/
      lattices/
    shared/                             # store_layout, field_write, nca_train_util

tools/                                  # interim: thin wrappers → casa.prisms.* (deprecation)
  README.md                             # «import from casa.prisms…»

lab/agent-stores/<store-id>/
  field_state.json                      # prisms.{control,memory,…}
  ltm/
    control/                            # legacy alias: ctrl/
    memory/
      grapheme/                         # legacy: l0/ paths optional
      lexicon/                          # legacy alias: l2/
    auditory/                           # roadmap
    visual/
    spatial/
  nca/
    control/lattice_predict/            # legacy: nca/lattice_predict/
    memory/lexicon/words-ru-00/         # legacy: nca/words-ru-00/
    auditory/A1_phon/
    spatial/S0_disparity/
```

**Жанровая папка = одна призма.** Внутри — только её `lattice_*`, codec, train, bench. Cross-prism — только `bridges/` в `shared/` или явные `x_bridge_*` в stack JSON.

---

## Lattice id: canonical v1 vs legacy

**Canonical `lattice_id`** (field, nca, manifest): v1 kebab from [`lattice-id-map.v1.json`](lattice-id-map.v1.json).  
**Legacy** (`L2_word_07`, `lattice_dmn`, …): alias only — boot resolves both until M4.

| Semantic id (prose) | Canonical v1 `lattice_id` | Legacy alias | Folder under `nca/` |
|---------------------|---------------------------|--------------|---------------------|
| `control.dmn` | `control-dmn` | `lattice_dmn` | `control/control-dmn/` |
| `control.predict` | `control-predict` | `lattice_predict` | `control/control-predict/` |
| `memory.grapheme.cyrl` | `alphabet-ru` | `L0_grapheme_cyrl` | `memory/sign/alphabet-ru/` |
| `memory.lexicon.shard` | `words-ru-07` | `L2_word_07` | `memory/lexicon/words-ru-07/` |
| `memory.math.schema` | `schema-math` | `F0_schema` | `memory/math/schema-math/` |
| `memory.math.cardinal` | `cardinal-math` | `F2_quantity` | `memory/math/cardinal-math/` |
| `episodic.surface` | `episodic-surface` | `H1_surface`, `H0_episode` | `hippo/episodic-surface/` |
| `episodic.rule` | `episodic-rule` | `H2_rule` | `hippo/episodic-rule/` |
| `sensory.audio.phoneme` | `audio-phoneme` | `A1_phon` | `auditory/audio-phoneme/` |
| `sensory.vis.object` | `vis-object` | `V1_object` | `visual/vis-object/` |
| `sensory.spatial.disparity` | `spatial-disparity` | `S0_disparity` | `spatial/spatial-disparity/` |

Prose: **«shard `memory.lexicon` (`words-ru-07`)»** — не «sss L2»; **«`memory.math.schema` (`F0_schema`)»** — не «F0».

---

## Замена префикса `sss_*` (миграция кода)

| Legacy module | Semantic home | Примечание |
|---------------|---------------|------------|
| `sss_cylinders_v0.py` | `casa.prisms.memory.prisms` | `ensure_prisms()` |
| `sss_surface_v0.py` | `casa.prisms.memory.surface` | 2-я СС output |
| `sss_l2_shard_v0.py` | `casa.prisms.memory.lexicon.shard` | |
| `sss_wake_v0.py` / `sss_sleep_v0.py` | `casa.prisms.hippo` + `shared.tick` | |
| `train_sss_nca_v0.py` | `casa.prisms.shared.nca_train` | prism-agnostic trainer |
| store `sss-*-v0` | **profile id** (ok) | имя store = dataset, не subsystem |

**Не переименовывать одним коммитом:** shim `tools/sss_foo.py` → `from casa.prisms.memory.foo import main` до green CI.

---

## `design/prisms/*/stack.v0.json`

Каждый файл:

- `prism_id`, `schema_version`
- `lattices[]`: `lattice_id`, `semantic_id`, `z_level`, `nca_profile`, `z_phases[]`
- `bridges[]`: `bridge_id`, `from`, `to`, `kind` (`z_bridge` | `x_bridge` | `control_bridge`)

См. начальные файлы в [`design/prisms/`](prisms/).

---

## Store manifest alias (roadmap)

`memory_manifest.json` / `pack.manifest.json` gain optional block:

```json
{
  "prism_layout_version": 1,
  "aliases": {
    "ltm/l2": "ltm/memory/lexicon",
    "ltm/ctrl": "ltm/control",
    "nca/words-ru-00": "nca/memory/lexicon/words-ru-00"
  }
}
```

Boot loader resolves **both** paths until migration complete.

---

## Порядок внедрения (P2, после fv=6 cartridge)

**Gate и фазы M0–M4:** [`CASA-ADR-0012-cide-parity-fieldbus-and-migration.md`](CASA-ADR-0012-cide-parity-fieldbus-and-migration.md).

| Step | Action |
|------|--------|
| S1 | Этот doc + `design/prisms/*.json` + ADR-0012 |
| S2 | `tools/README.md` — карта «куда переедет» | **done** |
| S3 | Create `casa/prisms/{control,memory}/` + shims; **no** store path break | **in progress** (control + shared ids) |
| S4 | New sensory code **only** under `casa/prisms/auditory|visual|spatial/` |
| S5 | Optional store subdirs `ltm/memory/` alongside `ltm/l2/` |
| S6 | Drop `sss_` prefix when shims unused |

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-05-31 | v1: folder taxonomy, semantic namespaces, sss migration table |
