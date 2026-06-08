# ADR-0067: Zone → Prism → Lattice wire migration

**Status:** accepted (design); **ownership model superseded by ADR-0068** (Memory Zone)  
**Date:** 2026-06-07  
**Related:** ADR-0068 (Memory Zone — primary owner of LTM/hippo), ADR-0061 (Intelligence Zones), ADR-0059 (innate organ basis), ADR-0010 (control stack), ADR-0019 (multi-prism CU), ADR-0060–0066 (zone instances), [control-lattice-stack.md](control-lattice-stack.md), [prisms/memory/stack.json](prisms/memory/stack.json), [zone-prism-map.v1.json](zone-prism-map.v1.json), [agent-bootstrap-manifest.v1.json](agent-bootstrap-manifest.v1.json)

---

## Context

**ADR-0061 `migrate_intelligence_zones`** сделал **organ map + state**: `intelligence_zones.*`, spawn agent-owned scratch (`agent-*-core/sandbox`), emotional wire, neuromodulator — **без** перепривязки content field.

Сейчас hot path часто видит **единый пул** `memory_lattices(state)` + общий bind/DAN spotlight. Math tract, spatial (когда будет), discourse и lexicon **конкурируют за один read budget**, хотя NCA-substrate у них уже **разный** (отдельные `lattice_id`, shards, `model.pt`).

**ADR-0068** уточняет: **Memory Zone** владеет `prism_memory` + `prism_hippo`; linguistic/logical/spatial — **domain clients** (`domain_scope`), не owners LTM. Этот ADR описывает **migrate + routing** поверх той модели.

### Каноническая иерархия

```text
Zone (memory | linguistic | logical | executive | …)
├── [memory only] explicit / implicit subsystems     ← ADR-0068
├── Prism A                ← wire-блок (prism_memory, prism_hippo, wm_prism, …)
│   ├── lattice_id₁
│   ├── lattice_id₂
│   └── bridges
├── zone_state             ← scalar core (axes, ATP, …)
└── cross_zone_links       ← executive bridges; domain clients → memory scopes
```

| Уровень | Что это | Пример |
|---------|---------|--------|
| **Zone** | контур (memory **или** intelligence) | `memory`, `linguistic`, `logical` |
| **Prism** | CU в wire | `prism_memory`, `prism_hippo`, `prism_control` |
| **Lattice** | одна решётка | `lexicon-ru-03`, `schema-math`, `H1_surface` |

**Invariant:** миграция = **ownership tags + read scopes** по цепочке zone → prism → lattice set. Не «одна zone → один lattice».

---

## Problem

| Симптом | Причина |
|---------|---------|
| Math и discourse «мешаются» в bind | router не знает memory `domain_scope` |
| Spatial будет биться с lexicon | нет `domain=vis` scope |
| Hippo / LTM «ни чья» | нет Memory Zone owner |
| `migrate_intelligence_zones` не трогал LTM | by design (0061 §3) |

**Цель:** domain representations **не конкурируют** за один bind pool; зоны **связаны** через executive bridges, не через shared substrate по умолчанию.

---

## Decision

### 1. Ownership (0068)

| Owner zone | Prisms | Role |
|------------|--------|------|
| **memory** | `prism_memory`, `prism_hippo`, `wm_prism` (STM) | LTM + episodic + consolidate |
| **executive** | `prism_control`, `intent_prism` (implicit procedural) | orchestrate + control lattices |
| **linguistic** | `linguistic_zone` agent scratch only | **client** `domain=lang` |
| **logical** | `logical_zone` agent scratch only | **client** `domain=math` |
| **emotional** | limbic agent lattices | episodic **tags**, not hippo owner |

Полная карта explicit/implicit: **ADR-0068**.

### 2. Domain scopes (intelligence clients)

| Client zone | Memory access | Tracts |
|-------------|---------------|--------|
| linguistic | `explicit.semantic: lang` + implicit priming | social, discuss, grammar, … |
| logical | `explicit.semantic: math` + implicit procedural | math, query |
| spatial | `explicit.semantic: vis` (planned) | — |
| executive | union(domains) + `explicit.episodic` | * (bounded) |
| social | lang + episodic read | social, discuss |

