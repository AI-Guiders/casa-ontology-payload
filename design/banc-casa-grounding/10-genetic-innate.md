# BANC grounding: Genetic / Innate catalog
**Status:** draft (P1)  
**Date:** 2026-09-19  
**CASA:** ADR-0062 · ADR-0059 · ADR-0065 · ADR-0086 epigenome  
**Data:** BANC v888 (`hemilineage`, `super_cluster`, `sexually_dimorphic`, `cell_type`)

---

## 1. CASA surface (what we built)

**Genetic Zone** = Tier −1 species substrate (0062). Sealed @ T=0: zone proportions, surprise_gains, defense/trauma genotype, character topology priors. **Not** an Intelligence Zone — no sandbox, no hot-path writes.

| Content | CASA |
|---------|------|
| species bootstrap | manifest genetic_zone |
| allelic fork | 0065 controlled mutations |
| innate tick order | 0059 |
| phenotype expression | 0086 epigenome layer |

Fly analog: **hemilineage + cell_type catalog** = developmental wiring spec, not learned content.

---

## 2. BANC slice (queries + numbers)

| Catalog field | Coverage |
|---------------|----------|
| **hemilineage** (unique) | **259** lineages · **50 501** neurons tagged |
| **super_cluster** (behavior groups) | 4 238 tagged |
| **cell_type** | fine-grained (thousands of types) |
| **sexually_dimorphic** | 3 816 dimorphic-ish vs 114 571 isomorphic |

**Top hemilineages:**

| hemilineage | Count | Note |
|-------------|-------|------|
| MBp | 4 552 | Kenyon cells |
| putative_primary | 3 921 | sensory primaries |
| 20A.22A | 785 | lineage block |
| VPNd2 | 779 | visual projection lineage |

**super_cluster (innate behavior modules):**

| Cluster | Count |
|---------|-------|
| head orienting | 389 |
| postural control | 369 |
| middle-hind leg | 335 |
| flight power | 323 |
| **reproduction** | 252 |
| walking | 248 |
| **threat response** | 160 |

**Cross-dataset anchors:** `malecns_match` 23 608 · `hemibrain_match` · `fafb_match` — same neuron across atlases.

**Read:** innate = **typed catalog + lineage constraints**; experience writes on top (MB still has 4552 Kenyon slots fixed at birth).

---

## 3. Motifs

```text
  genome / hemilineage (259)
        │
        ▼
  cell_type catalog @ eclosion
        │
   ┌────┴────┐
   ▼         ▼
isomorphic   dimorphic (2%)
(114k)       (social/motor rewrite)
        │
        ▼
  connectome edges (fixed topology, plastic synapses in life)
```

| Fly | CASA genetic |
|-----|--------------|
| hemilineage | `genetic_zone.tract_priors` |
| cell_type | lattice template ids @ T=0 |
| super_cluster | innate behavior modules (defense, reproduction) |
| dimorphic flag | sex/role allele table |
| cross-atlas match | species bootstrap version pin |

---

## 4. Rhyme / Gap / Port

| | Rhyme | Gap | Port |
|---|-------|-----|------|
| **Sealed meta** | topology fixed at eclosion | manifest params drift in runtime | genetic_zone **read-only** mirror; fork via 0065 only |
| **Lineage blocks** | 259 hemilineages | flat manifest keys | `hemilineage` → zone proportion priors |
| **Innate modules** | super_cluster behavior | all behavior learned | T=0 enable **threat/reproduction/walking** stubs |
| **Dimorphism as allele** | 2% dimorphic | ignored in single agent | `dimorphic_hotspots` table from BANC+MCNS |
| **Not content** | Kenyon count fixed, odor memory learned | risk: encoding lexicon in genome | **immutable** only alphabet/morph (0069), not facts |

---

## 5. Probes

| ID | Probe | Pass |
|----|-------|------|
| CZ-G1 | Hot-path write to genetic_zone → rejected | invariant |
| CZ-G2 | Fork changes `surprise_gains` but not episodic journal | allelic diff |
| CZ-G3 | T=0 zone proportions within genetic bounds | audit |
| CZ-G4 | `threat_response` innate module wired before first life event | bootstrap trace |

---

## 6. Follow-up

- Export `hemilineage` × `super_class` crosstab → `tools/fixtures/banc_innate_catalog.json`.
- MCNS: fruitless/dsx expression overlays (male courtship) — extend in 09/10.
- Lab ADR: genetic_zone pins BANC catalog **version**, not full 188k graph.
