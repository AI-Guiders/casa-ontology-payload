# CASA ↔ NVIDIA Cosmos mapping v0

**Date:** 2026-05-31  
**Status:** accepted (updated by CASA-ADR-0010)  
**Supersedes:** Cosmos table in [`fpn-control-region-v0.md`](fpn-control-region-v0.md) § Cosmos mapping  
**Parent:** [`CASA-ADR-0010-control-zone-predict-attention-value.md`](CASA-ADR-0010-control-zone-predict-attention-value.md), [`control-lattice-stack-v0.md`](control-lattice-stack-v0.md)

NVIDIA Cosmos World Foundation Models expose **Predict / Transfer / Reason** plus infrastructure (**Tokenizer**, **Guardrail**). CASA maps them onto the **same CA substrate** — separate control lattices and bridges, not an external LLM.

---

## Core mapping (post ADR-0010)

| Cosmos | CASA organ | lattice_id | Bridge / tool |
|--------|------------|------------|---------------|
| **Predict** (rollout next state) | forward-model digest + field rollout | **`lattice_predict`** | P8 → SN (prediction error); [`lattice_predict_v0.py`](../tools/lattice_predict_v0.py) |
| **Transfer** (adapt world model) | listen / ingest / sleep consolidate | `cyl_memory` L0–L3 + `run_sleep` | z_bridge compose; ADR-0002 ltm/nca ship |
| **Reason** (plan → act) | salience + attention + planner | **`lattice_sn`** + **`lattice_dan`** + **`lattice_fpn_wm`** + **`lattice_cen`** | P2a/P6/P7/P2b/P3/P4 |
| **Tokenizer** | field codec (tokens on grid) | (memory lattices) | [`codec_grid_v0.py`](../tools/codec_grid_v0.py), `.ltm` vocab+placements |
| **Guardrail** | critic + value + integrity | **`lattice_value`** + Critic + POST | P9 → SN/sleep/replay; [`surface_error_v0.py`](../tools/surface_error_v0.py), [`replay_buffer_v0.py`](../tools/replay_buffer_v0.py) |

### What changed from v0

| Cosmos | v0 (before ADR-0010) | v1 (now) |
|--------|----------------------|----------|
| Predict | «нет» — conflated with DMN world-state | **`lattice_predict`** — explicit rollout + surprise |
| Reason | SN gate + CEN plan only | SN(salience) + **DAN**(spotlight) + FPN(goal) + CEN(act) |
| Guardrail | implicit critic only | **`lattice_value`** tags + replay priority (ADR-0009) |

**DMN stays** «what we know» (ontology digest). It is **not** Predict.

---

## Control stack diagram

```text
  VALUE ──P9──► SN ◄──P8── PREDICT(rollout)
                  │ P2a
                  ▼
                 FPN ──P6──► DAN ──P7──► DMN / L2 (sparse read)
                  │ P2b              ▲
                  ▼                  │ P1
                 CEN ──P3───────────┘
                  │ P4
                  └──► FPN (outcome)
```

Machine-readable: [`control-lattice-stack.v0.json`](control-lattice-stack.v0.json).

---

## Memory vs control (ADR-0002 + ADR-0007)

| Layer | Ships in prod store | Role |
|-------|---------------------|------|
| `ltm/` + `nca/` (memory) | **yes** | specialization cartridge (lexicon, alphabet, …) |
| `ltm/ctrl/` + `nca/lattice_*/` (control) | roadmap | control NCA per lattice |
| `field_state.json` | **no** (lab) | full runtime snapshot |

Cosmos **Transfer** = changing the **agent store cartridge**, not recompiling core tools.

---

## Implementation status

| Brick | Status |
|-------|--------|
| Predict digest model (R3) | ✅ `lattice_predict_v0`, P8, bench + tests |
| Predict field NCA | roadmap `train_sss_nca_v0 --lattice-id lattice_predict` |
| DAN spotlight (R4) | ✅ `lattice_dan_v0`, P6/P7, bench + tests |
| Value organ (R5) | ✅ `lattice_value_v0`, P9; replay `value_weight` (R2) |
| Tick P1–P9 on field | roadmap (replace layered_infer hot path) |

---

## Related

- [`understanding-contract-v0.md`](understanding-contract-v0.md) — predict loop as comprehension invariant
- [`CASA-ADR-0009-experience-replay-retention.md`](CASA-ADR-0009-experience-replay-retention.md) — value → replay priority
- [`modules-fmri-analogy-v0.md`](modules-fmri-analogy-v0.md) — DAN/VAN split, sparse modules
