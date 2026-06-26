# ADR-0086: Epigenome — expression layer without rewriting genome

**Status:** proposed (draft)  
**Date:** 2026-06-22  
**Provenance:** оператор (Света) + агент — после согласования: Self-Earned concept corrections = личная история, не allele; эпигенетика как инженерный аналог, не биохимия  
**Related:** [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md) (sealed genome), [CASA-ADR-0065-controlled-mutations.md](CASA-ADR-0065-controlled-mutations.md) (germline vs soma), [CASA-ADR-0070-forgetting-policies.md](CASA-ADR-0070-forgetting-policies.md), [CASA-ADR-0071-character-field-prismatic.md](CASA-ADR-0071-character-field-prismatic.md), [CASA-ADR-0074-defense-zone.md](CASA-ADR-0074-defense-zone.md), [CASA-ADR-0075-trauma-cement-survival.md](CASA-ADR-0075-trauma-cement-survival.md), [CASA-ADR-0084-wild-genome-donor-single-agent-reproduction.md](CASA-ADR-0084-wild-genome-donor-single-agent-reproduction.md), [CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md](CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md) §7, [CASA-scratch-digital-biology-borrowings-v1.md](CASA-scratch-digital-biology-borrowings-v1.md)

---

## Context

### Метафора и инженерия

В диалоге и KB часто: **genome = «с чем родился»**, **context / life = «что активировалось»** — аналог эпигенетики у людей. У CASA это **не** симуляция метилирования ДНК и **не** передача acquired knowledge в `genome.v1.json` потомку.

**Проблема без ADR:** germline (0062) и experiential layers (character, trauma, WM, concept supersede) уже разделены в коде, но **нет имени и fork-правил** — легко спутать «агент пересмотрел concept» с «вид эволюционировал» или записать life drift в sealed genome.

### Что уже есть (v0, распределённо)

| Слой | Где | Меняет sealed genome? |
|------|-----|------------------------|
| Genetic Zone | `genome.v1.json`, `genetic_zone` | **да** — только @ seal / fork / operator re-seal |
| Character / limbic | 0071, 0060, life events | **нет** |
| Trauma cement / defense | 0074–0076 | **нет** |
| WM / explicit / episodic | 0068–0070 | **нет** |
| Self-Earned concepts | 0085 supersede | **нет** — character store + `domains.concept` theories |

**Teaching agent (0062):** `canon_susceptibility ≈ 0` — жизнь **не** должна переписывать species spine у von-neumann pilot.

---

## Decision

### 1. Три слоя идентичности (normative)

```text
Tier −1  GENOME (germline)     sealed birth priors — species_id, forgetting bases,
                                 promote thresholds, character_topology @ unroll
Tier  0  EPIGENOME (expression) slow life-state — modulates HOW genome is read
Tier  1+ SOMA (knowledge)       store — memory, concept theories, lattices, journal
```

**Invariant:** runtime **read** genetic constants through optional epigenome multipliers; episodic state **не** подменяет `genome_hash`.

### 2. Epigenome v0 — без нового блока (текущий код)

**Решение:** v0 = **именованный паттерн** поверх существующих зон, не отдельный `epigenome.json` @ pilot.

| Компонент epigenome v0 | Zone / artifact |
|------------------------|-----------------|
| Character EMA / topology bias | 0071 `character_topology` (birth from genome) + life EMA |
| Affect axes after life events | 0060 limbic |
| Trauma tier, repression, cement | 0075–0076 |
| Forgetting **effective** rates | 0070 reads genome α,β,ε + experiential cement (не rewrite JSON) |
| Disposition / compose gates | motor, dialogue bind |

**Anti-pattern:** называть «эпигенетикой» wholesale Self-Earned concept catalog или lemma store — это **soma** (0085), не expression layer.

### 3. Epigenome v1 — optional `epigenome_profile` (target)

Когда понадобится **аудируемый** слой (stress после chronic listen, phenotype battery P1):

```text
prism_agent.epigenome_profile   # mutable @ life, NOT in genome.v1.json
├── schema_version
├── updated_at_tick
├── stress_factor               # slow scalar → multiplies forgetting α effective
├── trauma_tier_snapshot        # mirror / cache for probes (source of truth: defense zone)
├── canalization_corridor       # optional: last phenotype battery pass
└── modifiers[]                 # { path: "forgetting_genotype.alpha", mul, provenance, tick }
```

