# Experiment J — windows ablation v1

**Date:** 2026-05-29  
**Goal:** Same union vocab (162 tokens), vary parallel windows / tiling; compare quality and wall-clock.

## Fixed (all runs)

- Bundles: `kb-russian-language-rules-v1` + `kb-regex-mre3-ru-chapter-map-v1`
- Codec v3, `concept-mode section`, tile 32×32, ghost 2, canvas 36×36
- `damage-mode patches`, `damage-patches 6`, default epochs **400** (smoke: 120)

Union vocab size is determined by both bundles (~162 tokens on current store).

## Arms

| Arm | `windows_per_batch` | stride | Spatial tiles on DMN | Meaning |
|-----|---------------------|--------|----------------------|---------|
| **w1** | **1** | 16 | 3 | One crop per optimizer step (minimal GPU batch) |
| **w32** | **32** | 16 | 3 | Current sweet spot (~auto on 8GB) |
| **w48** | **48** | 16 | 3 | More parallel (may be slower on 8GB — sweep first) |
| **w32_s8** | **32** | **8** | **5** | More spatial overlap + same GPU batch |

## Not compared here

- **Monolithic 64×64** — hours on laptop; out of scope.
- **Matched total window steps** — w1 would need 32× epochs (~12800 for parity with w32@400); too long. We report **windows_seen = epochs × windows_per_batch** explicitly.

## Metrics

- `train_wall_sec`, `sec_per_epoch`, `best_mix` (windowed eval during train)
- `bench_windowed_repair` on grammar bundle: mix, concepts F1
- `report_repair_union_windowed.json` style answer@1 (optional, full script)

## Run

```powershell
.\scripts\run_exp_j_windows_ablation.ps1
.\scripts\run_exp_j_windows_ablation.ps1 -Epochs 120   # quick
```

Output: `examples/exp_j_ru_v1/windows_ablation_report.json`
