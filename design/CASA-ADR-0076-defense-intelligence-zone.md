# ADR-0076: Defense Intelligence Zone

**Status:** accepted (P20a–c wired)  
**Date:** 2026-06-09  
**Related:** ADR-0061 (zones umbrella), ADR-0074 (defenses), ADR-0075 (trauma cement), ADR-0060 (emotional), ADR-0068 (memory), ADR-0071 (character), ADR-0062 (genome)

---

## Context

0074/0075 реализовали механизмы в `casa/prisms/defense/`, state в плоском `state.defense`. Оператор справедливо спросил: **не отдельная ли это зона?**

У человека защиты — не «хук на bind», а **контур** с:

- innate substrate @ T=0 (genome `defense_genotype`, `trauma_cement_genotype`);
- долгоживущим core (trauma edges, repression history);
- sandbox для rechannel/sublimation experiments;
- orchestration на tick после limbic update.

По паттерну ADR-0061 это **Intelligence Zone**, не подмодуль memory/emotional.

---

## Decision

### 1. Defense zone в карте 0061

| Zone | Intelligence | Core | Sandbox | Клиенты |
|------|--------------|------|---------|---------|
| **defense** | психологическая защита / survival gate | trauma_edges, repression/confab counters, honesty | `agent-defense-sandbox` — rechannel experiments | **emotional** (limbic), **memory** (hot recall), **character** (dent), bind/tract |

**Не дублирует:**

- **emotional** — владеет limbic axes; defense **читает**, не пишет axes (кроме sandbox promote).
- **memory** — владеет journal/hippo; defense **маркирует** meta.defense, фильтрует hot.
- **character** — владеет temperament EMA; defense **шлёт** dent/rechannel через wire.

**Владеет:** `intelligence_zones.defense.core` (бывший `state.defense`).

### 2. Wire

```text
intelligence_zones.defense/
├── core              trauma_edges, repression_*, confab_*, honesty_last
├── sandbox           rechannel experiments (promote → core edge strength)
├── core_lattice_id   agent-defense-core
└── sandbox_lattice_id agent-defense-sandbox

casa/prisms/defense/  orchestration prisms (gate, cement, infer) — как casa/prisms/affect/
casa/prisms/intelligence/defense_zone.py  spawn / ensure / migrate
```

**Tick order (фрагмент):**

```text
emotional.update (limbic)
→ infer_life_event (incl. security_threat, caregiver_violation)
→ defense.after_life_event (0074/0075)
→ bind → defense.apply_* (tract + block deltas)
```

### 3. Life events (infer P20a)

| Event | Cue (v0) | Affect delta |
|-------|----------|--------------|
| `security_threat` | violence / asphyxia / lethal threat lexicon | security↓↓, arousal↑, valence↓ |
| `caregiver_violation` | caregiver token + violence token | security↓↓↓, arousal↑, valence↓↓ |

Infer: `casa/prisms/defense/infer.py` — **не** operator flag.

### 4. Sandbox rechannel promote (P20b)

Агент пробует **rechannel** (threat cue → proxy tract) в sandbox, не трогая core:

```text
sublimation DEFER → sandbox_record_rechannel (draft, score≈0.12)
deliberate_practice / bump → sandbox_bump_rechannel_score
score ≥ promote_theta → promote_rechannel_experiment → trauma_edges core
```

| API | Role |
|-----|------|
| `sandbox_record_rechannel` | draft experiment |
| `sandbox_bump_rechannel_score` | practice nudge |
| `promote_rechannel_experiment` | sandbox → core via `promote_rechannel_to_core` |
| `try_auto_promote_rechannel_experiments` | @ intelligence tick |

**Не operator:** promote только при `score ≥ zone_policy.promote_theta` (default 0.65).

### 5. Sandbox lattices (P20c — ADR-0014 parity)

Агент **спавнит и крутит** призмы только в sandbox, как affect/WM:

```text
spawn_defense_scratch_lattice(topic)  → agent-defense-sandbox | agent-defense-lab-{topic}
place_defense_node / place_defense_rechannel_edge  → threat→proxy на lab lattice
sublimation DEFER → spawn + edge + experiment(lattice_id)
promote → требует lattice evidence если lattice_id задан
prune_defense_scratch_lattices  → TTL lab lattices @ tick
```

| API | Role |
|-----|------|
| `spawn_defense_scratch_lattice` | agent-owned scratch (cap `max_sandbox_lattices`) |
| `place_defense_rechannel_edge` | threat node → proxy node |
| `list_defense_sandbox_state` | REPL / honesty snapshot |

**Core** (`agent-defense-core`) — только promote ceremony; **не** произвольный place.

### 6. Bootstrap & migrate

- `agent-bootstrap-manifest.v1.json` → `defense_zone` @ `spawn_on_bootstrap: true`
- `migrate_intelligence_zones` — idempotent `state.defense` → `intelligence_zones.defense.core`
- `zone_proportions.defense` in genome (default 0.75)

### 7. Anti-patterns

| ❌ | ✅ |
|----|-----|
| Всё в emotional «потому что limbic» | emotional = axes; defense = gates + cement |
| Всё в memory «потому что journal» | memory = store; defense = accessibility split |
| Плоский state.defense без zone | migrate → intelligence_zones.defense |

---

## Links

- [CASA-ADR-0077-boundary-compose-encapsulation.md](CASA-ADR-0077-boundary-compose-encapsulation.md)
- [CASA-ADR-0074-psychological-defenses.md](CASA-ADR-0074-psychological-defenses.md)
- [CASA-ADR-0061-intelligence-zones.md](CASA-ADR-0061-intelligence-zones.md)
- [CASA-ADR-0075-trauma-cement-survival.md](CASA-ADR-0075-trauma-cement-survival.md)
