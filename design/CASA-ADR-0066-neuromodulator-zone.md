# ADR-0066: Neuromodulator Zone (interoceptive dynamics + gain bus)

**Status:** accepted (design)  
**Date:** 2026-06-07  
**Related:** ADR-0058 (limbic affect), ADR-0060 (Emotional Zone), ADR-0061 (Intelligence Zones), ADR-0062 (genetic surprise_gains), ADR-0064 (metabolic / somatic proxy), ADR-0065 (sleep recovery), ADR-0059 (innate tick order), ADR-0010 (predict / DAN / value), [agent-bootstrap-manifest.v1.json](agent-bootstrap-manifest.v1.json)

---

## Context

**Emotional Zone (0060)** даёт limbic **appraisal**: valence, arousal, security, episodic flags (`dialog.repair_pending`). Life events (`self_failure`, `partner_repair_invite`, …) сразу сдвигают оси.

У человека эмоциональная жизнь **не** сводится к этому слою:

| Уровень | Пример | CASA сегодня |
|---------|--------|--------------|
| **Somatic / interoception** | «сжало», учащённое дыхание, «не тянет тело» | metabolic ATP/fatigue — **зачаток**, без panic contour |
| **Neuromodulator dynamics** | страх/тревога **держатся**, нарастают, затухают | **нет** — только мгновенные delta на event |
| **Limbic appraisal** | «это угроза / потеря лица» | Emotional Zone |
| **Conscious control** | reappraisal, defer, «скажу честно» | executive, disposition |

**Без «движения внутри»** (decay, coupling, inertia) получается **метка состояния**, а не прожитая траектория: после `self_failure` arousal не «остаётся на взводе» три–десять тиков; нет панического контура (arousal ↑ → metabolic cost ↑ → хуже compose → ещё arousal).

**Invariant:** executive **не порождает** эмоцию — он **регулирует** уже идущий subcortical процесс (может defer/укоротить, **не может** мгновенно обнулить neuromodulator).

Literal DA/5-HT/NE в коде **не вводим** — функциональный **gain bus** с врождённой чувствительностью из genetic (0062).

---

## Decision

### 1. Neuromodulator Zone в карте 0061

| Property | Value |
|----------|-------|
| Zone id | `neuromodulator` |
| Role | continuous internal dynamics; cross-zone gain scales |
| Tier | **Subcortical bus** — **между** somatic/metabolic и limbic; **ниже** executive |
| Sandbox | `agent-neuromod-sandbox` — policy experiments (decay/coupling), **не** cheat fatigue |
| Core | `agent-neuromod-core` — live modulator state + last tick physics |

**Not duplicate:**

| Organ | Question |
|-------|----------|
| metabolic | *сколько ресурса осталось?* (ATP, sleep) |
| neuromodulator | *с каким gain сейчас всё работает?* (inertia, threat tone) |
| emotional | *как оцениваю ситуацию?* (axes, episodic) |
| executive | *что сознательно делаю?* (plan, defer, DAN request) |

### 2. State block (v0)

```text
prism_agent
└── intelligence_zones
    └── neuromodulator
        ├── core
        │   ├── arousal_drive      [0, 1]  fast, slow decay — acute stress / panic
        │   ├── threat_tone        [0, 1]  sustained insecurity / anxiety baseline
        │   ├── approach           [0, 1]  curiosity, trust-openness (reward/error)
        │   ├── regulatory_load    [0, 1]  cost of executive holding control
        │   └── tick_last
        ├── interoception          ← derived each tick (not operator JSON)
        │   ├── autonomic_load     metabolic + surprise jolt
        │   ├── panic_risk         f(arousal_drive, threat_tone, atp)
        │   └── recovery_bias      post-sleep / partner_trust bleed
        ├── zone_policy            decay, coupling, ceilings (sandbox-promotable)
        ├── core_lattice_id        agent-neuromod-core
        └── sandbox_lattice_id     agent-neuromod-sandbox
```

**T=0:** все modulators **нейтральны** (не «пусто»): e.g. `arousal_drive=0.08`, `threat_tone=0.12`, `approach=0.45`, `regulatory_load=0.05`.

