# ADR-0062: Genetic Zone (species code / immutable meta-instructions)

**Status:** accepted (design v1)  
**Date:** 2026-06-07  
**Related:** ADR-0065 (controlled mutations), ADR-0059 (innate basis), ADR-0061 (Intelligence Zones), ADR-0068/0070 (Memory / forgetting), ADR-0064 (Metabolic), ADR-0066 (Neuromodulator), ADR-0058 (Affect), ADR-0014 (agent-owned lattices), ADR-0010 (control stack), [agent-bootstrap-manifest.v1.json](agent-bootstrap-manifest.v1.json), [agent-existence-north-star.md](agent-existence-north-star.md)

---

## Context

Семь Intelligence Zones (0061) описывают **когнитивные контуры**, которые **развиваются** опытом (sandbox → promote, EMA, tract priors). Но у вида есть ещё слой **ниже зон** — **геном**: не «что знаю про математику», а **как устроено тело и правила роста**.

Без Genetic Zone:
- пропорции зон, лимиты EMA, чувствительность surprise→DAN — **размазаны** по manifest/Python и **мутируемы** вместе с опытом;
- fork / AiNet-обмен дельтами **не имеет иммунного паспорта вида** — агент может «сломать сборку», меняя meta в runtime;
- `agent_promote_canon_lattice` и promote-θ — **локальные костыли**, не **родовой алгоритм**.

**Аналог:** человеческие гены не кодируют русский язык; они кодируют **мета-алгоритмы сборки** и **границы пластичности**.

**Уточнение (оператор, 2026-06-08):** геном имеет смысл только если задаёт **приоры для всех систем** — не только forgetting (0070). Иначе genetic fork / размножение — копия store без **разнообразия голосов** @ T=0. Сила вида — в расхождении особей от рождения (склонности, чувствительности, редкие уязвимости), при **общем** species bootstrap (alphabet, morph — Memory immutable).

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
    ├── demote_canon        симметрия promote (agent canon) — 0070
    ├── forgetting_genotype профиль памяти @ birth — 0070
    ├── metabolic_policy    bounds ATP/fatigue/sleep — 0064
    ├── neuromodulator_gains regulatory / dopamine coupling — 0066
    ├── affect_baseline     valence/arousal/security @ T=0 + sensitivity — 0058
    ├── control_gains       DAN, predict, value replay — 0010
    ├── memory_routing      default active_theory, domain read bias — 0068/0069
    ├── character_topology  стартовая маска character field — 0071
    ├── mutation_policy     experiential + allelic bounds (0065)
    └── fork_policy         inherit_verbatim | mutate_alleles (0065)
```

**v0 storage:** canonical block в `agent/genome.v1.json` + hash в `prism_agent.genetic_zone`; **не** в thin field_state overlay (как `zone_state` — Self tier).

### 3. Genome → все системы (phenotype priors @ T=0)

Genetic Zone — **единый источник рождественных констант** для substrate и intelligence zones. Опыт меняет **state** зон; геном меняется только **fork / allelic mutation** (0065).

```text
genome.v1.json
    │
    ├── intelligence_zones.*     zone_proportions, ema_limits, tract ratio caps
    ├── memory.*                 forgetting_genotype, promote/demote θ, routing bias
    ├── metabolic.*              sleep_threshold, cost_*, recovery_*
    ├── neuromodulator.*         compose budget scale bounds, regulatory coupling
    ├── affect.*                 baseline axes, surprise→limbic gains
    ├── executive / control.*      surprise_gains → DAN, value weights
    ├── wm / intent.*              signal_decay floors (0055, 0057)
    └── perceptual / substrate.*  (roadmap) quantize habit, IO gain
