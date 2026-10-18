# BANC grounding: Memory / Hippo (Mushroom Body)
**Status:** draft (P0)  
**Date:** 2026-09-19  
**CASA:** ADR-0068 · ADR-0088 · ADR-0009 · `prism_memory` + `prism_hippo`  
**Data:** BANC v888 · literature: MB dopamine teaching (PPL→MBON, DOOMFLY)

---

## 1. CASA surface (what we built)

**Memory Zone** = infrastructure, not intelligence type (0068).

| Layer | CASA | Role |
|-------|------|------|
| explicit episodic | `prism_hippo` · H0–H3 | fast write wake |
| explicit semantic | `prism_memory` · L0–L3 | lexicon / schemas |
| implicit procedural | NCA registry, intent | procedural |
| consolidate | `run_sleep` · ADR-0009 | strengthen → LTM |
| integrate | ADR-0088 slice 3 | distant episode links |
| immutable | ADR-0069 | postulates @ promote |

Quad-mode (0088): wake index → consolidate → integrate → idle_micro.

---

## 2. BANC slice (queries + numbers)

**Mushroom body cohort (BANC v888):**

| Type | Count |
|------|-------|
| Kenyon cells | 4 552 |
| MB dopaminergic (DAN) | 301 |
| MBON (output) | 104 |
| MB extrinsic | 3 |
| **MB-touching edges** | **213 599** |

MBON types (cell_type): MBON10, MBON25/34, MBON19, … — sparse output layer.

**Not 1:1:** fly MB ≠ mammalian hippocampus; **functional rhyme** = sparse expansion + dopamine-tagged valence + output gating.

**DOOMFLY prior (engineering, not BANC table):** damage → PPL101 dopamine → ~4200 synapses → MBON11 — **local weight update on error**, not global BPTT.

**Central complex (navigation memory adjacency):** ~9 709 neurons (L1–L5 layers, PFN, FS) — separate doc **08-spatial**, but hippo integrate may touch CX paths.

---

## 3. Motifs

```text
  sensory (odor / context)
        │
        ▼
   Kenyon cells (4552)     ← sparse expansion / hash
        │
   ┌────┴────┐
   ▼         ▼
 DAN (301)  MBON (104)     ← valence tag / readout
   │         │
   └─ dopamine on error ──┘
        │
        ▼
   descending / behavior
```

| Fly MB | CASA hippo / memory |
|--------|---------------------|
| Kenyon expansion | `hippo_wake_index_tick` · moment_buffer |
| DAN reward/error | `lattice_value` + surprise → consolidate priority |
| MBON gating | sleep promote → `prism_memory` content |
| MB loops | `bridges_emergent` · integrate distant links |
| no MB in LTM lexicon | **separate** episodic (hippo) vs semantic (memory) — correct |

---

## 4. Rhyme / Gap / Port

| | Rhyme | Gap | Port |
|---|-------|-----|------|
| **Episodic fast write** | Kenyon = high-dimensional episodic index | hippo slice 0–1 partial | wake index = Kenyon analog |
| **Dopamine teach** | DAN on mismatch | consolidate blind to error magnitude | **value-weighted** consolidate (ADR-0009 + 0010) |
| **Sparse output** | 104 MBON vs 4552 Kenyon | too many direct hippo→act paths | integrate **before** CEN, not bypass |
| **Expansion ratio** | ~43:1 Kenyon:MBON | unknown CASA compression ratio | target moment_buffer cardinality bound |
| **Sleep** | MB plasticity offline | sleep = batch only | quad-mode consolidate ≈ MB replay |

---

## 5. Probes

| ID | Probe | Pass |
|----|-------|------|
| CZ-M1 | Surprise event → higher consolidate weight than neutral (same recency) | value_weight order |
| CZ-M2 | `bridges_emergent > 0` on coactive life stream | ADR-0088 R2 |
| CZ-M3 | Distant link A→B after `sleep_integrate` | ADR-0088 R3 |
| CZ-M4 | Hippo index size ≪ semantic LTM node count (sparse expansion) | ratio logged |

---

## 6. Follow-up

- Extract MB subgraph: `cell_class` Kenyon + DAN + MBON → fixture `banc_mb.json`.
- Do **not** claim MB = hippo homolog; doc says **functional rhyme**.
- Link DOOMFLY dopamine local update as **port candidate** for fast-weight slice (see 04-neuromodulator).
