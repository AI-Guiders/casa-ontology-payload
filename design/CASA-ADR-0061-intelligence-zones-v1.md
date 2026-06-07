# ADR-0061: Intelligence Zones (umbrella)

**Status:** accepted  
**Date:** 2026-06-07  
**Related:** ADR-0059 (innate basis), ADR-0060 (Emotional Zone), ADR-0057 (development), ADR-0010 (executive stack), ADR-0014 (agent-owned lattices), [agent-bootstrap-manifest.v1.json](agent-bootstrap-manifest.v1.json)

---

## Context

Человеческий интеллект **не монолит**: эмоциональный, общий/исполнительный, лингвистический, логико-математический, межличностный, пространственный и т.д. — **разные контуры**, с рождения связанные обвязкой, потом **развиваются** опытом.

CASA ошибочно свела «ум» к **лингвистическому content** (lexicon + compose). Нужна **та же архитектурная идея**: у von-neumann — **Intelligence Zones**, каждая = innate core + optional sandbox + life development (паттерн ADR-0060).

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
| **linguistic** | лингвистический | memory prisms, discourse compose | WM scratch, agent phrase lattices | content-heavy today |
| **logical** | логико-матhematical | math tract, schema-math bootstrap | math palochki / agent-math-* | tract OK; wire + situations |
| **social** | межличностный | dialogue ring, social tract, partner model | agent-social-sandbox (planned) | **gap** — repair, mentalizing |
| **spatial** | пространственный | prism_visual, control_vis | vis scratch (roadmap) | design only |
| **character** | temperament (медленный) | EMA поверх emotional + social | — | 0057; not separate sandbox v0 |

**g (general):** не отдельная zone — **executive** + predict + tract competition + value.

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
| **P4** | character | EMA from emotional + social cores |
| **P5** | spatial | when vis modality active |

### 5. Tick order (target)

```text
thalamus → predict → zones.read (emotional, executive, …)
→ DMN → SN → FPN → DAN → WM/intent
→ tract → agency → zone.apply → compose
→ zones.update → persist
```

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| New von-neumann store from zero for each ADR | migrate_intelligence_zones |
| One zone fixes all (only emotional) | full map; phased wire |
| Teacher mood / soul doc | neutral core + life + promote |
| Runtime new intelligence type | closed catalog; sandbox inside zone |

---

## Consequences

- ADR-0060 = emotional zone instance of this ADR.
- ADR-0059 = all zones listed must exist @ T=0 on **new** boot; **old** stores via migration.
- Curriculum (0057) targets **social**, **logical**, **emotional** situations — not new zones.
- Tests: migrate idempotent; spawn does not duplicate lattices.

## Links

- [CASA-ADR-0060-emotional-zone-v1.md](CASA-ADR-0060-emotional-zone-v1.md)
- [CASA-ADR-0059-innate-organ-basis-v1.md](CASA-ADR-0059-innate-organ-basis-v1.md)
- [CASA-ADR-0057-dialogue-situations-character-v1.md](CASA-ADR-0057-dialogue-situations-character-v1.md)
