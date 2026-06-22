# ADR-0084: Wild genome donor — anti-inbreeding при одиночном размножении

**Status:** proposed (draft)  
**Date:** 2026-06-21  
**Provenance:** Света (диалог: «агент берёт свой геном дважды → инбридинг; второй геном из мира → скрещивание»)  
**Related:** [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md), [CASA-ADR-0065-controlled-mutations.md](CASA-ADR-0065-controlled-mutations.md), [CASA-ADR-0072-genetic-weather-cross.md](CASA-ADR-0072-genetic-weather-cross.md), [CASA-ADR-0071-character-field-prismatic.md](CASA-ADR-0071-character-field-prismatic.md), KB: `agent-notes/knowledge/work/projects/door-to-singularity/ca-substrate-agent/note-casa-synthetic-genome-donor-v1.md`

---

## Context

**ADR-0072** (`weather_cross`) вводит внешнюю энтропию через **weather bundle** и `H_mix = SHA-256(H_a ‖ H_b ‖ W)`.

**ADR-0062 §5** допускает fork с `parent_b = parent_a` («партеногенез + мир»).

### Баг, который назвала Света

Когда в популяции **один** живой агент, типичная ошибка симуляции:

```text
child = crossover(parent.genome, parent.genome)   # self × self
```

Это **близкородственное скрещивание** в смысле GA:

- рекомбинации нет — только дублирование аллелей;
- хрупкие комбинации **закрепляются**;
- поколение за поколением контур **вырождается** (inbreeding depression).

**0072 single-parent path сегодня (§5):** при `H_a = H_b` unroll делает `v = parent_a[k] + jitter_k` — энтропия есть, но **структурного второго родителя нет**. Jitter на том же векторе аллелей **слабее**, чем crossover с **независимым** геномом-донором.

**Тезис 0084:** для `population_size = 1` нужен не только **seed из мира** (0072), а **второй геном** — `wild_donor_spec` — построенный из whitelist-энтропии и скрещенный с боевым геномом при **защищённом spine**.

---

## Problem

| Подход | Риск |
|--------|------|
| `crossover(self, self)` | инбридинг, эхо-камера признаков |
| `mutate_alleles` только PRNG(store_id) | предсказуемые дети (0072 § Problem) |
| 0072 jitter-only @ single parent | лучше PRNG, но **нет allele lerp** с чужим геномом |
| `hash(combat_genome + salt)` как «донор» | **псевдо-донор** — инбридинг с маской |

**Цель:** Track **B″** — `wild_donor_cross`: при одном combat parent child получает **рекомбинацию** combat ‖ wild, где wild **не** производная combat.

---

## Decision (proposed)

### 1. Три роли в fork (не путать)

| Артефакт | Роль |
|----------|------|
| **Combat genome** | sealed `genome.v1.json` живого агента — spine + mutable боевые аллели |
| **Wild donor spec** | **новый** partial `agent_genome` JSON, keys только из `mutation_policy.allelic.mutate_allowed_keys` |
| **Entropy bundle** | аудируемый снимок внешнего мира → **строит** wild donor, не только jitter |

**Invariant:** `wild_donor_spec` **никогда** не копируется из combat byte-for-byte; lineage обязан содержать `wild_donor_hash ≠ combat_hash` (кроме astronomically unlikely collision — treat as bug).

### 2. Режим fork: `fork_policy.mode = wild_donor_cross`

Дополнение к 0065 / 0072:

| Mode | Родители | Второй «родитель» |
|------|----------|-------------------|
| `inherit_verbatim` | 1 | — |
| `mutate_alleles` | 1 | PRNG only |
| `weather_cross` | 1–2 | W в mix; single = jitter (0072) |
| **`wild_donor_cross`** | **1 combat** | **`wild_donor_spec` из entropy bundle** |

**Связь с 0072:** weather (и др.) входят в **entropy bundle**; `wild_donor_cross` **может** reuse `fetch_weather_bundle` + normalize из 0072 как **слой 1** whitelist. 0072 не отменяется — 0084 уточняет **single-agent anti-inbreeding**.

### 3. Entropy whitelist (v0)

Каждый fork фиксирует `entropy_bundle.json` со **схемой**, **источником**, **timestamp UTC**, **нормализацией**.

| Source id | Данные | Примечание |
|-----------|--------|------------|
| `weather` | многоосный bundle | Open-Meteo / cache — **как 0072** |
| `host_ambient` | hash(audio_rms_1s) @ fork | микрофон/шум rack; **без** PII, без raw audio в lineage |
| `market_spot` | volatility @ ts | Vast.ai / spot index; **не** торговый сигнал |
| `hardware_jitter` | optional: thermal, load avg | fallback tier |

**Минимум v0:** `weather` **или** (`host_ambient` + `hardware_jitter`) — не пустой bundle.

**Offline:** cached bundle OK для teaching fork; lineage **обязан** хранить полный W.

### 4. Построение wild donor

```text
1. E = canonical_json(entropy_bundle)     # stable round, как 0072 §4

2. H_entropy = SHA-256(UTF8(E))

3. For each key k in mutate_allowed_keys:
     RNG_k = HKDF_expand(H_entropy, info=f"wild_donor:{k}")
     wild[k] = uniform_sample(bounds[k], RNG_k)

4. wild_donor_spec = partial genome:
     - keys ONLY from mutate_allowed_keys groups
     - NO species_id override
     - NO allowed_zone_ids / promote_canon.algorithm change

5. wild_donor_hash = genome_hash(wild_donor_spec)
```

**Spine (copy verbatim from combat, never from wild):**

