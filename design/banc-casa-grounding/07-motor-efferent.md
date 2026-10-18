# BANC grounding: Motor / Efferent
**Status:** draft (P0)  
**Date:** 2026-09-19  
**CASA:** ADR-0061 executive tip · FSR / `cen_act` · partner wire motor  
**Data:** BANC v888 · MCNS ♂ (dimorphic motor compare — P1)

---

## 1. CASA surface (what we built)

Motor = **output end** of control stack, not a separate intelligence zone.

| Path | CASA artifact |
|------|---------------|
| plan → act | `lattice_cen` → `cen_act` |
| partner speech | partner wire / FSR efferent |
| listen motor loop | `verify_motor_speech_loop.py` |
| world model act | ADR-0054 (planned bind) |

flow=**efferent** in BANC meta: only **1 033** neurons tagged (most motor typed via `super_class=motor`).

---

## 2. BANC slice (queries + numbers)

| Cohort | Count |
|--------|-------|
| motor (super_class) | 805 |
| descending | 1 316 |
| **descending → motor direct edges** | **17 745** |
| VNC intrinsic | 12 866 |

**Motor cell_type:** tibia flexors, femur reductors, tendon muscles, `EN*` / `EFF*` (effector IDs).

**body_part_effector:** abdomen 168 · front_leg 139 · hind_leg 126 · middle_leg 126 · wing 64 · neck 49 · proboscis 35 · haltere 27.

**Descending NT (motor command):** ACh dominant (910/1316) — excitatory command bias.

**Control path length:** sensory (16k) → … → DN (1.3k) → motor (805) — **funnel**.

**Read:** motor layer is **tiny** (805) but **highly targeted**; most wiring is in DN bridge, not in muscle neurons themselves.

---

## 3. Motifs

```text
  CB / VNC processing
        │
        ▼
   DESCENDING (1316)     ← command generation
        │
        ▼  17.7k direct edges
   MOTOR (805)           ← muscle / effector pool
        │
        ▼
   body_part_effector    ← abdomen, leg, wing, proboscis
```

| Fly | CASA |
|-----|------|
| DN types (DNc, DNb, DNg, DNp) | `lattice_cen` action classes |
| body_part_effector | FSR target / partner channel |
| few motor neurons | small efferent alphabet (not 50k outputs) |
| ACh DN | excitatory act bias |

---

## 4. Rhyme / Gap / Port

| | Rhyme | Gap | Port |
|---|-------|-----|------|
| **Funnel** | 1316 DN → 805 motor | cen may emit too many token types | **bound** efferent alphabet |
| **Body-part map** | leg/wing/abdomen tags | no effector somatotopy | `body_part_effector` → FSR slot map |
| **Direct DN→motor** | 17k edges = named paths | act sometimes from lexicon not DN stack | **CEN must pass through DN-equivalent choke** |
| **♂ dimorphism** | MCNS motor hotspots | single sex-agnostic motor | FPN mode for context routing (future) |
| **Tiny motor pool** | 805 << 188k | over-parameterized readout | linear readout on DN state, not full field |

---

## 5. Probes

| ID | Probe | Pass |
|----|-------|------|
| CZ-Mo1 | Act class count ≤ order of motor pool (hundreds, not thousands) | design audit |
| CZ-Mo2 | Ablate descending-equivalent (CEN without plan) → no structured motor | duck test |
| CZ-Mo3 | Sensory→motor path exists in BANC subgraph matching CASA journal provenance | graph overlap |
| CZ-Mo4 | Partner efferent with provenance tag, not script read | ADR-0078 |

Fixture: extract DN→motor subgraph from edgelist (`super_class` filter).

---

## 6. Follow-up

- `banc_subgraph.py` add **CZ-Mo** (desc→motor).
- MCNS compare for dimorphic motor (doc 09-social overlap).
- Link Shiu et al. 2024: optogenetic DN → motor firing validated in fly — use as external probe reference.
