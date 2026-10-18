# BANC grounding: Perceptual Zone
**Status:** draft (P0)  
**Date:** 2026-09-19  
**CASA:** ADR-0063 · ADR-0061 `perceptual` · ADR-0024 (control thalamus — global, not duplicate)  
**Data:** BANC v888

---

## 1. CASA surface (what we built)

**Perceptual Zone** = sensory gate **before** spatial/linguistic/executive routing (0063).

```text
RAW (vk, pixels, listen bytes, CA-CV)
        │
        ▼
  agent-percept-core   ← modality routers, quantize
        │
        ├──► spatial (vis quantize)
        ├──► linguistic (text stream)
        └──► executive (thalamus bandwidth — 0024)
```

**Not duplicate:** control thalamus = global arousal/wake-sleep; perceptual = **channel-specific** fan-out.

---

## 2. BANC slice (queries + numbers)

| Cohort | Count | Notes |
|--------|-------|-------|
| `sensory` (super_class) | 16 563 | afferent periphery |
| `visual_projection` | 7 316 | optic → CB relay |
| `optic_lobe_intrinsic` | 72 947 | massive visual compute mass |
| flow=afferent | 17 089 | explicit afferent tag |

**Sensory cell_class top:** bristle (6k), ORN (3k), chordotonal (2.1k), **photoreceptor (1.8k)**, taste bristle (1.2k).

**body_part_sensory top:** antenna 4.2k · hind_leg 1.9k · **retina 1.8k** · legs · interommatidial · abdomen · wing.

**Visual projection fan-out:** 629 825 outgoing edges → targets:
- CB intrinsic 216k
- VP (recurrent) 182k
- optic intrinsic 164k
- visual centrifugal 17k
- **descending 15.7k** (direct VP→DN skip?)

**Read:** perceptual is **thick at periphery** (16k+ sensors + 73k optic intrinsic), **thin at executive interface** (VP→DN is small vs VP→CB).

---

## 3. Motifs

```text
  RETINA / ORN / bristle / taste
           │
           ▼
    optic_lobe_intrinsic  (73k — local feature)
           │
           ▼
    visual_projection     (7k — columnar relay)
           │
     ┌─────┴─────┐
     ▼           ▼
 CB intrinsic   descending (sparse executive tap)
```

| Fly | CASA |
|-----|------|
| modality-specific receptors | vk / listen / vis quantize channels |
| optic lobe = heavy local CA | spatial zone + vis lattices (planned) |
| VP = relay to higher areas | perceptual → domain fan-out |
| DOOMFLY: R1–R6 + R8 → 4k photoreceptor drive | `listen_womb_tick` / cochlear_stub analog |

---

## 4. Rhyme / Gap / Port

| | Rhyme | Gap | Port |
|---|-------|-----|------|
| **Gate before cortex** | sensory → VP → CB, not raw to executive | text/listen sometimes bypass perceptual | **enforce** perceptual quantize on all modalities |
| **Modality channels** | ORN vs photoreceptor vs taste = separate classes | single undifferentiated input stream | `agent-percept-core` routers per modality |
| **Thick periphery** | 73k optic intrinsic = most neurons | spatial zone stub | vis lattices = **local** NCA, not executive |
| **Sparse executive tap** | VP→DN only 2.5% of VP out-edges | DAN reads whole field | executive read **only** post-perceptual digest |
| **body_part map** | antenna/leg/retina tags | no somatotopy in field | optional `body_part_sensory` → lattice region tags |

---

## 5. Probes

| ID | Probe | Pass |
|----|-------|------|
| CZ-P1 | Raw listen bytes never reach `lattice_fpn_wm` without perceptual digest | audit trace |
| CZ-P2 | Modality ablation (vis off) drops only vis-scoped tracts | duck test |
| CZ-P3 | VP→CB path latency < VP→executive direct (if any) | tick budget |
| CZ-P4 | Photoreceptor-count analog: N sensory drive units ≈ order of fly R1–R6 scale for vis stub | design bound |

---

## 6. Follow-up

- Wire perceptual fan-out in `agent-bootstrap-manifest.v1.json` explicitly.
- Cross-ref DOOMFLY photoreceptor mapping as **external prior** (not CASA canon).
- Spatial zone (08) depends on this doc.
