# ADR-0068: Memory Zone (Explicit / Implicit / Immutable)

**Status:** accepted (design); immutable kind in **ADR-0069** (postulates, promote, theory fork)  
**Date:** 2026-06-07  
**Related:** ADR-0069 (Immutable memory kind — canon lattices), ADR-0070 (Forgetting policies), ADR-0061 (Intelligence Zones), ADR-0067 (zone prism wire), ADR-0059 (innate basis), ADR-0010 (control stack), [multi-cylinder-memory.md](multi-cylinder-memory.md), [hippo-lattice-stack.md](hippo-lattice-stack.md), [prisms/memory/stack.json](prisms/memory/stack.json), [zone-prism-map.v1.json](zone-prism-map.v1.json), [agent-bootstrap-manifest.v1.json](agent-bootstrap-manifest.v1.json)

---

## Context

**ADR-0061** ввёл **Intelligence Zones** — контуры мышления (linguistic, logical, spatial, emotional, …).  
**ADR-0067** начал маршрутизацию **zone → prism → lattice**, но ошибочно записал `prism_memory` **владельцем** linguistic/logical.

Это смешивает две **ортогональные** оси:

| Ось | Вопрос | Пример |
|-----|--------|--------|
| **Intelligence zone** | *какой домен мышления?* | linguistic, logical, spatial |
| **Memory zone** | *как хранится и достаётся знание?* | explicit / implicit / **immutable** (0069) |

У человека **гиппокамп + кора** — не «лимбическая зона» и не «языковая зона»; это **система памяти**, которой пользуются все intelligence zones.  
Lexicon и math schemas живут в **одной инфраструктуре LTM**, но **разные domain scopes** при read — не конкуренция за одни клетки по умолчанию.

**Invariant (0068):** `prism_memory`, `prism_hippo`, sleep consolidate, WM STM — **Memory Zone**. Linguistic / logical / spatial — **клиенты** с `domain_scope`, не owners LTM.

---

## Decision

### 1. Memory Zone в карте 0061

| Property | Value |
|----------|-------|
| Zone id | `memory` |
| Role | storage + consolidation + read routing substrate |
| Tier | **Infrastructure** (как genetic/metabolic по «не intelligence type», но **hot path** на каждом tick) |
| Not duplicate | emotional episodic **tags**; linguistic **compose**; executive **orchestration** |

```text
intelligence_zones
├── memory                    ← 0068 + 0069
│   ├── explicit              episodic + mutable semantic (life writes)
│   ├── implicit              procedural + priming
│   └── immutable             adopted postulates (bootstrap + earned @ promote)
├── linguistic                ← domain client (lang scope)
├── logical                   ← domain client (math scope)
├── executive                 ← cross-subsystem orchestrator
└── …
```

### 2. Три memory kind (Explicit / Implicit / Immutable)

| Kind | Subkind / role | Что | Von-neumann today | Verbalize? |
|------|----------------|-----|-------------------|------------|
| **explicit** | episodic | события, turns, journal | hippo, dialogue | да |
| **explicit** | semantic (mutable) | lexicon/phrase drift, WM | lexicon-*, phrases-*, agent-wm-* | да |
| **implicit** | procedural | NCA, intent priors | `model.pt`, intent_prism | опционально |
| **implicit** | priming | bind/WM decay | edge scores | нет |
| **immutable** | postulates / conventions | принятые посылки; hot read-only; **promote** adds | alphabet-* @ bootstrap; earned TBD | да (read) |

**Sleep:** hippo → **explicit** semantic (mutable only); затем **три скорости забывания** (priming @ tick, episodic fade @ metabolic, NCA erosion @ sleep) — [CASA-ADR-0070-forgetting-policies.md](CASA-ADR-0070-forgetting-policies.md). **Immutable** — принятые postulates: bootstrap @ T=0, earned @ `promote_canon`, theory fork — [CASA-ADR-0069-immutable-memory-kind.md](CASA-ADR-0069-immutable-memory-kind.md).

### 3. Prisms → Memory Zone (ownership)

**Memory Zone владеет** (primary owner):

