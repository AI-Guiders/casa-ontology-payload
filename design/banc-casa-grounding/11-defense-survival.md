# BANC grounding: Defense / Survival
**Status:** draft (P2)  
**Date:** 2026-09-19  
**CASA:** ADR-0076 · ADR-0074 · ADR-0075 trauma cement  
**Data:** BANC v888 escape / nociception cohort

---

## 1. CASA surface (what we built)

**Defense Intelligence Zone** (0076) — psychological defense + survival gate. Distinct from emotional (reads axes) and memory (marks hot recall).

| Mechanism | CASA |
|-----------|------|
| trauma_edges | long-lived core |
| repression / confab | counters |
| defense_genotype | 0062 @ T=0 |
| sandbox rechannel | experiments → promote |

0074: defense catalog. 0075: trauma cement on survival events.

---

## 2. BANC slice (queries + numbers)

**Giant fiber escape circuit:**

| Type | Count | NT |
|------|-------|-----|
| GFC1–GFC4 | **35** total | ACh (all) |
| super_class | VNC intrinsic | — |

Giant fiber = **ultra-fast** looming/escape path (lit: <10ms leg extension).

**Nociception:**

| Cohort | Count |
|--------|-------|
| nociception (cell_function) | 213 |
| multidendritic (class) | 170 |
| VNC neurosecretory | 43 |

**Threat innate module:** `super_cluster` **threat_response** — 160 neurons.

**Aversive routing:** multidendritic → ascending → DN (sparse, fast) parallel to slow LH appraisal.

**Read:** defense in fly = **dual path** — (1) giant fiber hardwired escape, (2) nociceptive peptidergic slow pain, (3) small threat_response cluster for innate bias.

---

## 3. Motifs

```text
  looming / nociceptive
        │
   ┌────┴────┐
   ▼         ▼
GFC (35)   multidendritic (170)
 fast ACh    slow peptide
   │         │
   └────┬────┘
        ▼
   motor escape / DN suppress
        │
  threat_response cluster (160) — innate bias
```

| Fly | CASA defense |
|-----|--------------|
| giant fiber | **fast_path** survival bind (bypass compose) |
| nociception | trauma_cement on pain_threshold events |
| threat_response cluster | defense_genotype innate module |
| repression analog | hot recall filter (0074) |

---

## 4. Rhyme / Gap / Port

| | Rhyme | Gap | Port |
|---|-------|-----|------|
| **Fast vs slow** | GFC vs peptidergic | single defense latency | **two-tier**: fast_path + limbic appraisal |
| **Tiny escape core** | 35 neurons | overload path unbounded | cap fast_path triggers/tick |
| **Trauma persistence** | nociceptive + neurosecretory | episodic fades fast | cement edges on survival (0075) |
| **Innate threat** | 160 super_cluster | defense all learned | T=0 threat_response stub (10) |
| **Not psychology** | escape ≠ repression | — | map GFC→fast_path only; repression = CASA mechanism |

---

## 5. Probes

| ID | Probe | Pass |
|----|-------|------|
| CZ-D1 | Survival signal → fast_path act < N ticks compose | latency |
| CZ-D2 | Same event → trauma_edge persists post-sleep | cement |
| CZ-D3 | Repression reduces hot recall without deleting journal | filter |
| CZ-D4 | fast_path rate limited per tick | cap |

Fixture: `banc_gfc.json` — GFC subgraph + motor targets.

---

## 6. Follow-up

- Extract GFC → leg motor edges from edgelist.
- Cross-ref 05-emotional (arousal read), 10-genetic (defense_genotype).
- DOOMFLY damage→dopamine: **fast aversive teach**, not defense zone duplicate.
