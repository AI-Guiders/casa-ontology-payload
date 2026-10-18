# BANC × CASA — synthesis port map
**Status:** draft (capstone)  
**Date:** 2026-09-19  
**Inputs:** leaf docs 01–13 · BANC v888 · MCNS v1.0 (partial)  
**KB:** `note-casa-control-zone-banc-grounding.md`

---

## 1. Executive summary

Fly CNS connectome = **wiring spec** for organizational motifs, not executable CASA code. Across 13 zones:

| Verdict | Zones |
|---------|-------|
| **Strong structural rhyme** | executive, perceptual, memory/MB, motor, neuromodulator, spatial/CX, genetic, defense |
| **Partial / proxy** | emotional, social, metabolic, character |
| **CASA-only (honest)** | linguistic, logical |

**Core thesis confirmed:** evolution builds on a fixed scaffold (isomorphic 97%) with sparse dimorphic/specialized modules; CASA should **grow-to-spec** matching **motif statistics**, not copy 188 508 nodes.

---

## 2. Unified port table (actionable → roadmap)

| Priority | Port | Source motif | Target ADR / code | Probe |
|----------|------|--------------|-------------------|-------|
| **P0** | DAN `sparse_ratio` ≈ 0.12–0.15 | A/D touch 12% edges | ADR-0010 `lattice_dan` | CZ-E1 |
| **P0** | Perceptual gate before executive | VP→DN 2.5% fan-out | ADR-0063 enforce | CZ-P1 |
| **P0** | Value-weighted consolidate | MB DAN 301 → Kenyon | ADR-0009 + 0010 | CZ-M1 |
| **P0** | Bounded efferent alphabet | 805 motor, 1316 DN | `cen_act` / FSR | CZ-Mo1 |
| **P1** | 4-channel neuromod bus | DA/OA/5HT/GABA sparse overlay | ADR-0066 | CZ-N1–N4 |
| **P1** | CX-sized spatial module (~3k scale) | PFN/FS 2982 neurons | spatial zone ADR | CZ-S1–S4 |
| **P1** | `hemilineage` → tract priors | 259 lineages | ADR-0062 genetic | CZ-G1–G4 |
| **P1** | Social channel typing | pheromone volatile/contact | partner wire | CZ-So2 |
| **P2** | Metabolic integral + auto sleep | circadian/peptide proxy | ADR-0064 | CZ-Me1 |
| **P2** | Fast_path escape tier | GFC 35 neurons | ADR-0076 | CZ-D1 |
| **P2** | Character field EMA | isomorphic scaffold + dimorphic 2% | ADR-0071 | CZ-C1 |
| **P3** | Sparse gate metaphor only | LH/Kenyon | ADR-0073 | CZ-L2 |
| **—** | No connectome-in-LLM | FlyGPT negative controls | anti-pattern | — |

---

## 3. Cross-zone dependency graph

```text
genetic (10) ──► all zones @ T=0
perceptual (02) ──► spatial (08) ──► executive (01) ──► motor (07)
       │                │
       └──► memory (03) ◄── neuromod (04) ◄── emotional (05)
                    │              │
                    └── metabolic (06) ── sleep
       social (09) ──► emotional ──► character (13)
       defense (11) ◄── threat (fast + slow)
linguistic (12) ── own curriculum (gate metaphor from 02/03)
```

---

## 4. Fixture backlog (CI)

| Fixture | Source doc | Est. nodes |
|---------|------------|------------|
| `banc_cz-s1.json` | 01, 07 | ≤5k |
| `banc_mb.json` | 03 | ≤5k |
| `banc_nt_bus.json` | 04 | ≤10k |
| `banc_cx.json` | 08 | ≤10k |
| `banc_innate_catalog.json` | 10 | table only |
| `banc_gfc.json` | 11 | <100 |
| — | 12 | **none** (by design) |

Tool: `tools/banc_subgraph.py` — extend slices CZ-S8, CZ-Mo, MB, GFC.

---

## 5. Proposed lab ADRs (follow-up)

| ADR | Title | Blocks on |
|-----|-------|-----------|
| `CASA-ADR-00XX` | Control zone BANC grounding | CZ-E1 green |
| `CASA-ADR-00XX` | Perceptual gate enforcement | CZ-P1 |
| `CASA-ADR-00XX` | Neuromodulator gain bus v2 | CZ-N1 |
| `CASA-ADR-00XX` | Spatial CX grow-to-spec | CZ-S1 |
| `CASA-ADR-00XX` | Genetic catalog pin (BANC v888) | CZ-G1 |

Single umbrella optional; prefer **small addenda** per zone per hub anti-pattern.

---

## 6. Anti-patterns (series closure)

| ❌ Rejected | Evidence |
|-------------|----------|
| Photocopy 188k into field | scale + wrong substrate |
| LLM + frozen connectome | FlyGPT ≈ scramble |
| Manual pixel→button as «brain» | DOOMFLY adapter, not ontology |
| Fly language analog | 12-linguistic negative |
| Tier-2 EM before motifs | tier-1 sufficient for this series |

---

## 7. MCNS dimorphism gap

BANC ♀ atlas under-reports male-specific (8 neurons). **MCNS v1.0** required for:

- courtship song motor
- fruitless/dsx expression overlays
- social (09) + genetic (10) dimorphic ports

Action: `malecns_match` join table in fixture phase.

---

## 8. Discussion agenda (for operator review)

1. **P0 ports** — approve sparse_ratio target and perceptual gate as hard invariants?  
2. **Grow-to-spec** — which zone first: CX (08) or DN subgraph (01)?  
3. **Neuromod** — 4 functional channels vs richer neuropeptide bus?  
4. **Linguistic** — confirm out-of-scope for BANC fixtures.  
5. **Lab ADR** — one umbrella vs per-zone addenda.  
6. **bench** — `bench_banc_cascade_vs_predict.py` priority in toolchain.

---

## 9. Doc index

| # | Doc | Status |
|---|-----|--------|
| 00 | [hub](00-hub.md) | ✅ |
| 01 | [executive](01-executive-control.md) | P0 ✅ |
| 02 | [perceptual](02-perceptual.md) | P0 ✅ |
| 03 | [memory/hippo](03-memory-hippo.md) | P0 ✅ |
| 04 | [neuromodulator](04-neuromodulator.md) | P1 ✅ |
| 05 | [emotional](05-emotional-limbic.md) | P1 ✅ |
| 06 | [metabolic](06-metabolic-sleep.md) | P2 ✅ |
| 07 | [motor](07-motor-efferent.md) | P0 ✅ |
| 08 | [spatial](08-spatial-navigation.md) | P1 ✅ |
| 09 | [social](09-social-partner.md) | P2 ✅ |
| 10 | [genetic](10-genetic-innate.md) | P1 ✅ |
| 11 | [defense](11-defense-survival.md) | P2 ✅ |
| 12 | [linguistic](12-linguistic-logical.md) | P3 ✅ |
| 13 | [character](13-character-slow.md) | P2 ✅ |
| 99 | synthesis (this) | ✅ |

**Series complete** — ready for operator discussion.
