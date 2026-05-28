# Modules (fMRI-style parcellation) v0

**Status:** design + lab scaffold (Experiment F)  
**Date:** 2026-05-28  
**Prerequisites:** `kb-perdoc` bundles, `manifests/kb-clusters.v0.json`, codec **v3 + section**, Experiment E cluster checkpoints (optional baseline).

## Analogy

| fMRI / neuroscience | CASA field |
|---------------------|------------|
| Large-scale network (DMN, SN, CEN) | Layout region (`dmn_ontology`, …) |
| Resting-state cluster (goals, research, ops) | `kb-clusters.v0.json` → shared trunk vocab + train pool |
| **Parcel / task-positive ROI** | **Module** = `(doc_path, section)` activation on grid |
| BOLD time series | Micro-steps `t` within phase `z` |
| Task run (sparse ROIs) | Infer: damage/query activates **subset of modules** only |

Clusters answer *which vocabulary and prior*. Modules answer *where on (x,y) and which tokens* get repair for this document slice.

## Module identity

```
module_id = {cluster}/{bundle_stem}/{section_slug}
section_key = {doc_path}|{section}   # same as codec_grid_v3 S: hub
```

Generated manifest: `manifests/kb-modules.v0.json` via `tools/build_kb_modules.py`.

## Training v0 (shared trunk + module masks)

1. **One `UpdateRule` per cluster** (union token_ids across cluster bundles + reference bundles).
2. Each batch sample picks `(bundle, module)` from manifest.
3. **Damage** only in cells belonging to that module (∩ DMN rect), patch mode.
4. **Loss** weighted by spatial module mask on token channels (MSE × mask).

This is not N separate full models yet — it is **one CA with module-local supervision** (fMRI: same anatomy, different activation patterns).

## Inference v0 (sparse activation)

1. Encode full bundle → grid.
2. For each module in bundle: build cell mask; score patch damage **inside mask**.
3. Run NCA (full field state, same rule).
4. Report **modules_activated** = modules where damage overlap ≥ threshold.

Optional later: restrict rollout spatial mask to union of active modules (SN gate).

## Metrics

| Metric | Meaning |
|--------|---------|
| `delta_mix` per bundle | Same as E (0.6·c + 0.4·e F1) |
| `modules_per_bundle` | Parcel count |
| `mean_patch_overlap` | How localized damage was |
| Per-module bench | Win rate when only that parcel is damaged |

## Known limits

- Claims with `concept_id: null` produce **no `C:` token** — module may be hub/edges-only; fix payload or synthetic ids in a later pass.
- Many modules per cluster → thin data; v0 keeps **shared trunk**, module masks only reweight loss.
- Fail modules (e.g. research-ml): check graph↔claim alignment before adding per-module heads.

## GPU training

Train scripts use `tools/nca_train_util.py`:

- **Auto batch:** 64 on CUDA, 8 on CPU (`--batch-size 0`)
- **AMP** on CUDA by default (`--no-amp` to disable)
- **Targets + patch damage on GPU** (no per-step Python grid→tensor loop)
- cudnn benchmark + TF32 on NVIDIA

Example: `python tools/train_module_nca.py --cluster research --batch-size 128 --save-model --out-dir ...`

## Code

| File | Role |
|------|------|
| `tools/nca_train_util.py` | Device, AMP, GPU damage, fast scatter |
| `tools/build_kb_modules.py` | Regenerate `kb-modules.v0.json` |
| `tools/module_masks.py` | Tokens + cell masks per `(bundle, section_key)` |
| `tools/train_module_nca.py` | Cluster trunk, module-weighted train |
| `tools/exp_f_modules.py` | Experiment F train + bench |
| `scripts/run_modules_v0.ps1` | One-shot lab run |

## Experiment F output

`examples/exp_f_modules_v1/{cluster}/model.pt`, `report.json`, per-bundle `bench_*.json`.

Compare to E: same clusters, module-local damage + loss; expect better signal on weak bundles if parcels separate conflicting hubs.

## Repo

https://github.com/AI-Guiders/casa-ontology-payload
