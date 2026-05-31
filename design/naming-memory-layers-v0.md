# Naming: CASA memory layers — semantic registry v0

**Статус:** living note (align with CIDE [naming-layers-v1.md](../../cascade-ide/docs/design/naming-layers-v1.md) §6)  
**Дата:** 2026-05-31  
**Связано:** [CASA-ADR-0002-agent-memory-ltm-nca.md](CASA-ADR-0002-agent-memory-ltm-nca.md), [memory-hierarchy-v0.md](memory-hierarchy-v0.md)

## Зачем

`L0`–`L3` в CASA означают **ось z prism_memory**, не verify rungs CIDE и не Endsley SA. В документации использовать **semantic layer**; физические id решёток (`L2_word_07`, paths в `nca/`) **не переименовывать** в v0 — только alias в prose.

## Semantic layers

| Semantic layer | Legacy prefix | Lattice examples | KB analog (ADR-0002) |
|----------------|---------------|------------------|----------------------|
| `memory.grapheme` | L0 | `L0_grapheme` | always in force |
| `memory.syllable` | L1 | `L1_syllable` | domain working set |
| `memory.lexicon` | L2 | `L2_word`, `L2_word_00…63` | archive / evidence (sharded) |
| `memory.phrase` | L3 | `L3_phrase` | semantic routing |

## Hippo (отдельная ось)

| Semantic | Legacy | Role |
|----------|--------|------|
| `episodic.surface` | H1_surface | babble / surface episodes |
| `episodic.rule` | H2_rule | rule episodes → L3 |
| `episodic.scene` | H3_scene | scene consolidation |

Не сокращать до «L1 hippocampus» — использовать `episodic.*` или `H1_*` lattice id.

**Repo layout:** stacks и папки по призмам — [`prism-layout-and-naming-v1.md`](prism-layout-and-naming-v1.md); `sss_*` modules → `casa/prisms/memory/` (roadmap).

## Prose rule

- ✓ «shard `memory.lexicon` (`L2_word_07`)»
- ✗ «L2 verify» в CASA docs (wrong domain)

## История

| Дата | Изменение |
|------|-----------|
| 2026-05-31 | v0: semantic layers; cross-ref CIDE registry |
