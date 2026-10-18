# BANC grounding: Neuromodulator Zone
**Status:** draft (P1)  
**Date:** 2026-09-19  
**CASA:** ADR-0066 · ADR-0061 `neuromodulator` · ADR-0010 (`lattice_value`, DAN)  
**Data:** BANC v888 (`neurotransmitter_predicted`, `neurotransmitter_verified`, neuropeptide)

---

## 1. CASA surface (what we built)

**Neuromodulator Zone** = continuous **gain bus** между somatic/metabolic и limbic (0066). Не literal DA/5-HT в коде — функциональные каналы с decay/coupling/inertia.

| Channel (functional) | CASA role |
|----------------------|-----------|
| arousal / panic contour | cross-zone gain ↑, metabolic coupling |
| valence bias | limbic input scale |
| surprise persistence | holds 3–10 ticks post-event |
| genetic sensitivity | `surprise_gains` from 0062 |

Tier: **subcortical bus** — ниже executive, выше raw metabolic counters.

---

## 2. BANC slice (queries + numbers)

**Predicted NT (154 053 tagged neurons):**

| NT | Count | ~share |
|----|-------|--------|
| acetylcholine | 87 059 | 56.5% |
| glutamate | 25 099 | 16.3% |
| gaba | 21 686 | 14.1% |
| **dopamine** | **8 344** | 5.4% |
| histamine | 7 411 | 4.8% |
| octopamine | 2 303 | 1.5% |
| **serotonin** | **1 936** | 1.3% |
| tyramine | 215 | <0.2% |

**Non-olfactory dopamine (cell_class top):** lateral_horn_output 473 · CX_output 287 · MB_DAN 249 · lobula_columnar 161 · CX_intrinsic 125.

**Verified NT:** 43 507 ACh · 8 738 Glu · 6 845 GABA · 355 DA · 88 5HT · 81 OA (subset with immunolabel).

**Neuropeptide verified (7 025):** sNPF 4 780 · Tk 854 · Mip 362 · Dh31/Dh44 (arousal/metabolic lit).

**MB dopaminergic:** 301 neurons (`mushroom_body_dopaminergic_neuron`).

**Read:** fly uses **many excitatory/inhibitory bases** (ACh/Glu/GABA dominate) with **sparse modulator overlays** (DA/OA/5HT <7% combined). Modulators cluster on **output layers** (LH, CX, MB) — not uniform gain on all 188k.

---

## 3. Motifs

```text
  fast synaptic (ACh/Glu/GABA)     ← bulk wiring
           │
           ▼
  sparse modulator taps (DA/OA/5HT/Hist)
           │
     ┌─────┼─────┐
     ▼     ▼     ▼
    MB    CX    LH output
   (teach)(heading)(valence routing)
```

| Fly | CASA gain bus |
|-----|---------------|
| DA on error / reward | `lattice_value` + neuromod surprise channel |
| OA/5HT arousal | arousal contour + metabolic coupling (0066) |
| GABA brake | inhibitory gain channel |
| neuropeptide slow | second timescale bus (optional P2) |

---

## 4. Rhyme / Gap / Port

| | Rhyme | Gap | Port |
|---|-------|-----|------|
| **Multi-channel bus** | 6+ NT classes | single arousal delta on event | map **4 functional channels**: excite / inhibit / teach / arousal |
| **Sparse overlay** | DA 5.4%, not 50% | modulator affects whole field | **targeted** gain on LH-equivalent + value lattice only |
| **Persistence** | neuropeptide + slow DA | instant reset after event | decay τ from genetic; coupling arousal→metabolic |
| **MB DAN teach** | 301 DAN → Kenyon | consolidate ignores modulator state | neuromod **feeds** consolidate priority (link 03) |
| **Verified subset** | immunolabel ground truth | all predicted treated equal | probe on **verified** edges first in fixtures |

---

## 5. Probes

| ID | Probe | Pass |
|----|-------|------|
| CZ-N1 | Post `self_failure`: arousal decays over ≥5 ticks (not instant zero) | τ logged |
| CZ-N2 | Arousal↑ → metabolic cost↑ → compose defer rate↑ | coupling chain |
| CZ-N3 | Executive cannot zero modulator in same tick | invariant 0066 |
| CZ-N4 | DA-channel boost only on high-betweenness nodes (DN/LH analog) | sparse mask |

---

## 6. Follow-up

- Fixture: NT-labeled subgraph ≤10⁴ nodes (`tools/fixtures/banc_nt_bus.json`).
- Do **not** name variables `dopamine` in hot path — use functional channel ids.
- Cross-ref: 03-memory (MB DAN), 05-emotional (limbic read-only).
