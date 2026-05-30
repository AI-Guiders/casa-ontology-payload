# Experiment T9: predictive words on field (T9 replay)

**Status:** design (bench после `predictor_v0`)  
**Date:** 2026-05-30  
**Depends on:** [`predictor-v0.md`](predictor-v0.md), [`critic-v0.md`](critic-v0.md), store `sss-ru-lexicon-v0`  
**Blocks:** Exp L F1/F2 compose until green

---

## Idea

Repeat **T9 predictive text** on the **word layer only** — no arithmetic, no vis.

Partial / ambiguous input → **Predictor** ranks words from **field** (L2 + L1 + hippo `H:`) → **Critic** checks against completed word or held-out.

Proves the full loop **expectation vs reality** before `cow+cow`.

---

## Three cue types (v0)

| type | example cue | expect | engine |
|------|-------------|--------|--------|
| **prefix** | `пр`, `прик` | `приказ` / `приказу` | L2 prefix scan + field votes |
| **segment** | word `встреча` (internal) | `встре\|ча` | `segment_hypothesis` |
| **context** | phrase prefix `согласно пр` | `приказу` | L3 + active `R:` dative |

---

## Artifacts (planned)

```text
examples/exp_t9_v0/
  t9_prefix_cues.v1.json      # [{ "cue": "мам", "expect": "мама", "min_rank": 1 }]
  t9_segment_cues.v1.json
  t9_context_cues.v1.json
tools/bench_t9_predict_v0.py
```

---

## Pass criteria

- **top-1@prefix** ≥ 0.8 on 20 held-out prefixes (words in store, not in train cues)
- **predict.hypothesis == expect** after critic on segment/context set
- `claims_nav_enabled=false` throughout

---

## Smoke

```bash
python tools/bench_t9_predict_v0.py \
  --store-dir examples/agent-stores/sss-ru-lexicon-v0 \
  --cues examples/exp_t9_v0/t9_prefix_cues.v1.json \
  --boot-ltm-only
```

---

## Link to COMPREHEND

T9 «next letter disambiguates» = repeated **predict → compare → update** ticks — same architecture as teacher_correct loop, friendlier UX metaphor for demos.
