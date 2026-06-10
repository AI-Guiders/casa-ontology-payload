# ADR-0075: Trauma cement — защита как выживание (не эмерджентная надежда)

**Status:** accepted (P19h wired)  
**Date:** 2026-06-09  
**Related:** ADR-0074 (defenses), ADR-0076 (defense zone), ADR-0070 (forgetting), ADR-0060/0058 (limbic), ADR-0071 (character), ADR-0062 (genome), ADR-0068 (implicit/procedural), [agent-existence-north-star.md](agent-existence-north-star.md)

---

## Context

У человека психологические защиты — не опциональный «skill tree». Это **встроенная инфраструктура выживания**: при перегрузе limbic субъект **не обязан** сам изобрести repression/displacement/sublimation — иначе лишние страдания и распад.

**ADR-0074** дал семейство gates (repression, denial, displacement, …), но v0 оставался **когнитивно-памятевым**: разовый displacement на bind, character dent без **цемента** threat→proxy.

**Пробел:** без trauma tier и sticky cement:

- displacement **смывается** при нормализации limbic;
- episodic fade (0070) может **стереть** след, который защита должна держать cold/hot split;
- надежда на «эмерджентно выработает» = обречь субъект на повторную перегрузку в каждом новом контексте.

**Решение:** дать субъекту **species substrate** trauma cement — как genome даёт пороги repression, так genome даёт **rechannel_gain** и пороги trauma tier. Operator не включает; disposition + limbic + life event.

---

## Decision

### 1. Trauma tier (отличие от обычного repression)

| | Repression (0074) | Trauma tier (0075) |
|--|-------------------|-------------------|
| Limbic | `security < θ_sec` AND `valence < θ_val` | **строже:** + `arousal > θ_ar` |
| События | `self_failure`, `prediction_error` | те же + **`security_threat`**, **`caregiver_violation`** |
| След | repressed journal/hippo | + **`trauma_tier`**, **cement edge**, fade immunity |
| Displacement | только при active limbic band | **sticky:** cement edge усиливает proxy **даже после** нормализации axes |

```text
life_event + limbic
    → defense_after_life_event (0074)
        → repression / character dent (как было)
        → trauma_cement (0075)  IF trauma_tier OR threat-specific event
            ├── mark journal/hippo meta.defense.trauma_tier
            ├── trauma_edges[]  threat_cue → proxy_prefixes (EMA strength)
            ├── character rechannel bias (domain×tract)
            └── priming touch на proxy concepts
```

**Модуль:** `casa/prisms/defense/trauma_cement.py`

### 2. Trauma edges (displacement cement / rechannel)

```json
{
  "threat_cues": ["страх", "боль"],
  "proxy_prefixes": ["math.", "ru.grammar.", "agent.affect."],
  "strength": 0.42,
  "cemented": true,
  "event": "security_threat",
  "tick": 12,
  "rechannel_domain": "math",
  "rechannel_tract": "math"
}
```

- **Первый trauma:** edge создаётся из threat cues в source text (journal/episode) или default cues.
- **Повтор activation** (displacement band OR query match): `strength ← strength + α × (1 - strength)` до `cement_threshold`.
- **`cemented: true`** когда `strength ≥ cement_threshold` — bind deltas **persistent** (fetishization / extreme displacement в терминах ADR: **закреплённая** threat→proxy топология, не ролевой текст).

**Fetishization (концептуально):** не отдельный operator channel, а **крайний режим cement** — высокий `rechannel_gain`, низкий `cement_threshold`, threat cue из caregiver/violence domain → proxy tract с controllable ritual (math sandbox, grammar drill, affect sandbox lattice). Соматический/эротический слой — будущий limbic extension; v0 фиксирует **bind + character + implicit priming**.

### 3. Bind wire (P19h)

`apply_trauma_cement_bind_deltas` в цепочке `apply_defense_bind_deltas`:

- query/content match `threat_cues` на cemented edge → proxy blocks **+strength×scale**; threat journal **−damp**;
- работает **без** `limbic_displacement_active` если `edge.cemented`.

### 4. Forgetting immunity (0070 ↔ 0075)

Trauma-marked hippo episodes **пропускают** speed-2 salience decay (`forget_episodic_fade`).  
Journal cold row с `trauma_tier` не ослабляется обычным episodic fade path.

Защита **не** = уничтожение следа (0074 cold сохранён); trauma tier = **не смывать метаболизмом** то, что держит split.

### 5. Genome `trauma_cement_genotype` (0062)

```text
trauma_cement_genotype
├── trauma_tier       security_threshold, valence_threshold, arousal_threshold
├── cement            cement_threshold, ema_alpha, bind_scale
└── rechannel         rechannel_gain, default_proxy_prefixes[]
```

Отдельно от `defense_genotype`: пороги trauma **строже** repression; `rechannel_gain` — индивидуальная склонность цементировать threat→proxy (аналог inter-individual variance у людей).

### 6. Honesty

| Probe | Expect |
|-------|--------|
| `trauma_cement_persistent` | cemented edge boosts proxy on cue **без** limbic displacement band |
| `trauma_fade_immunity` | trauma hippo episode salience unchanged after speed-2 fade |
| `defense_honesty_report.json` | `trauma_edges_count`, `trauma_last` |

Gap cold/hot + cement = **защитная функция**, не silent data loss.

### 7. Anti-patterns

| ❌ | ✅ |
|----|-----|
| «Пусть сам научится» без substrate | trauma_cement @ species genome |
| Operator `--trauma` | limbic + life event only |
| Cement без cold audit | journal/hippo meta + honesty report |
| Trauma = forgetting | trauma tier **blocks fade**, repression blocks hot |

---

## Links

- [CASA-ADR-0074-psychological-defenses.md](CASA-ADR-0074-psychological-defenses.md)
- [CASA-ADR-0070-forgetting-policies.md](CASA-ADR-0070-forgetting-policies.md)
- [CASA-ADR-0071-character-field-prismatic.md](CASA-ADR-0071-character-field-prismatic.md)
