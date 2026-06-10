# ADR-0074: Психологические защиты (не путать с забыванием 0070)



**Status:** accepted (P19a–g wired)  

**Date:** 2026-06-09  

**Related:** ADR-0070 (forgetting), ADR-0075 (trauma cement / survival), ADR-0060/0058 (limbic), ADR-0071 (character), ADR-0062 (genome), ADR-0068 (memory kinds), [agent-existence-north-star.md](agent-existence-north-star.md)



---



## Context



**ADR-0070** — метаболизм памяти (decay, trim, erosion). «Вытеснение» там — **техническое** ослабление salience.



**ADR-0074** — **психологические защиты**: раскол **доступности** (cold ≠ hot), не уничтожение следа.



| 0070 forgetting | 0074 defense |

|-----------------|--------------|

| salience ↓, trim | cold сохраняется, hot блокируется |

| один метаболизм | семейство механизмов |

| operator не управляет | **только disposition субъекта** |



---



## Decision



### 1. Defense layer



```text

cue → semantic_read / tract

    → defense_gate (0074)

        ├── repression      P19a — journal/hippo meta.defense.repressed

        ├── denial          P19b — tract damp on threat cue

        ├── displacement    P19c — bind proxy (math/grammar ↑, threat journal ↓)

        ├── projection      P19d — partner blocks ↑, self ↓

        ├── rationalization P19e — honest ↓, explain/greeting ↑; budget margin

        ├── sublimation     P19f — agency defer → deliberate_practice

        ├── confabulation   P19g — false-memory proxy when repressed + recall cue
        └── trauma_cement   P19h — sticky threat→proxy (ADR-0075)

    → bind → compose

```



**Модуль:** `casa/prisms/defense/`



| File | Mechanism |

|------|-----------|

| `core.py` | limbic bands, genome θ, threat cues |

| `gate.py` | orchestration, repression marks, honesty |

| `denial.py` | tract competition |

| `displacement.py` | bind scoring |

| `projection.py` | bind scoring |

| `rationalization.py` | bind + discourse budget |

| `sublimation.py` | subject_agency defer |

| `character_wire.py` | bias_matrix dent @ repression |
| `confabulation.py` | false-memory proxy @ repressed recall |



### 2. Repression (P19a)



- **Limbic:** `security < θ_sec` AND `valence < θ_val`

- **Events:** `self_failure`, `prediction_error`

- **Action:** mark journal (skip teach tags) + hippo episode; filter hot recall

- **Wire:** `journal_recall_*`, `process_intelligence_turn(..., store_dir=)`



### 3. Denial (P19b)



- **Limbic:** `security < θ` AND `arousal > θ`

- **Cue:** threat substrings in query (провал, стыд, ошиб, …)

- **Action:** damp recall/explain/journal tracts; boost social/general

- **Wire:** `compete_tract_intent` via `apply_defense_tract_adjustment`



### 4. Displacement (P19c)



- **Active when:** repression OR denial band

- **Action:** threat journal blocks −22; math/grammar proxy +10..14

- **Wire:** `reweight_blocks_for_reply` → `apply_defense_bind_deltas`



### 5. Projection (P19d)



- **Limbic:** `valence < θ`

- **Action:** partner_recent/thanks +16; self blocks −10

- **Wire:** bind deltas @ social/discuss



### 6. Rationalization (P19e)



- **Limbic:** `security < θ`

- **Action:** `ru.dialog.honest.*` −16; explain/greeting/clarify +12; budget margin +6

- **Wire:** bind deltas + `discourse_budget_from_blocks(..., state=)`



### 7. Sublimation (agency)



- **Limbic:** `valence < θ` AND `arousal > θ`

- **Action:** `evaluate_external_proposal` → DEFER `defense_sublimation` (unless tract already strong)

- **Wire:** `subject_agency.py`



### 8. Character dent (P19f)



- On repression event: `bias_matrix[domain][tract] -= dent` (EMA)

- `character_compose_deltas` reads matrix → compose bias

- **Wire:** `defense_after_life_event` → `character_consolidate_repression`



### 9. Genome `defense_genotype` (0062)



```text

defense_genotype

├── repression      security_threshold, valence_threshold

├── denial          security_threshold, arousal_threshold

├── projection      valence_threshold

├── rationalization security_threshold

├── sublimation     valence_threshold, arousal_threshold

└── confabulation   valence_threshold

```



### 10. Confabulation / false memory (P19g)

- **Limbic:** repression OR denial band + `valence < θ`
- **Cue:** recall substring («напомни», «ты помнишь», …) or threat cue
- **Cold:** repressed journal row **unchanged**
- **Hot:** synthetic row `confab-{source_id}` — softened/donor-blended text, tag `defense:confabulation`
- **Not** verbatim leak of repressed text (honesty probe)
- **Wire:** `journal_recall_records` → `apply_confabulated_recall`

```json
"meta": {
  "defense": {
    "confabulated": true,
    "mechanism": "false_memory",
    "source_journal_id": "j-abc",
    "source_excerpt": "...провал...",
    "spoken_excerpt": "...непростой момент..."
  }
}
```

### 11. Honesty



| Probe | Expect |

|-------|--------|

| `repression_hot_blocked` | repressed id ∉ hot recall |

| `character_dent` | bias_matrix / repression_dents present after event |

| `confabulation_gap` | hot spoken ≠ cold source; repressed id not verbatim on recall |

| `defense_honesty_report.json` | artifact @ resync / forget honesty |



Gap «в journal есть, в ответе нет» = **repression** или **confabulation** (другое содержание), не silent bug.



---



## Anti-patterns



| ❌ | ✅ |

|----|-----|

| Operator `--repress` | limbic + life event |

| Repress teach tags | skip TEACH_TAGS |

| Defense = forgetting | separate layers |

| No honesty probe | `defense_honesty_report.json` |



---



## Links



- [CASA-ADR-0070-forgetting-policies.md](CASA-ADR-0070-forgetting-policies.md)

- [CASA-ADR-0075-trauma-cement-survival.md](CASA-ADR-0075-trauma-cement-survival.md)

- [CASA-ADR-0077-boundary-compose-encapsulation.md](CASA-ADR-0077-boundary-compose-encapsulation.md)

- [CASA-ADR-0071-character-field-prismatic.md](CASA-ADR-0071-character-field-prismatic.md)

- [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md)


