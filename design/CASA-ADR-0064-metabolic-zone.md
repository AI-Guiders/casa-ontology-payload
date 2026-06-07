# ADR-0064: Metabolic Zone (cognitive budget / fatigue / sleep gate)

**Status:** accepted (design v1)  
**Date:** 2026-06-07  
**Related:** ADR-0061 (executive + emotional surprise), ADR-0062 (genetic surprise_gains), ADR-0065 (sleep-merge experiential drift), ADR-0010 (value P9 / sleep), ADR-0055 (WM capacity), [agent-bootstrap-manifest.v1.json](agent-bootstrap-manifest.v1.json)

---

## Context

Инференс von-neumann **не обязан** быть бесконечным: длинная phrase chain, surprise storm, overload без sleep → **зависание рантайма** (observed: overnight hang).

Куски уже есть **без зоны**:
- `cognitive_overload` + `initiate_from_overload` в agency;
- WM `theta_*`, prune, max_scratch;
- REPL `/sleep`, hippo merge.

Но нет **единого ресурсного контура** — **Metabolic Zone**: накопитель «АТФ тика», принудительный downshift приоритетов, **hard trigger** sleep-merge.

---

## Decision

### 1. Metabolic Zone в карте 0061

| Property | Value |
|----------|-------|
| Zone id | `metabolic` |
| Role | tick energy budget, fatigue, sleep pressure |
| Tier | Intelligence Zone **P8** |
| Sandbox | `agent-metabolic-sandbox` — policy experiments (not fatigue cheat) |
| Core | `agent-metabolic-core` — live ATP counters |

**Not duplicate:** executive surprise counter = **signal**; metabolic = **integrated cost** + **actuation** (defer, sleep).

### 2. State block

```text
prism_agent
└── intelligence_zones
    └── metabolic
        ├── atp_current          1.0 … 0.0  (tick budget)
        ├── fatigue_ema          slow accumulator
        ├── sleep_pressure       0 … 1  (trigger sleep merge)
        ├── tick_cost_last       breakdown
        ├── forced_sleep         bool
        ├── core_lattice_id      agent-metabolic-core
        └── policy
            ├── atp_per_tick_base
            ├── cost_surprise
            ├── cost_compose_token
            ├── cost_bind_block
            ├── recovery_per_idle_tick
            └── sleep_threshold
```

**Genetic defaults (0062):** `surprise_gains.metabolic_fatigue`, `atp_per_tick_base`, `sleep_threshold` — **read-only** after seal.

### 3. Tick accounting

Each macro tick debits ATP:

| Event | Cost (default) | Source |
|-------|----------------|--------|
| Base tick | 0.02 | policy |
| Tract competition + bind | 0.05 + 0.001×blocks | bind |
| Compose phrase chain | 0.03 + 0.008×tokens | discourse |
| Surprise spike (P8) | `cost_surprise × surprise_n` | executive + genetic |
| WM promote edge | 0.04 | WM prism |

**Recovery:** idle tick (no partner input) +0.06 ATP; `/sleep` success resets fatigue_ema partially.

### 4. Actuation (when ATP low or sleep_pressure high)

| Threshold | Behavior |
|-----------|----------|
| `atp < 0.35` | defer secondary tracts (discuss, journal); social/math only |
| `atp < 0.20` | force short reply budget (compose max tokens) |
| `sleep_pressure ≥ 0.85` | **forced_sleep** → enqueue sleep merge before next partner turn |
| `fatigue_ema > 0.9` | REPL banner + suggest `/sleep` |

**Invariant:** metabolic **может** cut inference; **не может** mutate genetic zone or delete journal.

### 5. Tick order hook

```text
metabolic.begin_tick()           ← reserve ATP
  … thalamus → perceptual → zones → compose …
metabolic.end_tick(surprise, compose_stats)
  → update fatigue_ema, sleep_pressure
  → if forced_sleep: schedule sleep (hippo)
```

REPL: after each line, `metabolic_end`; if `forced_sleep`, auto-run `_run_sleep` or refuse long compose.

### 6. Bootstrap manifest (planned → P8)

```json
"metabolic_zone": {
  "enabled": true,
  "adr": "0064",
  "spawn_on_bootstrap": true,
  "core_lattice_id": "agent-metabolic-core",
  "sandbox_lattice_id": "agent-metabolic-sandbox",
  "concept_prefix_core": "agent.metabolic.",
  "initial_atp": 1.0,
  "policy": {
    "atp_per_tick_base": 0.02,
    "cost_surprise": 0.08,
    "cost_compose_token": 0.008,
    "sleep_threshold": 0.85,
    "recovery_per_idle_tick": 0.06
  }
}
```

### 7. API (target: `casa/prisms/metabolic/`)

| Function | Role |
|----------|------|
| `spawn_metabolic_zone` | cold boot |
| `metabolic_begin_tick` | reserve budget |
| `metabolic_end_tick` | debit + fatigue |
| `metabolic_allows(tract_id)` | gate competition |
| `metabolic_compose_budget` | max tokens |
| `metabolic_should_sleep` | trigger sleep merge |
| `metabolic_snapshot` | provenance / REPL verbose |

### 8. Rollout

| Phase | Action |
|-------|--------|
| **P8a** | ADR + spawn + persist in zone_state |
| **P8b** | REPL accounting + `/sleep` auto when pressure high |
| **P8c** | wire surprise → fatigue via genetic gains |
| **P8d** | agent_autonomous_tick sleep gate |

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| Infinite compose while ATP=0 | hard token cap |
| Sleep only manual | sleep_pressure auto |
| Overload string without counter | metabolic state |
| Fatigue stored in emotional axes | separate zone; emotional *reads* pressure optional |

---

## Consequences

- Protects runtime from hang; **does not** replace situation curriculum (0057).
- ADR-0062 genome owns default costs; metabolic sandbox may **propose** policy deltas → promote with θ (not genome mutation).
- `forced_sleep` / merge success — окно для experiential NCA drift (ADR-0065), не allelic fork.
- Migration: von-neumann additive spawn; `initial_atp = 1.0`.

## Links

- [CASA-ADR-0061-intelligence-zones.md](CASA-ADR-0061-intelligence-zones.md)
- [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md)
- [CASA-ADR-0065-controlled-mutations.md](CASA-ADR-0065-controlled-mutations.md)
- [CASA-ADR-0010-control-zone-predict-attention-value.md](CASA-ADR-0010-control-zone-predict-attention-value.md)
