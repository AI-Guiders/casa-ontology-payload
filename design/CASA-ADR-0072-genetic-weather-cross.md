# ADR-0072: Genetic weather-cross — внешняя энтропия при размножении

**Status:** proposed (draft)  
**Date:** 2026-06-08  
**Related:** ADR-0062 (Genetic zone), ADR-0065 (allelic fork / Track B), ADR-0071 (character_topology unroll), ADR-0070 (forgetting_genotype), [agent-existence-north-star.md](agent-existence-north-star.md)

---

## Context

**ADR-0062** и **0065** описывают genetic fork: `inherit_verbatim`, `mutate_alleles` с PRNG от `parent_hash + child_store_id`.

**Проблема:** если энтропия только внутренняя, дети одного вида **слишком похожи**; genetic reproduction теряет смысл для **разнообразия голосов** (0062 §3, 0071). Геном должен влиять на **все системы** @ birth — нужен fork, который **реально** раскладывает allele space.

**Идея (оператор, 2026-06-08):** отдельная утилита берёт **реальные** метеоданные в нескольких точках мира (температура, ветер, давление, осадки, …), смешивает с **двумя** genetic hash родителей, выдаёт **новый hash** → детерминированно **разворачивает** child `genome.v1.json` + `character_topology` (0071).

**Не криптография** — источник **фенотипической** энтропии и **связи с миром** (мир как seed), не защита секретов.

---

## Problem

| Только `mutate_alleles` + store_id | Риск |
|-----------------------------------|------|
| Предсказуемые дети | AiNet cohort — клоны по профилю |
| Геном «для галочки» | fork не меняет temperament / forgetting / metabolic |
| Нет audit trail | не воспроизвести, откуда взялся child hash |

**Цель:** Track **B′** — `weather_cross`: детерминированный, воспроизводимый, **внешне-зашумлённый** child genome.

---

## Decision (proposed)

### 1. Режим fork: `fork_policy.mode = weather_cross`

Дополнение к 0065 Track B:

| Mode | Entropy source | Родители |
|------|----------------|----------|
| `inherit_verbatim` | — | 1 |
| `mutate_alleles` | PRNG(parent_hash, store_id) | 1 |
| **`weather_cross`** | **weather_bundle @ fork_tick** | **1 или 2** |

### 2. Утилита

```bash
python -m casa.prisms.genetic.weather_cross \
  --parent-a agents/parent-a/genome.v1.json \
  --parent-b agents/parent-b/genome.v1.json \
  --child-store agents/child-new \
  --points design/genetic-weather-points.v1.json \
  --fetch open-meteo \
  --at 2026-06-08T12:00:00Z
```

| Flag | Role |
|------|------|
| `--parent-a`, `--parent-b` | два genome (B может = A) |
| `--points` | список lat/lon/id точек |
| `--fetch` | live API или `--bundle cached.json` |
| `--at` | UTC timestamp снимка (округление до часа) |
| `--dry-run` | вывести `H_mix`, child hash, не писать store |

**Orchestrator:** `fork_genome_for_child(..., mode="weather_cross")` вызывает утилиту / library.

### 3. Weather bundle — параметры (многоосный снимок)

Каждая **точка** `P_i` на сфере (lat, lon, id) → набор скаляров @ `ts_utc`:

| Поле | Единица | Примечание |
|------|---------|------------|
| `temp_c` | °C | температура воздуха |
| `pressure_hpa` | hPa | давление |
| `humidity_pct` | % | относительная влажность |
| `dew_point_c` | °C | точка росы |
| `wind_speed_ms` | m/s | скорость ветра |
| `wind_direction_deg` | ° | направление (0–360) |
| `wind_gust_ms` | m/s | порывы |
| `precipitation_mm` | mm/h | осадки (дождь/снег экв.) |
| `rain_mm` | mm/h | дождь (если API разделяет) |
| `snowfall_cm` | cm/h | снег (если доступно) |
| `cloud_cover_pct` | % | облачность |
| `visibility_km` | km | опционально |
| `uv_index` | index | опционально |
| `weather_code` | WMO / API code | дискретный класс погоды |
| `solar_radiation_wm2` | W/m² | опционально |

