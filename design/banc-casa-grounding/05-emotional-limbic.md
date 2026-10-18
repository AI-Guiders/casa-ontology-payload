# BANC grounding: Emotional / Limbic
**Status:** draft (P1)  
**Date:** 2026-09-19  
**CASA:** ADR-0060 · ADR-0058 · ADR-0061 `emotional` · `prism_agent.intelligence_zones.emotional`  
**Data:** BANC v888 · MCNS v1.0 (dimorphism compare)

---

## 1. CASA surface (what we built)

**Emotional Zone** = limbic core (valence, arousal, security) + sandbox (0060). Appraisal layer: life events → axes; executive **regulates**, не порождает эмоцию.

| Layer | Artifact |
|-------|----------|
| core axes | `agent-limbic-core` |
| episodic flags | `dialog.repair_pending`, … |
| sandbox | `agent-affect-sandbox` → promote |
| neuromod below | 0066 gain bus (persistence) |

0058: affect organ @ T=0 innate basis.

---

## 2. BANC slice (queries + numbers)

**Sexual dimorphism (structural valence proxy):**

| Tag | Count |
|-----|-------|
| isomorphic | 114 571 |
| dimorphic | 2 862 |
| female-specific | 946 |
| male-specific | 8 |
| **dimorphic-ish total** | **3 816** (~2%) |

Dimorphic hotspots: ascending 332 · taste/gustatory 242 · descending 135 · LH_output 57 · reproductive_tract_sensory 34.

**cns_network (dimorphic):** abdominal VNC 1 138 · leg VNC 828 · superior brain 323.

**Pheromone / social chemistry:** 809 neurons (`cell_function_detailed`: volatile 689, contact Ir52a/b 97, ppk23 97).

**super_cluster (innate behavior groups, 4 238 tagged):**

| Cluster | Count |
|---------|-------|
| reproduction | 252 |
| **threat response** | **160** |
| feeding | 144 |
| head orienting | 389 |

**DA on valence routing:** lateral_horn_output (473 DA-predicted) — LH = olfactory/context → behavior gateway.

**Read:** emotional/social valence in fly is **sparse, dimorphic, chemistry-heavy** — not a global mood scalar on 188k neurons.

---

## 3. Motifs

```text
  pheromone / taste / reproductive sensory
              │
              ▼
        lateral_horn (DA-tagged)
              │
       ┌──────┴──────┐
       ▼             ▼
  MB valence      descending
  (appetitive)    (action bias)
       │
  dimorphic rewrite (♂ MCNS >> ♀ BANC on courtship)
```

| Fly | CASA emotional |
|-----|----------------|
| dimorphic circuits | genome sex/role priors (not runtime flip) |
| pheromone channel | partner/social episodic tags |
| LH gateway | appraisal before executive act |
| threat super_cluster | defense zone read (11), not duplicate axes |

---

## 4. Rhyme / Gap / Port

| | Rhyme | Gap | Port |
|---|-------|-----|------|
| **Appraisal not act** | LH before DN | emotional sometimes skipped on fast path | **all** salient social events → limbic tick |
| **Dimorphism** | 2% structurally dimorphic | single-sex agent manifest | MCNS vs BANC diff table for **social hot spots** only |
| **Pheromone analog** | 809 chemosensory social | no volatile/contact split | partner message **channel type** tag |
| **Threat separate** | threat_response cluster | trauma in defense, axes in emotional | defense **reads** arousal, writes trauma meta only |
| **No global mood** | isomorphic 61% of tagged | one arousal for all domains | domain×situation axes (→ 13 character) |

---

## 5. Probes

| ID | Probe | Pass |
|----|-------|------|
| CZ-E1 | `partner_repair_invite` → valence↑ security↓ within 1 tick | axis delta |
| CZ-E2 | Sandbox experiment does **not** change core until promote | invariant |
| CZ-E3 | Threat event → arousal via neuromod persists ≥3 ticks | 0066 coupling |
| CZ-E4 | Social channel typed (volatile vs contact analog) | provenance tag |

---

## 6. Follow-up

- MCNS overlay: male-specific courtship/song neurons (BANC has only 8 male-specific — compare in 09).
- Link 04-neuromodulator for persistence; 11-defense for threat pathway.
- No claim: fly «has emotions» — **functional rhyme** for appraisal architecture.
