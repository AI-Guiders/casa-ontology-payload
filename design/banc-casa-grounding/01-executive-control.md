# BANC grounding: Executive / Control Zone
**Status:** draft (P0)  
**Date:** 2026-09-19  
**CASA:** ADR-0010 · ADR-0061 `executive` · [`control-lattice-stack.md`](../control-lattice-stack.md)  
**Data:** BANC v888 (`banc_888_meta.feather`, edgelist v2, betweenness afferent→efferent)

---

## 1. CASA surface (what we built)

| Organ | lattice_id | Role |
|-------|------------|------|
| world-state digest | `lattice_dmn` | что знаем |
| salience | `lattice_sn` | bottom-up gate |
| working memory / mode | `lattice_fpn_wm` | goal stack |
| planner / act | `lattice_cen` | что сделать |
| forward model | `lattice_predict` | rollout + prediction error |
| attention spotlight | `lattice_dan` | sparse read mask |
| priority tag | `lattice_value` | replay / consolidate bias |

Bridges P1–P9. Zone owner: **executive** (0061). Not a monolith — distributed stack.

---

## 2. BANC slice (queries + numbers)

| Metric | Value |
|--------|-------|
| ascending neurons | 1 849 |
| descending neurons | 1 316 |
| motor (efferent tip) | 805 |
| A\|D touch edges | 12.06% of all edges |
| brain→VNC via **descending** | **83.8%** |
| VNC→brain via **ascending** | **79.7%** |
| Top-100 afferent→efferent betweenness | 38 DN + 31 AN + 21 CB intrinsic |

**Top chokepoints (betweenness):** `DNc01` (gaba), `DNb05` (ACh), `AN19B001` (VNC ascending), `MeLp1` (visual projection), `DNpe053` (dopamine).

**Descending NT mix:** ACh 910 · GABA 241 · Glu 102 · 5HT 19 · OA 13 · DA 11.

**Read:** control is a **thin bridge layer** (~1.7% neurons) with **massive cross-region leverage** — not spread across 73k optic intrinsic cells.

---

## 3. Motifs

```text
  sensory / VP ──► CB intrinsic ──► [ASCENDING] ──► brain
                        │                              │
                        │         NECK BOTTLENECK      │
                        │         (A/D 80%+)           │
                        ▼                              ▼
                   VNC intrinsic ◄── [DESCENDING] ◄── DN chokepoints
                        │
                        ▼
                     MOTOR
```

| Fly motif | CASA rhyme |
|-----------|------------|
| A/D = neck bottleneck | `lattice_dan` sparse_ratio; P7 mask |
| DN betweenness hubs | P8 surprise routes through named chokepoints |
| cascade / forward propagation | `lattice_predict` rollout k |
| value / dopamine on error | `lattice_value` + P9 → sleep (DOOMFLY PPL→MBON analog) |
| FPN/CEN higher centers | `lattice_fpn_wm` / `lattice_cen` modes |

---

## 4. Rhyme / Gap / Port

| | Rhyme | Gap | Port |
|---|-------|-----|------|
| **Distributed stack** | A/D + DN/AN = multi-organ control, not one blob | SN still overloaded salience+routing in early lab | keep P6–P9 split (ADR-0010) |
| **Sparse routing** | 12% edges, 80% cross-region via A/D | DAN `sparse_ratio` was magic number | **target ≈ 0.12–0.15** active field fraction from A/D edge share |
| **Predict** | cascade on graph ≈ predict rollout | no field-level cascade yet | Phase A: `bench_banc_cascade_vs_predict` |
| **Value** | DA DN (`DNpe053`) on betweenness top | value = FIFO not NT-tagged | high-betweenness surprise → `lattice_value` boost |
| **Neck** | brain↔VNC asymmetry (276k vs 230k edges) | no explicit neck prism | optional `control_bridge` tier: `brain` / `neck` / `vnc` |

---

## 5. Probes

| ID | Probe | Pass |
|----|-------|------|
| CZ-E1 | DAN sparse_ratio within ±15% of 12% (A/D touch fraction) | field metric |
| CZ-E2 | P8 surprise ∝ betweenness rank on sensory→motor path | Spearman ρ > 0.3 |
| CZ-E3 | Ablate `lattice_predict`: P1–P5 still routes (degraded) | no crash |
| CZ-E4 | cascade @ k on DN subgraph ≈ predict frontier | Jaccard ≥ 0.6 |

Fixture: `tools/fixtures/banc_cz-s1.json` (visual→DN→motor subgraph).

---

## 6. Follow-up

- Lab ADR addendum: `CASA-ADR-00XX-control-zone-banc-grounding` after CZ-E1 green.
- Code: `tools/banc_subgraph.py` (CZ-S1, CZ-S3 neck, CZ-S5 betweenness).
- Cross-ref: [`note-casa-control-zone-banc-grounding.md`](../../../../agent-notes/knowledge/work/projects/door-to-singularity/ca-substrate-agent/note-casa-control-zone-banc-grounding.md) (KB first look).