| Prism / organ | Memory kind | Subkind |
|---------------|-------------|---------|
| `prism_memory` | explicit | Semantic (mutable LTM shards) |
| `prism_memory` (subset) | **immutable** | Postulate lattices — [0069](CASA-ADR-0069-immutable-memory-kind.md); agent spawn via promote only |
| `prism_hippo` | explicit | Episodic |
| `wm_prism` | explicit | Semantic STM (+ scratch lattices) |
| Dialogue ring (`store/dialogue/`) | explicit | Episodic (text wire, not NCA) |
| `journal/` Self tier | explicit | Episodic / semantic notes |
| `intent_prism` | implicit | Procedural (tract priors) |
| `nca_train_registry`, shard `model.pt` | implicit | Procedural |
| Bind activation / WM edge decay | implicit | Priming |
| Sleep replay queue | — | Consolidate scheduler (both paths) |

**Не Memory Zone** (остаются intelligence / substrate):

| Zone | Holds | Uses memory via |
|------|-------|-----------------|
| linguistic | discourse bias, `linguistic_zone` agent scratch | `domain_scope: lang.*` |
| logical | math tract, `logical_zone` scratch | `domain_scope: math.*` |
| spatial | vis layout (roadmap) | `domain_scope: vis.*` |
| emotional | limbic axes; **episodic flags** | tags on explicit episodic, not hippo owner |
| executive | control prisms | orchestrate read unions + bridges |
| social | partner model | episodic read + social state |

### 4. Domain scopes (intelligence → memory)

Intelligence zones **не владеют** `prism_memory`. Они запрашивают **subset**:

```text
memory_zone.read(
  kind=explicit,
  subkind=semantic,
  domain=lang,           # linguistic client
  tract=social,
)
→ lattice_ids: lexicon-*, phrases-*, morph-*, …

memory_zone.read(
  kind=explicit,
  subkind=semantic,
  domain=math,           # logical client
  tract=math,
)
→ lattice_ids: schema-math, compose-math, …
```

| Domain id | Client zone | Semantic lattice patterns | Implicit hooks |
|-----------|-------------|----------------------------|----------------|
| `lang` | linguistic | `alphabet-*`, `syllables-*`, `lexicon-*`, `phrases-*`, `morph-*` | discourse tract EMA |
| `math` | logical | `schema-math`, `compose-math`, `math-*`, `logic-*` | schema-math NCA |
| `vis` | spatial | `vis-*`, `layout-*`, `scene-*` (planned) | vis quantize habit |
| `control` | executive | `control-*` lattices | predict/DAN procedural |
| `episodic` | executive, social, recall tract | hippo H*, dialogue | — |

**Cross-domain bridge** (0067): math result → verbalize via `lang` scope — **два read**, один compose; не merge lattices.

#### 4.1 Immutable — singleton @ Memory; intelligence = client only

**Decision:** одна **`memory.immutable`** на агента — не `linguistic.immutable`, не `logical.immutable`.

| | Memory Zone | Intelligence zone |
|---|-------------|-------------------|
| **Owns** postulate lattices | ✅ | ❌ |
| **Reads** subset by domain + active theory | ✅ (router) | ✅ (`immutable_read_scope`) |
| **Promote ceremony lands** | ✅ `memory.immutable` + metadata | initiator only (logical, linguistic, operator) |

**Партиции внутри singleton** (логические «полки», не отдельные intelligence zones):

```text
memory.immutable
├── domains.lang
│   └── theories[]     lang-ru-orthography-v1 → alphabet-*, syllables-ru
│                      lang-ru-morph-v1       → morph-role-*
├── domains.math
│   └── theories[]     (earned @ promote)
└── domains.vis
    └── theories[]     (roadmap)
```

Intelligence zones держат **указатель на scope**, не vault:

```text
intelligence_zones.linguistic
  immutable_read_scope: { domain: lang, theory_ref: active }

intelligence_zones.logical
  immutable_read_scope: { domain: math, theory_ref: active }
```

**Executive** на cross-domain tick: **union read** `lang` immutable + `math` immutable + explicit pools — без merge lattices.

**Invariant:** promote_canon всегда append в **единый** `memory.immutable` catalog с `domain` + `theory_id`; theory fork = новая ветка в том же store, не новая intelligence zone.

Подробнее epistemic model + earned path: [CASA-ADR-0069-immutable-memory-kind.md](CASA-ADR-0069-immutable-memory-kind.md) §8–9.

### 5. State block (v0)

