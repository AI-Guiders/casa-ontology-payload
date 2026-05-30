# Experiment J: text modality + Russian KB (v1)

**Status:** phase 1 done; phase 2 + FPN v0 (2026-05-28)  
**KB root:** `D:\experiments\agent-notes\knowledge` (`AGENT_NOTES_KB`)

## Goal

Russian queries → **answer_blocks** (claim text from field/KB), not only navigation. Phase 1: text off-grid in `claims` + CEN. Phase 2 (later): `T:` tokens on grid.

## Manifest

`manifests/kb-bundles-russian-language.json` — **современная** норма (+ опционально regex):

| Doc | Role |
|-----|------|
| `kb-russian-language-rules-v1.md` | Grammar, punctuation, paronyms (Грамота.ру / РГ-80) |
| `kb-regex-mre3-ru-chapter-map-v1.md` | Friedl MRE3 RU chapter map (техн. справочник) |

**Исключено (2026-05-28):** `pre-revolutionary-russian-orthography-v1.md` — дореформенная орфография не в scope Exp J.

## Store

`lab/agent-stores/language-agent-lab-v0`

## Smoke

```powershell
$env:AGENT_NOTES_KB = 'D:\experiments\agent-notes\knowledge'
.\scripts\run_exp_j_language_sync.ps1

python tools/sn_cen_infer.py --from-field --query "согласно приказу" `
  --store-dir lab/agent-stores/language-agent-lab-v0

python tools/bench_answer_recall.py `
  --queries lab/exp_j_ru_queries.jsonl `
  --store-dir lab/agent-stores/language-agent-lab-v0 `
  --out lab/exp_j_ru_v1/report.json
```

## Phase 2 — NCA train (modern union)

```powershell
.\scripts\run_exp_j_train.ps1          # smoke: 600 ep, 2 bundles (~10 min)
.\scripts\run_exp_j_train_full.ps1     # full: 1200 ep, grammar-only + curve s20 (~30–45 min)
.\scripts\run_exp_j_train_full.ps1 -Union   # 1200 ep, grammar + MRE3 union
```

| Run | Output |
|-----|--------|
| smoke | `nca_out_exp_j_ru_v1/model.pt` |
| full grammar | `nca_out_exp_j_ru_grammar_full_v1/model.pt`, `exp_j_ru_v1/curve_grammar_s20.json` |
| full union | `nca_out_exp_j_ru_union_full_v1/model.pt`, `curve_union_s20.json` |

Checkpoint: `language-agent-lab-v0/checkpoints/model_hard.pt`

## FPN + autonomous T (v0)

- Session: `agent_session.json` in store (`tools/fpn_state.py`)
- Tick loop: `.\scripts\run_exp_j_autonomous.ps1` or `python tools/agent_autonomous_tick.py --ticks N`
- Infer with session: `sn_cen_infer.py --from-field --session --query "..."`

## Scripts

| Script | Role |
|--------|------|
| `run_exp_j_language_sync.ps1` | KB sync + rebuild union |
| `run_exp_j_kb_watcher.ps1` | Living ingest |
| `run_exp_j_bench.ps1` | answer@k (+ repair if model) |
| `run_exp_j_train.ps1` | NCA train + benches |
| `run_exp_j_train_windowed.ps1` | Windowed NCA (tile + planner v0) |
| `run_exp_j_autonomous.ps1` | 3-tick FPN demo |

## Windowed field + planner v0 (2026-05-29)

Локальный NCA на **тайлах** DMN (32×32, stride 16, ghost 2); планировщик v0 взвешивает плотность токенов.

```powershell
.\scripts\run_exp_j_train_windowed.ps1              # grammar smoke
.\scripts\run_exp_j_train_windowed.ps1 -Union -Epochs 1200   # union full (batched)
```

Канон: [`windowed-field-and-planner-v0.md`](windowed-field-and-planner-v0.md), ablation: [`experiment-j-windows-ablation-v1.md`](experiment-j-windows-ablation-v1.md).  
Выход grammar: `nca_out_exp_j_ru_windowed_v1/`; union: `nca_out_exp_j_ru_union_windowed_v1/`, `curve_union_windowed_s20.json`, `compare_grammar_full_vs_union_windowed.json`.

## Data scale (2026-05-29)

| | Было | Стало |
|---|------|--------|
| claims (grammar bundle) | ~20 | **~89** |
| `claims_nav` (union store) | ~61 | **~134** |
| bench queries | 16 | **21** |

Расширение: KB §8–14 в agent-notes + `semantic_payload` (абзацы, предложения, таблицы).

## Metrics

- **answer@k** — `expect_substr` found in top answer_blocks
- **answer@k repair** — same after damage + NCA rollout
- **concept_id coverage** — share of claims with non-null id after `semantic_payload` v2