### 3. Machine-readable map — `zone-prism-map.v1.json` (schema v2)

Канон: [zone-prism-map.v1.json](zone-prism-map.v1.json) — блоки `memory_zone` + `intelligence_zones` + `cross_zone_bridges`.

```text
memory_zone.owner_prisms → all LTM/hippo lattices tagged owner_zone=memory
memory_zone.explicit.semantic.domains.lang → lattice_patterns for linguistic client
memory_zone.explicit.semantic.domains.math → lattice_ids for logical client
intelligence_zones.linguistic.memory_access → client contract only
```

### 4. Read routing (target hot path)

```text
tract + intent
  → memory_resolve_scopes(tract, active_intelligence_zone)
  → owner=memory: expand domains + explicit|implicit kind
  → bind / semantic_read ONLY within scoped lattices
  → executive cross_zone_bridge? → second pass (bounded)
```

| Tract | Primary client | Memory scope |
|-------|----------------|--------------|
| `math` | logical | `explicit.semantic: math` |
| `social`, `discuss`, … | linguistic | `explicit.semantic: lang` |
| `recall` | executive | `explicit.episodic` + lang |
| spatial (future) | spatial | `explicit.semantic: vis` |

### 5. Cross-zone связность

| Связь | Механизм |
|-------|----------|
| Math → words | bridge `logical_verbalize_lang`; two memory scopes, one compose |
| DMN digest | executive → `domain=lang` |
| Repair | social/episodic read; emotional tag only |
| Deictic spatial | spatial + linguistic via WM hints (planned) |

**Anti-pattern:** default scan all 145 lattices.

### 6. Migration tool — `migrate_zone_prism_wire`

```bash
python -m casa.prisms.intelligence.migrate_zone_prism_wire \
  --store-dir agents/von-neumann \
  --map design/zone-prism-map.v1.json \
  --dry-run
```

**Steps (idempotent):**

1. Load field_state, agent prism, pack.manifest.
2. Tag every lattice: `owner_zone=memory` (LTM/hippo) or owning intelligence zone (agent scratch, control).
3. Tag semantic lattices with `domain` (`lang`, `math`, `vis`).
4. Write `state.meta.zone_prism_map_version` (≥2), `ltm/meta/zone_prism_map.json`.
5. Update router: tract → client zone → memory scope.
6. Report: untagged, domain conflicts, counts per domain.

**No wipe** — 0061 §3 preserved.

### 7. Rollout

| Phase | Action |
|-------|--------|
| **P11a** | zone-prism-map v2 + dry-run (0067 + 0068) |
| **P12a** | Memory zone state + spawn catalog lattices (0068) |
| **P12b** | `memory_resolve_scopes` in bind hot path |
| **P12c** | MEMORY.md grouping by explicit/implicit/domain |
| **P12d** | Implicit priming decay + procedural gains |
| **P12e** | Consolidate under `memory.consolidate` |

### 8. Acceptance probes

| Probe | Pass |
|-------|------|
| All LTM/hippo lattices | `owner_zone=memory` |
| math query | bind ⊆ `domain=math` |
| discuss query | bind ⊆ `domain=lang` |
| hippo lattice | `explicit.episodic`, not linguistic owner |
| idempotent re-run | 0 tag changes |

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| Linguistic owns `prism_memory` | Memory zone owns; linguistic = client |
| Zone = one lattice | Zone = prisms × many lattices |
| Implicit global bind | Scoped read + bridges |
| Emotional owns hippo | Memory explicit episodic |
| Wipe for topology | Additive migrate |

---

## Consequences

- **0068** = ownership; **0067** = migrate tool + routing contract.
- `MEMORY.md` groups: Memory → Explicit/Implicit → domain → prism → lattice.
- Lexicon **content** unchanged; tags + router only.

## Links

- [CASA-ADR-0068-memory-zone.md](CASA-ADR-0068-memory-zone.md)
- [CASA-ADR-0061-intelligence-zones.md](CASA-ADR-0061-intelligence-zones.md)
- [CASA-ADR-0059-innate-organ-basis.md](CASA-ADR-0059-innate-organ-basis.md)
- [multi-cylinder-memory.md](multi-cylinder-memory.md)
- [zone-prism-map.v1.json](zone-prism-map.v1.json)
