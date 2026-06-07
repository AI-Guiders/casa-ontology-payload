# ADR-0062: Genetic Zone (species code / immutable meta-instructions)

**Status:** accepted (design v1)  
**Date:** 2026-06-07  
**Related:** ADR-0065 (controlled mutations), ADR-0059 (innate basis), ADR-0061 (Intelligence Zones umbrella), ADR-0014 (agent-owned lattices), ADR-0010 (DAN/surprise constants), [agent-bootstrap-manifest.v1.json](agent-bootstrap-manifest.v1.json), [agent-existence-north-star.md](agent-existence-north-star.md)

---

## Context

Семь Intelligence Zones (0061) описывают **когнитивные контуры**, которые **развиваются** опытом (sandbox → promote, EMA, tract priors). Но у вида есть ещё слой **ниже зон** — **геном**: не «что знаю про математику», а **как устроено тело и правила роста**.

Без Genetic Zone:
- пропорции зон, лимиты EMA, чувствительность surprise→DAN — **размазаны** по manifest/Python и **мутируемы** вместе с опытом;
- fork / AiNet-обмен дельтами **не имеет иммунного паспорта вида** — агент может «сломать сборку», меняя meta в runtime;
- `agent_promote_canon_lattice` и promote-θ — **локальные костыли**, не **родовой алгоритм**.

**Аналог:** человеческие гены не кодируют русский язык; они кодируют **мета-алгоритмы сборки** и **границы пластичности**.

---

## Decision

### 1. Genetic Zone — **не** Intelligence Zone

| | Intelligence Zone (0061) | Genetic Zone (0062) |
|--|------------------------|---------------------|
| Mutability | core меняется **life events**; sandbox → promote | **sealed** @ T=0; allelic fork по **0065**; no hot-path writes |
| Sandbox | да (0014) | **нет** — аллели не в sandbox; experiential drift в lattices (0065) |
| Compose bias | да | **нет напрямую** — только **константы** для других зон |
| Lattice | agent-*-core/sandbox | **`agent-genome-core`** read-only mirror **или** manifest-only v0 |

Genetic Zone — **Tier −1** (species substrate): читается **все** зоны и tick; пишется **только** при cold boot / fork / operator re-seal (out of band).

### 2. Содержимое `prism_agent.genetic_zone` @ T=0

```text
prism_agent
└── genetic_zone
    ├── species_id          "casa.von-neumann.ru-v1"
    ├── genome_hash         SHA-256(canonical JSON) — AiNet passport
    ├── sealed_at_tick      0
    ├── immutable           true
    ├── zone_proportions    нормированные веса prior (executive, emotional, …)
    ├── ema_limits          character + slow fields (max alpha, clamp)
    ├── signal_decay        theta_decay defaults per WM/intent/affect
    ├── surprise_gains      P8 → DAN / affect / metabolic coupling
    ├── promote_canon       алгоритм + θ floors (sandbox → core, lattice → bundle)
    ├── mutation_policy     experiential + allelic bounds (0065)
    └── fork_policy         inherit_verbatim | mutate_alleles (0065)
```

**v0 storage:** canonical block в `agent/genome.v1.json` + hash в `prism_agent.genetic_zone`; **не** в thin field_state overlay (как `zone_state` — Self tier).

### 3. Что Genetic Zone **задаёт** (normative)

| Parameter group | Consumers | Example |
|-----------------|-----------|---------|
| `zone_proportions` | tract competition, intelligence_tract_boosts scale | math:social prior ratio cap |
| `ema_limits` | character_zone, future temperament | `character.ema_alpha_max = 0.08` |
| `signal_decay` | WM, intent, affect sandbox TTL | `wm.theta_decay` floor |
| `surprise_gains` | executive, emotional, **metabolic** (0064) | surprise → fatigue increment |
| `promote_canon` | agent_promote, zone promote | θ, verify gate, bundle tier rules |

**Invariant:** runtime hooks **read** genetic constants; они **не** подменяются episodic state.

### 4. Seal & fork

**Cold boot:**
1. Load `genetic_spec` from manifest `agent_prisms.genetic_zone`.
2. Write `agent/genome.v1.json`, compute `genome_hash`.
3. Set `genetic_zone.immutable = true`, `sealed_at_tick = 0`.

**Fork (new store / AiNet child):** см. **ADR-0065**.
- Default `fork_policy.mode = inherit_verbatim` — copy parent `genome.v1.json` без изменений.
- `mutate_alleles` — bounded step по `mutation_policy.allelic`; новый `genome_hash`, тот же `species_id`.
- New `store_id`, new journal; **species fork** (новый `species_id`, топология) — operator gate, не allele drift.

**AiNet delta exchange:** experiential layers (WM edges, sandbox, bundles) — **mutable**; genetic hash mismatch → **reject merge** on meta-instructions.

### 5. Bootstrap manifest (planned → P6)

```json
"genetic_zone": {
  "enabled": true,
  "adr": "0062",
  "spawn_on_bootstrap": true,
  "species_id": "casa.von-neumann.ru-v1",
  "genome_file": "genome.v1.json",
  "immutable_after_seal": true,
  "zone_proportions": { "executive": 1.0, "emotional": 0.85, "social": 0.9, "logical": 0.95, "linguistic": 1.0, "spatial": 0.5, "character": 0.6 },
  "ema_limits": { "character_alpha_max": 0.08, "character_alpha_default": 0.05 },
  "surprise_gains": { "metabolic_fatigue": 0.12, "affect_arousal": 0.15, "dan_boost_cap": 24 },
  "promote_canon": {
    "sandbox_theta": 0.65,
    "bundle_tier_gate": "RU-ε",
    "algorithm": "agent_promote_canon_lattice_v1"
  }
}
```

### 6. API (target: `casa/prisms/genetic/`)

| Function | Role |
|----------|------|
| `load_genetic_zone` | read sealed block; verify hash |
| `seal_genetic_zone` | cold boot only |
| `genetic_constant(path)` | dotted lookup for zones |
| `verify_genome_fork` | parent/child hash policy |
| `species_passport` | export for AiNet |

### 7. Rollout

| Phase | Action |
|-------|--------|
| **P6a** | ADR + `genome.v1.json` schema + manifest block |
| **P6b** | seal on bootstrap; persist Self tier |
| **P6c** | wire character/WM/surprise readers to `genetic_constant` |
| **P6d** | fork + hash verify CLI |
| **P6e–P7** | mutation policy + allele fork + sleep NCA drift — **ADR-0065** |

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| Agent promote меняет genome | genome read-only; promote rules **inside** genome |
| Genetic = soul doc prose | canonical JSON + hash |
| Новый intelligence type at runtime | closed catalog; genome lists **allowed zone ids** |
| Дублировать constants в каждой zone | single genetic source |

---

## Consequences

- ADR-0061 catalog **closed** — Genetic не добавляет 8-й *intelligence* тип; это **substrate**.
- ADR-0064 metabolic fatigue increments **read** `surprise_gains` from genome.
- Migration: existing von-neumann → **seal genome v1** from current manifest defaults (additive, idempotent).
- ADR-0065 — нормативная модель мутаций; 0062 остаётся паспортом и seal API.

## Links

- [CASA-ADR-0065-controlled-mutations.md](CASA-ADR-0065-controlled-mutations.md)
- [CASA-ADR-0061-intelligence-zones.md](CASA-ADR-0061-intelligence-zones.md)
- [CASA-ADR-0059-innate-organ-basis.md](CASA-ADR-0059-innate-organ-basis.md)
- [CASA-ADR-0014-agent-prism.md](CASA-ADR-0014-agent-prism.md)