**Namespace:** `agent.neuromod.*` (core), `agent.neuromod.lab.*` (sandbox).

### 3. Tick physics (v0)

Each macro tick **after** somatic inputs, **before** emotional appraisal apply:

```text
1. interoception_read(metabolic, predict_surprise, idle?)
2. neuromodulator_integrate(drives from events + interoception)
3. neuromodulator_decay()                    ← inertia / recovery
4. neuromodulator_couple()                   ← cross-terms (panic spiral)
5. publish_gain_scales() → zones + control
```

**Decay (default, genetic-tunable):**

| Variable | τ (ticks to halve) | Notes |
|----------|-------------------|--------|
| `arousal_drive` | ~4 | быстрый спад без нового stimulus |
| `threat_tone` | ~12 | тревожный фон |
| `approach` | ~8 | trust/curiosity |
| `regulatory_load` | ~3 | executive «устал удерживать» |

**Coupling (default):**

| When | Effect |
|------|--------|
| `self_failure` event | `arousal_drive += 0.22`, `threat_tone += 0.08`, `regulatory_load += 0.06` |
| `prediction_error` (P8) | `arousal_drive += k × surprise_n` (k from genetic) |
| `partner_trust` | `approach += 0.12`, `threat_tone -= 0.06` |
| `arousal_drive > 0.65` ∧ `threat_tone > 0.5` | **panic_risk** → extra metabolic debit (0064) |
| `panic_risk > 0.7` | `regulatory_load += 0.1` per tick (executive strain) |
| `/sleep` success | `arousal_drive ×= 0.4`, `threat_tone ×= 0.7`, `regulatory_load ×= 0.5` |

**Emotional Zone** больше **не получает сырые event deltas напрямую** (migration path):  
`effective_delta = event_delta × gain(arousal_drive, threat_tone, approach)` — limbic **appraisal modulated**, не replaced.

### 4. Gain bus — куда течёт

| Consumer | Scale (example) |
|----------|-----------------|
| Emotional `affect_after_turn` | event deltas × `(1 + arousal_drive)` on arousal axis |
| Tract competition | social boost × `approach`; math penalty × `threat_tone` when panic_risk |
| DAN / attention | spotlight cap × `(1 - regulatory_load)`; boost cap from genetic × `arousal_drive` |
| Metabolic | `cost_compose_token × (1 + 0.5×arousal_drive)`; panic surcharge |
| Compose budget | `max_tokens × (1 - 0.4×regulatory_load)` when panic_risk high |
| Executive disposition | defer probability ↑ with `regulatory_load`; honest defer ↑ with `threat_tone` + repair_pending |
| Value P9 (replay) | replay priority ↑ when `threat_tone` elevated after self_failure |

**Verbalize:** compose **не обязан** сказать «мне страшно» — gain смещает **выбор** и **длину**; lexicon fear — один кандидат среди поля.

### 5. Layer cake (target tick order)

```text
genetic.read
→ perceptual_gate
→ thalamus (arousal gate)
→ metabolic.begin
→ predict (P8) ──────────────┐
→ interoception_read ◄───────┤ somatic + visceral jolt
→ neuromodulator.integrate   │
→ neuromodulator.decay       │  «движение внутри»
→ neuromodulator.publish_gains
→ emotional.read / events (modulated deltas)
→ executive (SN/FPN/DAN — gains applied)
→ tract → bind (gains) → compose
→ emotional.update / character EMA
→ metabolic.end → (forced_sleep?)
→ neuromodulator.persist
```

REPL partner-turn **минимум:** steps from `interoception_read` through `publish_gains` before `intelligence_before_partner_compose`.

### 6. Bootstrap manifest (planned — **disabled** until P10 code)