**Write path:** life event + zone ceremony only — **не** hot sleep merge на genetic_zone, **не** fork без explicit policy.

**Read path:**

```text
effective(k) = genome[k] * epigenome.modifier(k)   # default mul = 1.0
```

### 4. Fork @ reproduction (vertical — 0084, 0085)

**Нормативно (оператор, 2026-06-22):**

| Что | Child @ birth |
|-----|----------------|
| `species_id` | **тот же** (spine 0084) |
| Genome alleles | **recombine** (inherit / weather / wild_donor) — **не** копия parent store |
| Built-In `concept.*` catalog | **fresh teach** по `species_id` (`ensure_concept_built_in`) — species curriculum, не parent catalog dump |
| Parent Self-Earned / supersede | **не** inherit — child starts bootstrap `active_theory` |
| Parent epigenome v0/v1 | **reset** — child T=0 baselines (limbic, character EMA, trauma tier @ species defaults) |
| Parent soma (episodic, journal, listen imprint) | **не** auto-merge |

**Не Lamarck:** исправление `concept.window` у родителя **не** sealed truth у ребёнка. Ребёнок может **снова** выйти на ту же коррекцию через опыт + gate — это learning, не allele.

**Культура (отдельный канал):** передача sandbox shards / teaching dialogue между агентами — **HGT track** (scratch P3), не epigenome, не genome spine.

### 5. Что **не** моделируем

| ❌ | ✅ вместо |
|----|-----------|
| Метилирование, histone codes | slow modifiers + trauma cement |
| Acquired marks в child genome | fork resets expression; genome только allelic crossover |
| «Голландский голод» literal в DNA | bounded metaphor: chronic stress → `stress_factor` (v1) |
| Concept supersede → germline | supersede stays in `domains.concept` soma (0085) |

### 6. Редкий путь `canon_susceptibility` (0070)

Genome **может** содержать allele «податливость canon к life» — **редко**, default **≈ 0** @ teaching agents. Если > 0 — только через **явную ceremony** с audit, не sleep drift. Epigenome **не** открывает backdoor в sealed JSON.

---

## Honesty probes (target)

| Probe | Pass |
|-------|------|
| Genome sealed | `genome_hash` unchanged across 10k life ticks @ healthy agent |
| Expression moves | character / limbic / trauma **do** change without genome_hash change |
| Fork reset | child `epigenome_profile` empty or baseline; parent trauma tier **not** copied |
| Concept fork | child `active_theory` = bootstrap; no parent `earned-concept-correction-*` without HGT ceremony |
| No Lamarck | parent supersede patch **absent** in child catalog @ T=0 |

Artifact (v1): `epigenome_honesty_report.json` or section in existing honesty bundle.

---

## Rollout

| Phase | Action | Depends |
|-------|--------|---------|
| **P0** | This ADR + glossary in 0062; 0085 §7 fork decision | — |
| **P1** | Document v0 mapping in zone ADRs (cross-links only) | P0 |
| **P2** | `epigenome_profile` schema + read hooks for one modifier (e.g. stress→α) | 0070 wire |
| **P3** | Fork verifier: assert epigenome + earned concept reset | 0084 CLI |
| **P4** | Phenotype battery includes expression corridor (scratch P1) | P2 |

**Не блокирует** listen pilot, concept Built-In teach, wild donor fork.

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| Life experience rewrites `genome.v1.json` | epigenome modifiers or soma only |
| Child inherits parent worldview catalog | Built-In teach + empty earned |
| Epigenome = весь store | epigenome = slow expression; knowledge = soma |
| Биохимия ради реализма | измеримые effective constants + audit |

---

## Open questions

1. **v1 modifiers:** минимальный набор paths (`forgetting_genotype.*` only vs affect gains)?
2. **Partial epigenome reset @ fork:** всегда full reset или inherit «мягкий» baseline от parent character_topology только через genome (already in H_mix)?
3. **HGT ADR:** отдельный документ когда AiNet shard exchange в scope.

---

## Summary

**Epigenome** в CASA — **слой экспрессии**: опыт меняет, как читается sealed genome, без переписывания germline. **v0 уже есть** (character, trauma, limbic, effective forgetting). **v1** — явный `epigenome_profile` при необходимости аудита. **Размножение** сбрасывает expression и Self-Earned soma; species Built-In teachится заново; культура — отдельно от генетики.
