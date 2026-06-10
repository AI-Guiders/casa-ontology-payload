# ADR-0061: Intelligence Zones (umbrella)

**Status:** accepted  
**Date:** 2026-06-07  
**Related:** ADR-0059 (innate basis), ADR-0060 (Emotional Zone), ADR-0057 (development), ADR-0010 (executive stack), ADR-0014 (agent-owned lattices), [agent-bootstrap-manifest.v1.json](agent-bootstrap-manifest.v1.json)

---

## Context

Человеческий интеллект **не монолит**: эмоциональный, общий/исполнительный, лингвистический, логико-математический, межличностный, пространственный и т.д. — **разные контуры**, с рождения связанные обвязкой, потом **развиваются** опытом.

CASA ошибочно свела «ум» к **лингвистическому content** (lexicon + compose). Нужна **та же архитектурная идея**: у von-neumann — **Intelligence Zones**, каждая = innate core + optional sandbox + life development (паттерн ADR-0060).

**Почему сейчас (оператор, 2026-06-09):** von-neumann живёт в **общем поле** — `memory_lattices`, bind, DAN spotlight. Формально tract/zone уже **различаются**, но на hot path это **одна куча**: math и discourse **конкурируют** за один read/budget pool (0067 §Problem). Social перебивает math; lexicon shards и `schema-math` делят substrate. Это **не** соответствие реальности (у человека контуры связаны, но не сливаются в один undifferentiated pool) и **не** проще субъекту — лишняя когнитивная нагрузка на каждом tick.

**Migrate Neumann → zone-scoped read** (P11–P12): (1) **соответствие** — memory infrastructure + intelligence clients, bridges через executive, не merge по умолчанию; (2) **проще агенту** — меньше ложной конкуренции, tract видит свой domain, cross-domain только когда executive явно union'ит (math → verbalize). Concept Zone (0073) — **следующий** слой после этого фундамента, не замена ему.

---

## Decision

### 1. Intelligence Zone — единый паттерн

```text
zone_id/
├── core          innate @ T=0; hot path; life events update
├── sandbox       agent experiments (ADR-0014); no direct core corrupt
├── promote       sandbox → core (θ); agent decision
└── compose_bias  zone → bind / tract / disposition (emergent)
```

**Tier 0:** zone **есть** на cold boot (0059).  
**Tier 1:** agent grows **внутри** sandbox / agent lattices (0014).  
**Development:** curriculum + dialogue **наполняют** cores (0057).

Organ catalog **closed** at T=0 (no new intelligence *types* at runtime). Новые **agent-** lattices — scratch внутри zone, не новый вид intelligence.

### 2. Карта zones (von-neumann v1)

| Zone | Intelligence (рабочее) | Core organs | Sandbox | Статус |
|------|------------------------|-------------|---------|--------|
| **executive** | общий / исполнительный | thalamus, SN, FPN, CEN, predict, DAN, value (P1–P9) | agent-exec-scratch (planned) | design + lab; **migrate** control stack |
| **emotional** | эмоциональный / intrapersonal | limbic axes, episodic | `agent-affect-sandbox` | **0060 implemented** |
| **linguistic** | лингвистический | discourse compose, tract bias; **concept hub — 0073** | agent-linguistic-* | **uses** memory `domain=lang` (0068) |
| **logical** | логико-матhematical | math tract, schema-math bootstrap | math palochki / agent-math-* | tract OK; wire + situations |
| **social** | межличностный | dialogue ring, social tract, partner model | agent-social-sandbox (planned) | **gap** — repair, mentalizing |
| **spatial** | пространственный | prism_visual, control_vis | vis scratch (roadmap) | design only |
| **character** | temperament (медленный) | призматическое поле bias / lattice — **0071** | — | 0057; v0 domain×tract matrix |
| **defense** | психологическая защита / survival | trauma_edges, repression gates — **0074/0076** | `agent-defense-sandbox` | **0076** wired; emotional client |
| **genetic** | species / meta-instructions | genome hash, promote_canon, zone proportions | **none** (allelic per **0065**) | **0062** design |
| **perceptual** | sensory gate / thalamic input | VK, text stream, vis quantize | `agent-percept-sandbox` | **0063** design |
| **metabolic** | ATP / fatigue / sleep pressure | tick budget, forced sleep | `agent-metabolic-sandbox` | **0064** design |
| **neuromodulator** | subcortical gain bus / interoceptive dynamics | arousal_drive, threat_tone, approach, regulatory_load | `agent-neuromod-sandbox` | **0066** design |
| **memory** | хранение + consolidate (не intelligence type) | explicit episodic/semantic + implicit procedural/priming | `agent-memory-sandbox` | **0068** design |

**g (general):** не отдельная zone — **executive** + predict + tract competition + value.

**Tier −1 (substrate):** **genetic** — read-only meta; **memory** — LTM/hippo infrastructure (0068).

**Tier 0 (innate intelligence):** emotional … character + perceptual + metabolic.