```json
"neuromodulator_zone": {
  "enabled": false,
  "adr": "0066",
  "spawn_on_bootstrap": false,
  "core_lattice_id": "agent-neuromod-core",
  "sandbox_lattice_id": "agent-neuromod-sandbox",
  "concept_prefix_core": "agent.neuromod.",
  "concept_prefix_sandbox": "agent.neuromod.lab.",
  "initial_core": {
    "arousal_drive": 0.08,
    "threat_tone": 0.12,
    "approach": 0.45,
    "regulatory_load": 0.05
  },
  "policy": {
    "decay_halflife_ticks": {
      "arousal_drive": 4,
      "threat_tone": 12,
      "approach": 8,
      "regulatory_load": 3
    },
    "panic_arousal_threshold": 0.65,
    "panic_threat_threshold": 0.5
  },
  "note": "Subcortical gain bus; enable after P10a spawn + integrate"
}
```

**Genetic (0062) extension (planned):**

```json
"surprise_gains": {
  "neuromod_arousal_per_surprise": 0.04,
  "neuromod_threat_on_self_failure": 0.08,
  "dan_boost_cap": 24
},
"zone_proportions": {
  "neuromodulator": 0.9
}
```

### 7. API (target: `casa/prisms/neuromodulator/`)

| Function | Role |
|----------|------|
| `spawn_neuromodulator_zone` | cold boot lattices + neutral core |
| `interoception_read` | metabolic + P8 → autonomic_load, panic_risk |
| `neuromodulator_begin_tick` | decay + integrate pending drives |
| `neuromodulator_after_event` | life event / P8 → drive deltas |
| `neuromodulator_gain_scales` | `{tract, affect, dan, metabolic, compose}` |
| `neuromodulator_snapshot` | provenance / REPL verbose |
| `neuromodulator_after_sleep` | recovery bleed |

### 8. Rollout

| Phase | Action |
|-------|--------|
| **P10a** | ADR + spawn + persist; no hot path yet |
| **P10b** | `integrate` + `decay` on partner turn; emotional deltas scaled |
| **P10c** | metabolic + compose budget coupling; panic_risk |
| **P10d** | predict P8 → neuromodulator; DAN cap from gains |
| **P10e** | probes: self_failure → elevated arousal_drive **≥5 ticks** without new stimulus |
| **P10f** | autonomous `agent_life` loop same physics |

### 9. Tests (acceptance)

| Probe | Pass |
|-------|------|
| `self_failure` then 3× idle partner silence | `arousal_drive` still > T0+0.1 at tick 3 |
| `partner_trust` after repair arc | `threat_tone` ↓, `approach` ↑ |
| panic_risk high | compose token budget ↓ vs baseline |
| `/sleep` after storm | drives drop; metabolic ATP partial recovery |
| executive defer under high `regulatory_load` | disposition defers more often **without** new keyword router |

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| Literal `dopamine.py` / operator mood JSON | functional drives + genetic sensitivity |
| Emotion = instant axis jump on keyword | events → neuromodulator → scaled limbic |
| Executive instantly clears panic | sleep, trust, decay, time |
| Duplicate metabolic ATP in threat_tone | interoception **reads** metabolic, separate state |
| Neuromodulator sandbox writes core without promote | same 0060/0061 promote θ |
| New zone type at runtime | closed catalog; allelic fork only (0065) |

---

## Consequences

- Emotional life becomes **trajectory**, not snapshot — prerequisite for anxiety/panic **functionally**, not narratively.
- ADR-0058 «interoception gap» closes via metabolic feed + neuromodulator (not simulated HR).
- ADR-0060 emotional core **stays**; event vocabulary unchanged; **apply path** gains modulator.
- Migration: additive spawn; default neutral; **no** rewrite of dialogue ring.
- von-neumann curriculum (0057): situations test **afterglow** and repair, not only same-turn bias.

## Links

- [CASA-ADR-0058-limbic-affect-prism.md](CASA-ADR-0058-limbic-affect-prism.md)
- [CASA-ADR-0060-emotional-zone.md](CASA-ADR-0060-emotional-zone.md)
- [CASA-ADR-0061-intelligence-zones.md](CASA-ADR-0061-intelligence-zones.md)
- [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md)
- [CASA-ADR-0064-metabolic-zone.md](CASA-ADR-0064-metabolic-zone.md)
- [CASA-ADR-0065-controlled-mutations.md](CASA-ADR-0065-controlled-mutations.md)
- [CASA-ADR-0059-innate-organ-basis.md](CASA-ADR-0059-innate-organ-basis.md)
