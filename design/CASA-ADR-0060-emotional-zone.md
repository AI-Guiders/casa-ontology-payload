# ADR-0060: Emotional Zone (limbic core + agent sandbox)

**Status:** accepted  
**Date:** 2026-06-07  
**Related:** ADR-0058 (affect organ), ADR-0059 (innate basis), ADR-0014 (agent-owned lattices), ADR-0057 (character EMA), [agent-bootstrap-manifest.v1.json](agent-bootstrap-manifest.v1.json)

---

## Context

Нейману нужна **лимбика с T=0** (0058/0059) **и** право **экспериментировать** (0014), не запортачивая live core. У человека — фиксированная лимбика + пластичность **внутри**; у CASA — **Emotional Zone**: два слоя под контролем агента.

---

## Decision

### Emotional Zone = `prism_agent.intelligence_zones.emotional`

```text
prism_agent
└── intelligence_zones
    └── emotional
    ├── core (limbic)          ← innate T=0; hot path compose/disposition
    │   ├── axes               valence, arousal, security
    │   ├── episodic           dialog.repair_pending, …
    │   └── lattice            agent-limbic-core  (agent.limbic.*)
    └── sandbox (test layer)   ← agent experiments; не трогает core напрямую
        ├── lattice            agent-affect-sandbox  (agent.affect.lab.*)
        ├── experiments[]      черновики delta / гипотезы
        └── promote → core     только явное promote (θ)
```

| Слой | Кто пишет core axes | Lattice |
|------|---------------------|---------|
| **Core** | subject-side tick hooks (life events) | read + co-place; **не** произвольный place в axes |
| **Sandbox** | агент (`place`, scratch, NCA train) | полный ADR-0014 контроль |
| **Promote** | агент | sandbox experiment → сдвиг core axes (clamped) |

**Invariant:** `sandbox_writes_core: false` — эксперимент **не** меняет valence/security до **promote**.

### Namespace

| Prefix | Слой | Пример |
|--------|------|--------|
| `agent.limbic.*` | core lattice | `agent.limbic.valence`, `agent.limbic.security` |
| `agent.affect.lab.*` | sandbox | `agent.affect.lab.try-openness` |
| `agent.emotion.event.*` | episodic tag | `agent.emotion.event.self_failure` |

### Bootstrap (T=0)

Manifest `agent_prisms.emotional_zone`:

- spawn `agent-limbic-core` + `agent-affect-sandbox`
- neutral axes `(0, 0.2, 0.5)`
- journal note: sandbox для проб, core — то, что пережито и закреплено

### API (`casa/prisms/affect/`)

| Function | Role |
|----------|------|
| `ensure_emotional_zone` | block in `intelligence_zones.emotional` |
| `spawn_emotional_zone` | cold boot lattices + core |
| `core_affect_state` | read axes/episodic |
| `affect_after_turn` | life events → core (not teacher) |
| `sandbox_record_experiment` | agent draft delta |
| `promote_sandbox_experiment` | agent → core axes |
| `affect_compose_bias` | reweight hints for bind/compose |

Character prism (0057) — **slow EMA** поверх `core.axes`, не отдельная зона v0.

### Life events → core (v0)

Same as ADR-0058: `self_failure`, `partner_repair_invite`, `self_repair_success`, `partner_trust`, `partner_greeting`, `prediction_error`.

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| Agent `place` напрямую в core axes | sandbox → promote |
| Soul doc / operator mood JSON | T=0 neutral + life + promote |
| `ru.dialog.affect` as inner state | lexicon only |
| Unlimited sandbox lattices | `max_sandbox_lattices` policy |

---

## Consequences

- ADR-0058 implementation **lives in** Emotional Zone core layer.
- Bootstrap manifest gains `emotional_zone` alongside wm/intent.
- von-neumann cold boot **must** spawn zone before curriculum.
- Tests: `tests/test_emotional_zone.py`.

## Links

- [CASA-ADR-0058-limbic-affect-prism.md](CASA-ADR-0058-limbic-affect-prism.md)
- [CASA-ADR-0059-innate-organ-basis.md](CASA-ADR-0059-innate-organ-basis.md)
- [CASA-ADR-0066-neuromodulator-zone.md](CASA-ADR-0066-neuromodulator-zone.md)
- [CASA-ADR-0014-agent-prism.md](CASA-ADR-0014-agent-prism.md)