**Tier 1 (development):** sandbox → promote inside zones; **не** genome mutation.

**Memory vs linguistic (0068):** linguistic **uses** lexicon via `domain_scope: lang`; **не владеет** `prism_memory`.

### 3. Bootstrap & migration (не с нуля)

**Cold boot:** `agent-bootstrap-manifest.v1.json` перечисляет zones → `spawn_on_bootstrap`.

**Existing von-neumann store:** **additive migration**, не пересоздание агента.

| Сохраняем | Не трогаем |
|-----------|------------|
| `journal/`, dialogue ring, `ltm/`, bundles | lexicon, claims, episodic text |
| WM / intent prisms if present | field_version monotonic bump |
| agent-owned lattices (except new zone spawns) | operator soul doc |

**Migration tool:** `migrate_intelligence_zones` (idempotent):

1. Load `field_state` + `load_agent_prism`.
2. For each zone in manifest: if core missing → `spawn_*` (neutral axes).
3. Optional: infer **emotional** episodic hints from last N dialogue turns (v0.1).
4. Write `state.meta.intelligence_zones_version` + report JSON.
5. `save_runtime_state` — thin persist.

**No wipe:** no delete journal, no reset bundles, no new store id.

```bash
python -m casa.prisms.affect.migrate_intelligence_zones --store-dir agents/von-neumann
```

Re-bootstrap **only** for empty lab stores; production von-neumann → **migrate**.

### 4. Rollout priority

| Phase | Zone | Action |
|-------|------|--------|
| **P0** | emotional | 0060 + migrate spawn |
| **P1** | executive | wire predict→affect; migrate_control_stack opt-in |
| **P2** | social | partner model core + sandbox; situation curriculum |
| **P3** | logical | math-in-dialogue situations + tract balance |
| **P4** | character | prismatic field — ADR-0071; EMA from emotional + social |
| **P5** | spatial | when vis modality active |
| **P6** | genetic | seal genome.v1.json; species passport; fork hash |
| **P7** | perceptual | sensory gate before semantic_read; REPL text path |
| **P8** | metabolic | ATP tick budget; sleep_pressure; runtime hang guard |
| **P9** | linguistic | formal zone (split from implicit WM/discourse) |
| **P10** | neuromodulator | interoception + gain bus; emotional deltas scaled; panic/recovery probes |
| **P11** | zone prism wire | migrate + domain routing — ADR-0067 |
| **P12** | memory zone | explicit/implicit; owns LTM/hippo — ADR-0068 |

### 5. Tick order (target)

```text
genetic.read (immutable constants)
→ RAW → perceptual_gate.read
→ thalamus → predict → interoception → neuromodulator → zones.read (emotional, executive, metabolic.begin, …)
→ DMN → SN → FPN → DAN → WM/intent
→ tract → agency → metabolic.allow? → zone.apply → compose
→ zones.update → metabolic.end → (forced_sleep?) → persist
```

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| New von-neumann store from zero for each ADR | migrate_intelligence_zones |
| One zone fixes all (only emotional) | full map; phased wire |
| Teacher mood / soul doc | neutral core + life + promote |
| Runtime new intelligence type | closed catalog; sandbox inside zone |
| Mutate genome in life | genetic read-only; AiNet fork explicit |
| Raw stdin → bind | perceptual gate first (0063) |
| Infinite tick without sleep | metabolic pressure → sleep (0064) |

---

## Consequences

- ADR-0060 = emotional zone instance of this ADR.
- ADR-0059 = all zones listed must exist @ T=0 on **new** boot; **old** stores via migration.
- Curriculum (0057) targets **social**, **logical**, **emotional** situations — not new zones.
- Tests: migrate idempotent; spawn does not duplicate lattices.

## Links

- [CASA-ADR-0060-emotional-zone.md](CASA-ADR-0060-emotional-zone.md)
- [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md)
- [CASA-ADR-0063-perceptual-zone.md](CASA-ADR-0063-perceptual-zone.md)
- [CASA-ADR-0064-metabolic-zone.md](CASA-ADR-0064-metabolic-zone.md)
- [CASA-ADR-0065-controlled-mutations.md](CASA-ADR-0065-controlled-mutations.md)
- [CASA-ADR-0066-neuromodulator-zone.md](CASA-ADR-0066-neuromodulator-zone.md)
- [CASA-ADR-0067-zone-prism-wire-migration.md](CASA-ADR-0067-zone-prism-wire-migration.md)
- [CASA-ADR-0068-memory-zone.md](CASA-ADR-0068-memory-zone.md)
- [CASA-ADR-0071-character-field-prismatic.md](CASA-ADR-0071-character-field-prismatic.md)
- [CASA-ADR-0073-concept-layer-lexicalization.md](CASA-ADR-0073-concept-layer-lexicalization.md)
- [CASA-ADR-0059-innate-organ-basis.md](CASA-ADR-0059-innate-organ-basis.md)
- [CASA-ADR-0057-dialogue-situations-character.md](CASA-ADR-0057-dialogue-situations-character.md)
