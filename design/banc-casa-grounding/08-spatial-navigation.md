# BANC grounding: Spatial / Navigation (Central Complex)
**Status:** draft (P1)  
**Date:** 2026-09-19  
**CASA:** ADR-0061 `spatial` · vis/spatial lattices (planned) · ADR-0024 thalamus bandwidth  
**Data:** BANC v888 central complex cohort

---

## 1. CASA surface (what we built)

**Spatial Zone** (0061) — heading, layout, body-in-space. Today: **stub** relative to perceptual/executive; vis quantize exists, full spatial prism partial.

Planned: local NCA for optic-like processing; CX analog for **egocentric heading + path integration**.

---

## 2. BANC slice (queries + numbers)

**Central complex neurons:**

| cell_class | Count |
|------------|-------|
| CX intrinsic | 1 184 |
| CX input | 984 |
| CX output | 814 |
| **Total CX** | **2 982** |

**CX-touching edges:** 283 040.

**cns_network:** `central complex related` — 2 896 neurons in that partition.

**Key cell_types:**

| Type | Count | Role (lit) |
|------|-------|------------|
| PFN* (PFNa/p/d/e…) | 471 | path integration / heading |
| FS* (FS1A, FS2, FS4A…) | 273 | fan-shaped body columnar |
| BM_InOm | 1 212 | bridge medulla↔CX (input) |

**DA in CX:** 287 output + 125 intrinsic + 33 input — dopamine-tagged navigation/error.

**Region:** `central_brain` 47 688 neurons (broader than CX proper).

**Read:** navigation is a **compact dedicated circuit** (~3k neurons, ~1.6% of CNS) with heavy edge traffic — not delegated to full 73k optic intrinsic mass.

---

## 3. Motifs

```text
  visual / proprio (BM_InOm, PFN inputs)
              │
              ▼
     ellipsoid_body / fan-shaped_body
         (FS columns, PFN)
              │
              ▼
     CX output ──► descending / motor steering
              │
         DA error on mismatch
```

| Fly CX | CASA spatial |
|--------|--------------|
| PFN heading integrator | egocentric pose lattice |
| FS columnar map | 2D field slice for body heading |
| CX→DN | spatial digest → executive plan |
| DA on nav error | predict lattice PE on pose |

---

## 4. Rhyme / Gap / Port

| | Rhyme | Gap | Port |
|---|-------|-----|------|
| **Dedicated module** | 3k CX vs 73k optic | spatial zone undeveloped | **grow-to-spec** CX-sized module, not full optic copy |
| **Compact output** | 814 CX output | spatial feeds whole executive | CX-output analog → **digest only** to `lattice_dmn` |
| **High edge density** | 283k CX edges | no path integration metric | probe: pose error → DN-equivalent surprise |
| **Separate from perceptual** | optic intrinsic ≠ CX | vis and spatial merged | keep 02-perceptual local; 08 = heading only |
| **DA teach on nav** | CX DA neurons | value not pose-specific | nav PE → value channel subset |

---

## 5. Probes

| ID | Probe | Pass |
|----|-------|------|
| CZ-S1 | Egocentric pose state survives ≥10 ticks without sensory refresh | drift bound |
| CZ-S2 | Rotated visual input → pose update, not full rebind | duck test |
| CZ-S3 | CX-subgraph cascade depth ≈ predict rollout k | correlation |
| CZ-S4 | Spatial digest size ≪ perceptual field (compact output) | cardinality |

Fixture: `banc_cx.json` — PFN+FS+CX I/O ≤10⁴ nodes.

---

## 6. Follow-up

- Extract CX subgraph in `banc_subgraph.py` (new `cz_s8_cx`).
- Cross-ref 01-executive (DN steering), 07-motor (wing/leg effector).
- Literature: CX compass + path integration (Hulse & Jayaraman reviews) — external cite only.
