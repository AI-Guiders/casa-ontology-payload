# ADR-0063: Perceptual Zone (sensory gate / thalamic input)

**Status:** accepted (design v1)  
**Date:** 2026-06-07  
**Related:** ADR-0024 (control thalamus), ADR-0061 (spatial + linguistic), ADR-0059 (innate basis), input modality / VK-field, [agent-bootstrap-manifest.v1.json](agent-bootstrap-manifest.v1.json)

---

## Context

Сырой ввод (VK scan-codes, CA-CV 64×64, text listen field, keyboard layout) сегодня **размазан**:
- thalamus — в **executive** по 0061, но **не** gating REPL;
- spatial — stub без активного vis;
- linguistic — WM/intent + semantic_read **напрямую** из текста.

Биологически **рецепторное поле** изолировано: сигнал **очищается, квантуется**, затем **веером** идёт в cortical areas — не в одну «general» трубу.

**Perceptual Zone** = **Sensory Gate @ T=0**: единый шлюз **до** spatial/linguistic/executive routing.

---

## Decision

### 1. Perceptual Zone в карте 0061

| Property | Value |
|----------|-------|
| Zone id | `perceptual` (alias: sensory_gate) |
| Intelligence | первичная перцепция / thalamic relay |
| Tier | Intelligence Zone **P7** |
| Sandbox | `agent-percept-sandbox` — calibration experiments only |
| Core | `agent-percept-core` — modality routers |

**Not duplicate:** control thalamus (0024) = **global arousal / wake-sleep bandwidth**; perceptual = **channel-specific quantization & fan-out**.

### 2. Architecture

```text
RAW INPUT (vk, pixels, audio stub, text bytes)
        │
        ▼
┌───────────────────────────────────────┐
│  Perceptual Zone (agent-percept-core) │
│  • denoise / debounce                 │
│  • modality classify                  │
│  • quantize → percept tokens          │
└───────────────────────────────────────┘
        │ fan-out (weighted by genetic proportions 0062)
        ├──────────────┬──────────────┬─────────────►
        ▼              ▼              ▼
   spatial_zone   linguistic_path   executive
   (where?)       (lang.word.*,     (salience /
                   grapheme)         surprise seed)
```

### 3. Modality registry (T=0)

| Modality | Source module | Percept token prefix | Primary fan-out |
|----------|---------------|----------------------|-----------------|
| **keyboard** | vk_layout, keyboard ortho | `percept.vk.*` | linguistic + executive |
| **text_stream** | text_listen, REPL stdin | `percept.text.*` | linguistic |
| **visual** | CA-CV 64×64 (roadmap) | `percept.vis.*` | spatial + executive |
| **proprio** | tick meta (stub) | `percept.self.*` | executive + emotional |

**Invariant:** bind/compose **не** читают RAW; только **percept tokens** или downstream concept_hints **после** gate.

### 4. State block

```text
prism_agent
└── intelligence_zones
    └── perceptual
        ├── core_lattice_id     agent-percept-core
        ├── sandbox_lattice_id  agent-percept-sandbox
        ├── active_modalities[] keyboard, text_stream
        ├── last_tokens[]       ring buffer (hot)
        ├── noise_floor         calibrated
        └── fan_out_weights     override genetic defaults per modality
```

### 5. Tick placement

```text
RAW → perceptual_gate.read()     ← NEW (before semantic_read)
  → thalamus bandwidth (0024)
  → predict / zones.read
  → semantic_read(concept_hints += percept_tokens)
  → …
ACT → perceptual_gate.learn()    optional sandbox record
```

REPL today skips this block — **target:** `_partner_reply` passes stdin through `perceptual_gate` first.

### 6. Bootstrap manifest (planned → P7)

```json
"perceptual_zone": {
  "enabled": true,
  "adr": "0063",
  "spawn_on_bootstrap": true,
  "core_lattice_id": "agent-percept-core",
  "sandbox_lattice_id": "agent-percept-sandbox",
  "concept_prefix_core": "agent.percept.",
  "concept_prefix_sandbox": "agent.percept.lab.",
  "active_modalities": ["keyboard", "text_stream"],
  "fan_out": {
    "keyboard": { "linguistic": 0.7, "executive": 0.3 },
    "text_stream": { "linguistic": 0.85, "social": 0.15 }
  }
}
```

### 7. API (target: `casa/prisms/perceptual/`)

| Function | Role |
|----------|------|
| `spawn_perceptual_zone` | cold boot lattices |
| `perceptual_ingest(raw, modality)` | gate → tokens |
| `perceptual_fan_out(tokens)` | hints for spatial/linguistic/executive |
| `perceptual_sandbox_calibrate` | agent adjusts noise_floor (sandbox) |

### 8. Rollout

| Phase | Action |
|-------|--------|
| **P7a** | ADR + lattice spawn + text_stream path for REPL |
| **P7b** | keyboard/VK hook into gate |
| **P7c** | vis fan-out when spatial enabled |
| **P7d** | provenance `perceptual_zone` on dialogue turns |

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| semantic_read parses stdin alone | perceptual → hints |
| Spatial ingests pixels directly | percept → spatial |
| Thalamus = full perceptual stack | split global arousal vs channel gate |
| Teacher templates per modality | emergent routing from tokens + genetic weights |

---

## Consequences

- ADR-0061 **linguistic** zone (future) receives input **only** post-perceptual.
- ADR-0062 genetic `zone_proportions` scales fan-out defaults.
- Tests: REPL line → `percept.text.*` tokens in provenance before bind.

## Links

- [CASA-ADR-0024-control-thalamus.md](CASA-ADR-0024-control-thalamus.md)
- [CASA-ADR-0061-intelligence-zones.md](CASA-ADR-0061-intelligence-zones.md)
- [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md)