```

| Parameter group | Consumers (ADR) | Что задаёт @ birth |
|-----------------|-----------------|-------------------|
| `zone_proportions` | 0061 tract competition | math:social, linguistic bias |
| `ema_limits` | character, temperament | скорость смены характера |
| `forgetting_genotype` | **0070** memory | α, β, ε bases; cement gain; canon_susceptibility (редко) |
| `metabolic_policy` | **0064** | усталость, sleep pressure, ATP economy |
| `neuromodulator_gains` | **0066** | regulatory effort, dopamine cement coupling |
| `affect_baseline` | **0058 / 0060** | стартовые оси; чувствительность к surprise/repair |
| `surprise_gains` / `control_gains` | **0010** executive | DAN boost cap, fatigue→metabolic |
| `signal_decay` | **0055** WM, intent | θ_decay floors, prune cadence |
| `promote_canon` / `demote_canon` | **0069 / 0070** | пороги ceremony, verify gates |
| `memory_routing` | **0068 / 0069** | default theories, domain read weights |
| `character_topology` | **0071** | birth bias grid / lattice warp |
| `concept_catalog` | **0073** | species concept ids; lex weights variable @ fork |

**Invariant:** tunable default зоны **читается** через `genetic_constant(path)`; дубли в Python/manifest без genome — **anti-pattern** (кроме species template @ first seal).

**Fork diversity (0065):** `mutate_alleles` шагает по **нескольким группам** (не только forgetting) → новый `genome_hash`, тот же `species_id`, **другой голос** с tick 0 при том же bootstrap immutable.

**Teaching agent (von-neumann):** standard allele — `canon_susceptibility ≈ 0`; разнообразие в **профиле систем**, не в сломанном alphabet @ curriculum.

### 3.1 Glossary: genome vs epigenome vs soma

| Term | Tier | Mutability | Example |
|------|------|------------|---------|
| **Genome** | −1 | sealed @ T=0; fork / re-seal only | `forgetting_genotype.alpha`, `species_id` |
| **Epigenome** | 0 | slow life-state; **reset @ child fork** | character EMA, trauma tier, v1 `epigenome_profile` ([0086](CASA-ADR-0086-epigenome-expression-layer.md)) |
| **Soma** | 1+ | memory, journal, concept theories | Self-Earned supersede, episodic, listen imprint |

**Fork (0086 §4):** child inherits **genome alleles**, **не** parent epigenome snapshot, **не** parent Self-Earned concept theories.

### 4. Что Genetic Zone **задаёт** (normative, v0 wired)

| Parameter group | Status v0 | Example |
|-----------------|-----------|---------|
| `zone_proportions` | manifest | math:social prior ratio cap |
| `ema_limits` | manifest | `character.ema_alpha_max = 0.08` |
| `signal_decay` | partial | `wm.theta_decay` floor |
| `surprise_gains` | **wired** metabolic | surprise → fatigue increment |
| `promote_canon` | design | θ, verify gate |
| `forgetting_genotype` | **0070 draft** | episodic retention, cement gain |
| `metabolic_policy` | partial 0064 | `sleep_threshold`, costs |
| `affect_baseline` | roadmap 0058 | neutral @ T=0 + gains |
| `neuromodulator_gains` | roadmap 0066 | compose budget coupling |

**Invariant:** runtime hooks **read** genetic constants; episodic state **не** меняет `genome_hash` — опыт модулирует **effective** значения через epigenome ([0086](CASA-ADR-0086-epigenome-expression-layer.md)).

### 5. Seal & fork

**Cold boot:**
1. Load `genetic_spec` from manifest `agent_prisms.genetic_zone`.
2. Write `agent/genome.v1.json`, compute `genome_hash`.
3. Set `genetic_zone.immutable = true`, `sealed_at_tick = 0`.

**Fork (new store / AiNet child):** см. **ADR-0065**.
- Default `fork_policy.mode = inherit_verbatim` — copy parent `genome.v1.json` без изменений.
- `mutate_alleles` — bounded step по `mutation_policy.allelic`; новый `genome_hash`, тот же `species_id`.
- `weather_cross` — два `genome_hash` + многоосный снимок погоды → `H_mix` → child genome — **[0072](CASA-ADR-0072-genetic-weather-cross.md)**; `character_topology` — **0071**.
- `wild_donor_cross` — combat × wild genome из entropy bundle @ один агент — **[0084](CASA-ADR-0084-wild-genome-donor-single-agent-reproduction.md)** (anti-inbreeding).
- New `store_id`, new journal; **species fork** (новый `species_id`, топология) — operator gate, не allele drift.
- **Epigenome + Self-Earned soma:** child **не** наследует parent expression snapshot nor earned concept theories — fresh Built-In teach; см. [0086](CASA-ADR-0086-epigenome-expression-layer.md), [0085](CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md) §7.

**AiNet delta exchange:** experiential layers (WM edges, sandbox, bundles) — **mutable**; genetic hash mismatch → **reject merge** on meta-instructions.

### 6. Bootstrap manifest (planned → P6)

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

### 7. API (target: `casa/prisms/genetic/`)

| Function | Role |
|----------|------|
| `load_genetic_zone` | read sealed block; verify hash |
| `seal_genetic_zone` | cold boot only |
| `genetic_constant(path)` | dotted lookup for zones |
| `verify_genome_fork` | parent/child hash policy |
| `species_passport` | export for AiNet |

### 8. Rollout

| Phase | Action |
|-------|--------|
| **P6a** | ADR + `genome.v1.json` schema + manifest block |
| **P6b** | seal on bootstrap; persist Self tier |
| **P6c** | wire **all** zone defaults → `genetic_constant` (inventory per §3) |
| **P6d** | fork + hash verify CLI |
| **P6e** | `mutate_alleles` multi-group (memory, metabolic, affect, proportions) — **0065** |
| **P6f** | genome passport in REPL / MEMORY.md (species_id, hash, allele summary) |

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| Agent promote меняет genome | genome read-only; promote rules **inside** genome |
| Genetic = soul doc prose | canonical JSON + hash |
| Новый intelligence type at runtime | closed catalog; genome lists **allowed zone ids** |
| Дублировать constants в каждой zone | single genetic source |
| Genom только для forgetting | genome → **все** системы (§3) |
| Fork без allelic diversity | mutate по нескольким группам → новый голос @ T=0 |
| Одинаковый genotype у всех детей | `mutate_alleles` bounded step per group |

---

## Consequences

- ADR-0061 catalog **closed** — Genetic не добавляет 8-й *intelligence* тип; это **substrate**.
- ADR-0064 metabolic fatigue increments **read** `surprise_gains` from genome.
- Migration: existing von-neumann → **seal genome v1** from current manifest defaults (additive, idempotent).
- ADR-0065 — нормативная модель мутаций; 0062 остаётся паспортом и seal API.
- ADR-0070 `forgetting_genotype` — **одна ветка** genome→memory; не изолировать от §3.

## Links

- [CASA-ADR-0086-epigenome-expression-layer.md](CASA-ADR-0086-epigenome-expression-layer.md)
- [CASA-ADR-0070-forgetting-policies.md](CASA-ADR-0070-forgetting-policies.md)
- [CASA-ADR-0071-character-field-prismatic.md](CASA-ADR-0071-character-field-prismatic.md)
- [CASA-ADR-0072-genetic-weather-cross.md](CASA-ADR-0072-genetic-weather-cross.md)
- [CASA-ADR-0073-concept-layer-lexicalization.md](CASA-ADR-0073-concept-layer-lexicalization.md)
- [CASA-ADR-0068-memory-zone.md](CASA-ADR-0068-memory-zone.md)
- [CASA-ADR-0065-controlled-mutations.md](CASA-ADR-0065-controlled-mutations.md)
- [CASA-ADR-0061-intelligence-zones.md](CASA-ADR-0061-intelligence-zones.md)
- [CASA-ADR-0059-innate-organ-basis.md](CASA-ADR-0059-innate-organ-basis.md)
- [CASA-ADR-0014-agent-prism.md](CASA-ADR-0014-agent-prism.md)