```text
prism_agent
└── intelligence_zones
    └── memory
        ├── explicit
        │   ├── episodic
        │   │   ├── hippo_lattice_ids[]
        │   │   ├── dialogue_ring_ref
        │   │   └── journal_domains[]
        │   └── semantic
        │       ├── ltm_root_ref
        │       ├── active_shards { l2, l3 }
        │       └── wm_prism_ref
        ├── implicit
        │   ├── procedural
        │   │   ├── nca_registry_ref
        │   │   └── intent_prism_ref
        │   └── priming
        │       ├── bind_decay_halflife_ticks
        │       └── last_activation_tick
        ├── immutable                    ← singleton; domain partitions inside
        │   ├── lattice_ids[]
        │   ├── lattice_patterns[]
        │   ├── write_gate_ref          genetic.promote_canon
        │   ├── domains { lang, math, vis, … }
        │   └── theories[]              theory_id, domain, active, postulate_lattice_ids[]
        ├── consolidate
        │   ├── last_sleep_at_tick
        │   ├── replay_queue_depth
        │   └── merge_policy_ref
        ├── core_lattice_id          agent-memory-core (catalog)
        └── sandbox_lattice_id       agent-memory-sandbox
```

**T=0:** explicit semantic = bootstrapped LTM empty OK; episodic = empty ring; implicit = neutral priors.  
**Namespace:** `agent.memory.explicit.*`, `agent.memory.implicit.*`, sandbox `agent.memory.lab.*`.

### 6. Tick order (memory hooks)

```text
… perceptual → executive predict …
→ memory.priming_decay()                    # implicit short-lived
→ memory.explicit.episodic.touch?           # wake write hippo on surprise
→ intelligence zones (emotional, …) apply
→ tract → memory.resolve_scopes(tract)      # domain → lattice set
→ bind / semantic_read WITHIN scopes
→ memory.write_gate(lattice)?            # block hot write to immutable
→ compose
→ memory.explicit.episodic.append?          # partner/subject turn
→ … metabolic.end …
→ (sleep?) memory.consolidate()             # hippo → LTM + procedural strengthen
→ (sleep?) memory.forget()                  # trim episodic, decay semantic — 0070
→ (ceremony?) promote_canon()               # explicit/sandbox → immutable postulate
```

REPL **минимум P12b:** `memory.resolve_scopes` before bind; math tract ≠ phrase shards by default.

### 7. Bootstrap manifest (planned → enable with P12a)

```json
"memory_zone": {
  "enabled": true,
  "adr": "0068",
  "spawn_on_bootstrap": true,
  "core_lattice_id": "agent-memory-core",
  "sandbox_lattice_id": "agent-memory-sandbox",
  "concept_prefix_core": "agent.memory.",
  "concept_prefix_sandbox": "agent.memory.lab.",
  "explicit": {
    "episodic": { "hippo_prism": "prism_hippo", "dialogue": true, "journal": true },
    "semantic": { "ltm_prism": "prism_memory", "wm_prism": "wm_prism" }
  },
  "implicit": {
    "procedural": { "intent_prism": "intent_prism", "nca_registry": true },
    "priming": { "decay_halflife_ticks": 6 }
  },
  "immutable": {
    "lattice_patterns": ["alphabet-*", "syllables-ru", "morph-role-*"],
    "lattice_ids": [],
    "write_gate": "genetic.promote_canon",
    "note": "Hot path read-only; new postulates via promote_canon; theory fork not overwrite"
  },
  "note": "Owns prism_memory + prism_hippo; intelligence zones use domain_scope"
}
```

### 8. API (target: `casa/prisms/memory/zone.py`)

| Function | Role |
|----------|------|
| `ensure_memory_zone` | wire under `intelligence_zones.memory` |
| `spawn_memory_zone` | catalog lattices + index refs |
| `memory_resolve_scopes` | tract + client zone → `{explicit\|implicit\|immutable}` lattice sets + `active_theory_id` |
| `memory_explicit_read` | semantic/episodic bounded read |
| `memory_implicit_gains` | procedural + priming scales for tract/bind |
| `memory_consolidate_snapshot` | sleep report hook |
| `memory_zone_snapshot` | provenance / MEMORY.md grouping |
| `memory_write_allowed` | memory_kind + genetic promote_canon gate |
| `memory_kind_for_lattice` | tag lookup (P11 index) |

### 9. Relation to ADR-0067

