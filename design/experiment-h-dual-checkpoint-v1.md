# Experiment H — dual checkpoint inference

**Date:** 2026-05-28  
**Motivation:** G phase2 on hard bundles improves `research-ml` but degrades easy bundles in the **same** `model.pt`.

## Policy

| Tier | Checkpoint at bench |
|------|---------------------|
| easy | `model_phase1.pt` (after cluster train only) |
| hard | `model_hard.pt` (after module finetune) |

Train (`train_tiered_cluster.py`) now saves both files.  
Bench-only replay: `tools/exp_h_dual_checkpoint_bench.py` on existing G weights (phase1 fallback = E cluster model).

## Run

```powershell
python tools/exp_h_dual_checkpoint_bench.py
```

Output: `examples/exp_h_dual_bench_v1/report.json`

## Expected

- goals/ops ≈ G easy path (same as E)
- research: `research-ml` strong (hard ckpt) + tda-flow/training ≈ E (phase1 ckpt)