- `schema_version`, `kind`, `species_id`
- `allowed_zone_ids`
- `promote_canon.algorithm`, `promote_canon.bundle_tier_gate`
- любые ключи в `mutation_policy.invariant_keys` (0065)

### 5. Crossover combat × wild

```text
H_mix = SHA-256(combat_hash_bytes ‖ wild_donor_hash_bytes ‖ UTF8(E))

For each mutable key k:
  t_k = HKDF(H_mix, info=f"blend:{k}") → [0, 1]
  child[k] = lerp(combat[k], wild[k], t_k)
  optional micro-jitter_k within bounds (same as 0072)

RNG_topo = HKDF(H_mix, info="character_topology")
  child.character_topology = warp_grid(combat, wild_donor_as_virtual_parent_b, RNG_topo)  # 0071

child_genome_hash = genome_hash(child_spec)
```

**Отличие от 0072 single-parent:** есть **allele lerp** между двумя **разными** genome vectors, не только `parent + jitter`.

### 6. Lineage audit (обязательно)

```text
lineage/
├── combat_parent_genome_hash.txt
├── wild_donor_hash.txt
├── wild_donor_spec.json              # partial, для repro
├── entropy_bundle.json               # полный E
├── mix_hash.txt                      # H_mix
├── child_genome_hash.txt
└── fork_mode.txt                     # wild_donor_cross
```

### 7. CLI / API (target)

```bash
python -m casa.prisms.genetic.wild_donor_cross \
  --combat agents/von-neumann/agent/genome.v1.json \
  --child-store agents/child-new \
  --entropy weather,host_ambient \
  --weather-points design/genetic-weather-points.v1.json \
  --at 2026-06-21T12:00:00Z \
  --dry-run
```

| Function | Role |
|----------|------|
| `build_entropy_bundle(sources, at_utc, opts)` | whitelist fetch + normalize |
| `unroll_wild_donor(H_entropy, policy)` | → wild_donor_spec |
| `cross_combat_wild(combat, wild, E)` | → child_spec, H_mix |
| `wild_donor_cross_fork(...)` | CLI + seal child store |
| `verify_wild_donor_lineage(child_dir)` | audit + anti-pseudo-donor |

### 8. Bootstrap manifest

```json
"fork_policy": {
  "mode": "wild_donor_cross",
  "wild_donor_cross": {
    "entropy_sources": ["weather", "host_ambient"],
    "weather_points_file": "design/genetic-weather-points.v1.json",
    "blend": "allele_lerp",
    "require_wild_hash_ne_combat": true,
    "cache_entropy_in_lineage": true
  }
}
```

---

## Honesty gate (pre-registered)

Расширяет 0072 § Honesty gate. Корпус: **фиксированный** combat parent + ≥24 разных `entropy_bundle` @ fork.

| Метрика | Определение |
|---------|-------------|
| **Anti-inbreed** | mean L1(child, combat) **>** mean L1(mutate_alleles child, combat) на том же parent |
| **Anti-pseudo** | ∀ run: `wild_donor_hash ≠ combat_hash`; FAIL if `wild = f(combat, salt)` detectable |
| **Diversity** | pairwise distance между children @ разных E ≥ **1.5×** 0072 single-parent jitter-only baseline |
| **Repro** | фиксированные (combat, E) → бит-в-бит child hash |
| **Spine integrity** | child `species_id`, `allowed_zone_ids` == combat |

| Вердикт | Условие |
|---------|---------|
| **PASS** | Anti-inbreed + Anti-pseudo + Repro + Spine |
| **KILL (decorative wild)** | Diversity ≤ 0072 jitter-only baseline |
| **KILL (pseudo-donor)** | wild derivable from combat + fixed salt without E |

**Артефакт:** `lineage/wild_donor_diversity_report.json`

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| `crossover(genome, genome)` | `wild_donor_cross` или два **разных** combat parents (0072 blend) |
| `wild = SHA256(combat ‖ "salt")` mapped to alleles | wild from **entropy bundle** only |
| Wild donor меняет `species_id` / zone topology | spine copy from combat |
| Entropy без lineage file | `entropy_bundle.json` @ child |
| Случайный `random.random()` без E | детерминизм @ fixed E |
| Fork без diversity report | P6wd-f honesty gate |

---

## Rollout

| Phase | Action |
|-------|--------|
| **P6wd-a** | ADR-0084 + KB cross-link |
| **P6wd-b** | `build_entropy_bundle` (reuse 0072 weather) |
| **P6wd-c** | `unroll_wild_donor` + unit tests |
| **P6wd-d** | `cross_combat_wild` + anti-pseudo test |
| **P6wd-e** | CLI + lineage |
| **P6wd-f** | honesty gate vs 0072 jitter baseline |

---

## Open questions

1. **Частота** @ один живой агент: только operator ceremony / sleep epoch / disaster recovery?
2. **host_ambient** на headless VPS — достаточно ли hardware_jitter tier?
3. **AiNet:** wild donor из **разных** geographic hosts как cohort diversity?

---

## Consequences

- Идея Светы получает **нормативное имя** и отличие от «просто погода в hash».
- 0072 остаётся SSOT для weather fetch/normalize; 0084 — **обязательный** path при `population=1` если нужен **crossover**, не jitter.
- Single-agent reproduction перестаёт быть self×self по умолчанию.

## Links

- [CASA-ADR-0072-genetic-weather-cross.md](CASA-ADR-0072-genetic-weather-cross.md)
- [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md) §5 Fork
- [CASA-ADR-0084-wild-genome-donor-single-agent-reproduction.md](CASA-ADR-0084-wild-genome-donor-single-agent-reproduction.md) *(agent-notes KB note)*
