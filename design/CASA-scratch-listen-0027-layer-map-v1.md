# Scratch: listen pilot — ADR-0027 layer map (as implemented)

**Status:** scratch — фиксирует **где что лежит сейчас**, чтобы не забыть при C0 curriculum / C1 wire  
**Date:** 2026-06-21  
**Parent:** [CASA-ADR-0027-sensory-motor-periphery-mcp.md](CASA-ADR-0027-sensory-motor-periphery-mcp.md), [CASA-ADR-0028-field-native-sensory-experience.md](CASA-ADR-0028-field-native-sensory-experience.md), [CASA-ADR-0083-curriculum-ontology-agent-store.md](CASA-ADR-0083-curriculum-ontology-agent-store.md), [CASA-scratch-listen-wire-gap-v1.md](CASA-scratch-listen-wire-gap-v1.md)

---

## One-line

Listen A/V pilot = **partial 0027**: `file_replay` adapters + codecs + compositor (`listen_moment` / `womb_tick`) → brain imprint. **Not yet:** Transport queue, FieldBus `PerceptReady`, live mic MCP as Neumann tract, somatosensory.

---

## Layer map (listen aud + vis)

| 0027 layer | Module(s) | Backend @ pilot | Notes |
|------------|-----------|-----------------|-------|
| **Periphery** | corpus files, `video.mp4`, manifest ndjson | `file_replay` / `file_replay_stream` | mic/headphone/file = **same adapter contract** once live backend exists |
| **Adapter** | `casa/sensory/adapters/listen_corpus.py`, `media_path.py` | `capture_listen_scene`, `capture_listen_stream` | resolves paths; **no imprint** |
| **Contracts** | `casa/sensory/contracts.py` | `ListenCorpusCapture`, `ListenStreamCapture`, `RawCapture` | provenance `backend_id` on moment result |
| **Codec** | `casa/sensory/codecs/retinal_lrgb.py`, `cochlear_stub.py` | inside `imprint_*` | field-native tokens, not OCR subs |
| **Perception helpers** | `load_rgb_frame`, `load_wav`, `chapter_scene_cuts` | stream frame extract | host-side feature path |
| **CCU / compositor** | `casa/prisms/memory/listen_moment.py`, `casa/domain/listen_womb_tick.py` | one moment / stream step | packages scene → imprint + optional life tick |
| **Brain** | `imprint_auditory/visual`, `run_life_tick`, sleep | `agents/von-neumann` | ADR-0028 primary tracts |

```text
manifest + video.mp4 + wav
  → adapters.capture_listen_*     (ADR-0027 §2)
  → codecs + load_*               (perception/codec)
  → listen_moment / womb_stream   (compositor + brain ingest)
  → field_state + life tick
```

---

## What is **not** this stack

| Concern | Where it lives | Not listen adapter |
|---------|----------------|-------------------|
| **Curriculum ontology** | `casa/curriculum/` → teach @ store (ADR-0083) | symbolic school graph |
| **Concept Zone** | `concept_layer.py` | 4-hub stub + earned promote |
| **Limbic valence** | `casa/prisms/affect/` | model axes, not taste/smell/touch |
| **Partner text efferent** | `process_dialogue_on_tick` | separate tract |
| **Operator webcam MCP** | host prosthesis | not Neumann somatosensory until wired as backend |

---

## Backend registry (normative ids)

| `backend_id` | Source | Entry API |
|--------------|--------|-----------|
| `file_replay` | listen corpus manifest scene | `capture_listen_scene` |
| `file_replay_stream` | chapter video + wav + wall-clock | `capture_listen_stream` |
| *(future)* `mcp_webcam_capture` | live AV burst | ADR-0027 §2 — not implemented |
| *(future)* `somatosensory_*` | pressure/touch sensors | **new tract** — not aud/vis adapter swap |

**Rule:** new peripheral = new `backend_id` + adapter module; **do not** fork `listen_moment` per vendor.

---

## Open (0027 gap backlog)

- [ ] `casa/sensory/transport/` — async queue, backpressure
- [ ] FieldBus publish on `capture_listen_*` complete (optional observability)
- [ ] `sensory_profile` in store manifest (`capture_backend`, pipeline id)
- [ ] Live mic backend implementing same capture contracts
- [ ] Somatosensory tract (body / physical sensors) — separate from this map

---

## Tests

- `tests/test_sensory_listen_adapter.py` — adapter resolve
- `tests/test_listen_moment*.py` — compositor + imprint (unchanged API)

---

## Related commits intent

Refactor only: **move path resolution out of `listen_moment`** into `casa/sensory/adapters/`; public imports preserved via re-exports.