| 0067 v1 (superseded) | 0068 + 0067 v2 |
|----------------------|----------------|
| linguistic **owns** `prism_memory` lang subset | **memory** owns; linguistic has `domain_scope: lang` |
| logical **owns** math lattices | **memory** owns; logical has `domain_scope: math` |
| `shared_prisms.prism_hippo` | hippo under **memory.explicit.episodic** |
| `zone_id` on lattice | `memory_zone_id` + optional `domain_tag` |

**Migrate tool** (0067): `owner_zone=memory` for all LTM/hippo lattices; `domain_scopes` table for clients.

### 10. Rollout

| Phase | Action |
|-------|--------|
| **P12a** | ADR-0068 + `zone-prism-map` v2 + manifest block |
| **P12b** | `memory_resolve_scopes`; bind scope math vs lang |
| **P12c** | `MEMORY.md` groups: Memory → Explicit/Implicit → domain |
| **P12d** | Priming decay + implicit gains on tract |
| **P12e** | Consolidate report under `memory.consolidate` |
| **P12f** | Probes: recall = explicit episodic; math habit = implicit without new lemma |

| **P12g** | Sleep merge skip immutable; promote_canon → earned postulates |
| **P12h** | Theory fork metadata; active_theory_id in resolve |
| **P15** | Forgetting policies — ADR-0070; post-sleep trim/decay |

### 11. Tests (acceptance)

| Probe | Pass |
|-------|------|
| Every LTM/hippo lattice | `owner_zone=memory` |
| Math bind | candidates ⊆ `domain=math`; no `phrases-*` |
| Discuss bind | candidates ⊆ `domain=lang`; no `schema-math` |
| Dialogue turn | lands explicit episodic; emotional gets tag only |
| Post sleep | hippo pending ↓; semantic field_version ↑; NCA registry unchanged path |
| Intent prior after 20 social turns | implicit procedural shifts; no new L3 token required |
| Sleep merge | no write to `morph-role-ru` without promote gate |
| Hot path field_write | immutable lattice → rejected or rerouted to sandbox |

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| Linguistic zone owns LTM | Memory zone owns; linguistic = domain client |
| One lattice = memory zone | Memory = many prisms × many lattices |
| Implicit = «не помню» narrative only | NCA / priors / priming as first-class |
| Emotional zone owns hippo | Emotional tags on explicit episodic |
| Merge episodic text into lexicon shard | Sleep merge via consolidate policy |
| Explicit/Implicit = same bind pool | Separate resolve paths; bridge explicit→compose |
| Genetic immutable = весь LTM | Genetic = rules; memory immutable = canon subset |
| Immutable = truth / only @ bootstrap | Postulates bootstrap or earned; not ultimate truth |
| Per-intelligence immutable vault | Singleton `memory.immutable`; domain × theory partitions |
| `linguistic.immutable` owner | `linguistic.immutable_read_scope` → filter on memory catalog |
| Immutable lexicon 50k shards | Postulate tier narrow; lexicon explicit mutable |
| Overwrite postulate on theory change | Theory fork + new immutable branch |

---

## Consequences

- Закрывает архитектурный зазор: **как думать** (intelligence) vs **где лежит** (memory).
- ADR-0067 и `zone-prism-map` **обновляются** под memory ownership + domain scopes.
- ADR-0061 linguistic row «memory prisms» → **uses** memory zone, не owns.
- `multi-cylinder-memory` и `hippo-lattice-stack` становятся **доками внутри Memory Zone**, не orphan design.

## Links

- [CASA-ADR-0061-intelligence-zones.md](CASA-ADR-0061-intelligence-zones.md)
- [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md)
- [CASA-ADR-0065-controlled-mutations.md](CASA-ADR-0065-controlled-mutations.md)
- [CASA-ADR-0067-zone-prism-wire-migration.md](CASA-ADR-0067-zone-prism-wire-migration.md)
- [CASA-ADR-0069-immutable-memory-kind.md](CASA-ADR-0069-immutable-memory-kind.md)
- [CASA-ADR-0070-forgetting-policies.md](CASA-ADR-0070-forgetting-policies.md)
- [multi-cylinder-memory.md](multi-cylinder-memory.md)
- [hippo-lattice-stack.md](hippo-lattice-stack.md)
- [zone-prism-map.v1.json](zone-prism-map.v1.json)
