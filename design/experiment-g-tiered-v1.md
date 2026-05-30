# Experiment G — tiered train (easy vs hard bundles)

**Date:** 2026-05-28  
**Hypothesis:** module-only train (F) helps **hard** bundles but hurts **easy** high-baseline bundles.  
**Policy:** easy → cluster DMN only; hard → cluster DMN + module finetune.

## Tiers

From `manifests/kb-bundle-tiers.v0.json` (baseline mix @ damage 0.4, threshold **0.85**):

| Tier | Train |
|------|--------|
| **easy** | Phase 1 only: `train_dmn_nca_multibundle` (full field) |
| **hard** | Phase 1 + Phase 2: `train_module_nca --hard-only --init-model` |

## Phases

1. **Phase 1** — 600 ep, all cluster bundles + reference (same as E).  
2. **Phase 2** — 200 ep, module-masked, **hard bundles only**, init from phase 1 `model.pt`, lr 1e-4.

Bench: union model, all bundles @ 0.4 (global, same as E/F).

## Scripts

- `tools/build_kb_bundle_tiers.py` — regenerate tiers from E bench  
- `tools/train_tiered_cluster.py` — run both phases per cluster  
- `tools/exp_g_tiered.py` — full experiment + report  
- `scripts/run_tiered_g_v0.ps1`

## Output

`examples/exp_g_tiered_v1/report.json` — compare to E and F via `tools/compare_exp_ef.py` (point F or G).
