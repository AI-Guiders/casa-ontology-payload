# Windowed field + spatial planner v0

**Status:** implemented (lab v0)  
**Date:** 2026-05-29  
**See also:** [`casa-layout-v0.md`](casa-layout-v0.md), [`experiment-j-text-modality-v1.md`](experiment-j-text-modality-v1.md)

## Problem

NCA rules are **local** (3×3 perception). Training on the full 64×64 canvas every step is slow and wastes capacity on empty margin. Large KB layouts will not fit one rect — we need **tiling** without breaking the same stencil at inference.

## Idea

| Layer | Role |
|-------|------|
| **NCA (physics)** | Same `UpdateRule`; runs on a **crop** (tile + ghost margin). |
| **Window** | `Tile` = axis-aligned rectangle on the field; crops use **ghost cells** for stencil context. |
| **Planner v0** | Schedules which tiles to train/repair (density-weighted coverage). |
| **Merge** | Overlapping tiles: weighted paste (distance-to-center) at inference. |

Monolithic 64×64 training remains valid; windowed mode is an **alternate train/repair path**, not a new codec.

## Contracts

### Tile

```text
Tile { x0, y0, w, h, id? }
```

Tiles are generated over a layout `Rect` with `(tile_w, tile_h)` and stride `< size` for overlap.

### Ghost

`ghost` ≥ 1 (default **2**): extra border read from the global tensor, not included in loss. Sobel 3×3 needs at least 1; we use 2 for stability.

### Loss

MSE (or weighted MSE) is multiplied by `loss_mask` = 1 only on the **interior** tile pixels inside the crop.

### Planner v0 (`field_planner_v0.py`)

- **Train:** `sample_train_tiles(n, epoch, seed)` — weighted by token activation density in each tile (more signal where the bundle is dense).
- **Repair:** `repair_order()` — descending density, then raster tie-break (deterministic).

Future: hook SN salience / FPN goals into tile priority (v1).

## Batched windows (v0.1, 2026-05-29)

All window crops are **fixed canvas** `tile + 2×ghost` (default 36×36), zero-padded — one `nca_rollout` on `[B,C,H,W]`.

| Flag | Default | Meaning |
|------|---------|---------|
| `--windows-per-batch` | `0` (auto) | Parallel crops per optimizer step (~48 on 8GB vs 24 full-field) |
| `--batch-size` | unused in windowed train | Use `windows-per-batch` instead |

Repair: all planner tiles in **one** `nca_rollout_eval` batch when `len(tiles)>1`.

## Code map

| File | Purpose |
|------|---------|
| `tools/field_window.py` | `Tile`, tiling, `extract_window_crop`, loss mask, merge paste |
| `tools/field_planner_v0.py` | `FieldPlannerV0` |
| `tools/train_dmn_nca_windowed.py` | Batched windowed multibundle train |
| `tools/repair_dmn_nca_windowed.py` | Batched sliding repair + merge |
| `tools/bench_windowed_repair.py` | Monolithic vs windowed F1 |
| `scripts/run_exp_j_train_windowed.ps1` | Smoke train + bench |

## Smoke

```powershell
.\scripts\run_exp_j_train_windowed.ps1
```

Outputs: `examples/nca_out_exp_j_ru_windowed_v1/`, `examples/exp_j_ru_v1/report_windowed_repair.json`.

## When to enable full union

1. Windowed smoke F1 ≥ monolithic smoke on grammar bundle (same seeds).  
2. No seam regression on `bench_windowed_repair` overlap grid.  
3. **Production default:** `run_exp_j_train_windowed.ps1 -Union -Epochs 1200` (~15 min on RTX 4060 8GB).

**Do not** rely on monolithic `train_dmn_nca_multibundle` union 1200 for laptops — full 64×64 × 1200 ep is often **hours** and was interrupted by OS updates. Fair vocab compare with monolith only if `nca_out_exp_j_ru_union_full_v1/model.pt` already exists (`-TrainMonolith` to opt in).

## Non-goals (v0)

- Multi-GPU tile sharding  
- Learned planner (RL)  
- Cross-tile edge consistency loss (only overlap blend at decode)