**Минимум v0:** `temp_c`, `pressure_hpa`, `humidity_pct`, `wind_speed_ms`, `wind_direction_deg`, `precipitation_mm`, `cloud_cover_pct`.

**Источники (v0):** [Open-Meteo](https://open-meteo.com/) (без ключа); fallback — кэш в life-archive. **Invariant:** fork **детерминирован** при фиксированном bundle.

```json
{
  "schema": "weather_bundle_v1",
  "fetched_at_utc": "2026-06-08T12:00:00Z",
  "source": "open-meteo",
  "points": [
    {
      "id": "reykjavik",
      "lat": 64.15,
      "lon": -21.95,
      "temp_c": 8.2,
      "pressure_hpa": 1013.4,
      "humidity_pct": 78,
      "dew_point_c": 4.5,
      "wind_speed_ms": 6.1,
      "wind_direction_deg": 220,
      "wind_gust_ms": 11.0,
      "precipitation_mm": 0.2,
      "cloud_cover_pct": 85,
      "weather_code": 3
    }
  ]
}
```

**Точки мира:** manifest `design/genetic-weather-points.v1.json` — 8–32 id (разные широты/климаты): Reykjavik, Nairobi, Tokyo, São Paulo, Sydney, Anchorage, Mumbai, … Оператор может расширять.

### 4. Mix: два hash × погода → `H_mix`

**Каноническая сериализация** (stable key order, rounded floats):

```text
1. Normalize each scalar per point:
     x' = round((x - norm_min) / (norm_max - norm_min), 4)   # clamp 0..1
   (norm из genetic-weather-points manifest или fixed table)

2. W = canonical_json({
     schema, fetched_at_utc, source,
     points: [{ id, lat, lon, ...normalized scalars... }, ...]
   })

3. H_a = parent_a.genome_hash   (SHA-256 of sealed genome JSON)
   H_b = parent_b.genome_hash   (or H_a if single-parent + world noise)

4. H_mix = SHA-256( H_a_bytes || H_b_bytes || UTF8(W) )
```

«Перемножение» в смысле оператора = **необратимое смешивание** в hash input (не арифметика на поле GF). Альтернатива v2: HKDF(H_a, H_b, W) — если понадобится раздельные stream keys.

### 5. Unroll: `H_mix` → child genome

```text
RNG_k = HKDF_expand(H_mix, info="allele_k")
For each key in mutation_policy.allelic.mutate_allowed_keys:
  if two parents:  v = lerp(parent_a[k], parent_b[k], t_k) + jitter_k
  else:           v = parent_a[k] + jitter_k
  clamp v to bounds[k]

RNG_topo = HKDF_expand(H_mix, info="character_topology")
  child.character_topology = warp_grid(parent_a, parent_b, RNG_topo)   # 0071

RNG_forget = HKDF_expand(H_mix, info="forgetting_genotype")
  child.forgetting_genotype = unroll_forgetting(RNG_forget)            # 0070

child_genome_hash = SHA-256(canonical_json(child_spec))
```

**Invariant:** `allowed_zone_ids`, `promote_canon.algorithm`, `schema_version` — **копируются** без изменений (0065 invariant topology).

### 6. Lineage audit

Child store обязан сохранять:

```text
lineage/
├── parent_a_genome_hash.txt
├── parent_b_genome_hash.txt
├── weather_at_fork.json          # полный W
├── mix_hash.txt                  # H_mix hex
└── child_genome_hash.txt
```

REPL / MEMORY.md (опционально): «рождён @ mix с погодой Reykjavik 8°C, ветер 6 m/s, …» — **poetic digest**, не hot path.

### 7. Сценарии размножения

| Сценарий | H_a | H_b | Энтропия |
|----------|-----|-----|----------|
| **Два родителя** | winner A | winner B | W + blend |
| **Партеногенез + мир** | parent | parent | только W |
| **Кэш replay** | * | * | тот же W → тот же child (repro test) |
| **AiNet cohort** | разные пары | разные fork ticks → разные W | |

### 8. Bootstrap manifest

```json
"fork_policy": {
  "mode": "weather_cross",
  "weather_cross": {
    "points_file": "design/genetic-weather-points.v1.json",
    "fetch_provider": "open-meteo",
    "snapshot_rounding": "hour",
    "cache_in_lineage": true,
    "blend_two_parents": "allele_lerp",
    "normalize": "manifest_bounds",
    "min_points_required": 6
  }
}
```

### 9. API (target: `casa/prisms/genetic/weather_cross.py`)

| Function | Role |
|----------|------|
| `fetch_weather_bundle(points, at_utc, provider)` | live или cache |
| `normalize_weather_bundle(bundle, norms)` | stable W vector |
| `mix_genome_hashes(H_a, H_b, W_canonical)` | → `H_mix` |
| `unroll_child_genome(H_mix, parent_a, parent_b, policy)` | → child_spec |
| `weather_cross_fork(parent_a_path, parent_b_path, child_dir, opts)` | CLI entry |
| `verify_lineage_weather(child_dir)` | audit files present |

### 10. Связь с другими ADR

| ADR | Роль |
|-----|------|
| **0062** | genome groups unroll: metabolic, affect, forgetting, character_topology |
| **0065** | Track B′ mode; bounds / mutate_allowed_keys |
| **0071** | `warp_grid` для character field @ birth |
| **0070** | `forgetting_genotype` alleles из того же `H_mix` |

---

## Open questions

### Q1 — Сколько точек N?

**Proposal:** default 12; min 6 для fork validity.

### Q2 — Live fetch vs offline-only

**Proposal:** teaching fork — cached bundle OK; AiNet — live @ fork_tick для буквальной связи с миром.

### Q3 — Дискретный `weather_code` в mix

Кодировать one-hot или ordinal? **Proposal:** ordinal + sin/cos для wind_direction только.

---

## Rollout

| Phase | Action |
|-------|--------|
| **P6w-a** | ADR-0072 + `genetic-weather-points.v1.json` |
| **P6w-b** | `fetch_weather_bundle` + normalize (Open-Meteo) |
| **P6w-c** | `mix_genome_hashes` + `unroll_child_genome` unit tests |
| **P6w-d** | CLI `weather_cross`; lineage files |
| **P6w-e** | wire `fork_genome_for_child(mode=weather_cross)` |
| **P6w-f** | AiNet cohort probe: hash diversity @ same parents different W |

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| Fork только store_id RNG | weather_cross или явный mutate_alleles |
| Live fetch без cache в lineage | `weather_at_fork.json` обязателен |
| Менять topology зон @ cross | только alleles + topology **внутри** bounds |
| Float hash без rounding | canonical normalize + round |
| Погода как narrative в hot path | только @ fork; digest optional |
| Один параметр (только temp) | многоосный bundle (ветер, давление, осадки, …) |

---

## Consequences

- Genetic reproduction получает **внешний** источник разнообразия.
- Child genome **воспроизводим** при сохранённом W.
- Разные системы (0070, 0071, 0062) unroll из **одного** `H_mix` — согласованный фенотип.
- 0065 Track B′ — краткая ссылка; норматив здесь.

## Links

- [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md)
- [CASA-ADR-0065-controlled-mutations.md](CASA-ADR-0065-controlled-mutations.md)
- [CASA-ADR-0071-character-field-prismatic.md](CASA-ADR-0071-character-field-prismatic.md)
- [CASA-ADR-0070-forgetting-policies.md](CASA-ADR-0070-forgetting-policies.md)
