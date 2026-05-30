# Experiments A → B → C (v1 results)

**Date:** 2026-05-28  
**Scripts:** `scripts/run_experiments_abc_v1.ps1` · `tools/exp_a_kb_scale.py` · `exp_b_decode_sweep.py` · `exp_c_goal3_grid.py`

## A — KB scale (8 bundles + union train)

**Setup:** `examples/kb/*.bundle.v1.json`, v3/section, 1200 epochs, bench @ damage 0.4, 20 seeds.  
**Model:** `examples/exp_a_kb_scale_v1/model.pt`

### Summary

| Metric | Value |
|--------|-------|
| mean Δ mix F1 | **−0.0024** |
| NCA wins (mix) | **0 / 8** |

**Gate (mean Δ ≥ +0.03, all bundles win):** **not met**

### Interpretation

1. **Shared hub graph:** all KB bundles use the same `ca-substrate-agent.hub.graph.json` → identical edge tokens; baseline edge F1 already ~0.53; little room for NCA.
2. **Per-doc concepts** differ, but union vocab dilutes signal across 8 payloads on one layout.
3. **research-ml.bundle:** concepts F1 = 0 (no recoverable `concept_id` in payload vs graph) — metric artifact.

**Follow-up (A′):** union train **KB + 3 reference** bundles (800 ep) → `examples/exp_a_prime_kb_plus_ref_v1/`

| Metric | A (KB only) | A′ (KB + ref) |
|--------|-------------|---------------|
| mean Δ mix | −0.0024 | −0.0185 |
| NCA wins | 0/8 | **3/11** |

A′ не отменяет вывод A: масштабирование на hub-graph bundle без отдельных graph per doc даёт потолок; reference bundles помогают частично.

Artifacts: `examples/exp_a_kb_scale_v1/`, `examples/exp_a_prime_kb_plus_ref_v1/`

---

## B — Decode sweep (threshold / min_votes)

**Damage:** 0.4 · **Recommended:** `threshold=0.35`, `min_votes=2` (mode across bundles)

| Model | Bundles | Best mix F1 (example) |
|-------|---------|------------------------|
| `exp_a_kb_scale_v1` | kb casa-goals, playbook | ~0.77 |
| `nca_out_v3_section` | ca-substrate | **0.738** (was ~0.69 @ 0.5/3) |
| `nca_out_v3_section` | research-spec | **0.80** |

Defaults updated in `tools/canonical.py`: `CANONICAL_THRESHOLD`, `CANONICAL_MIN_VOTES`.

Artifacts: `examples/exp_b_decode_sweep_v1/`, `examples/exp_b_decode_sweep_v1/ref/`

---

## C — Goal 3 repair grid

**Setup:** `ca-substrate-agent.bundle.v1.json`, model `nca_out_v3_section`, patches ∈ {6,8,10,12} × 20 seeds.

See `examples/exp_c_goal3_grid_v1/report.json` for `win_rate` and `patch_summary`.

**Gate (≥50% seeds with repair > error):** **met** — `win_rate` **71.25%** (57/80).

| Patches | Win rate | mean Δ concepts | mean Δ edges |
|---------|----------|-----------------|--------------|
| 6 | 50% | +0.061 | +0.059 |
| 8 | 55% | +0.071 | +0.074 |
| 10 | 85% | +0.123 | +0.127 |
| 12 | 95% | +0.155 | +0.160 |

Stronger agent-error (more patches) → clearer NCA repair signal (CASA goal 3).

---

## D — Per-doc graphs (follow-up)

**Hypothesis:** shared hub graph caused A failure; each KB doc gets its own `extract_md_graph` root.

**Run:** `python tools/exp_d_kb_perdoc.py` → bundles in `examples/kb-perdoc/`, report `examples/exp_d_kb_perdoc_v1/report.json`

### D results (2026-05-28)

| Metric | A (hub) | D (per-doc) |
|--------|---------|-------------|
| mean Δ mix @0.4 | −0.002 | **−0.011** (union larger) |
| NCA wins | 0/8 | **6/10** |

Per-doc graphs **help per bundle** (6 wins vs 0), but union vocab + shared DMN still drags mean Δ. Gate (+0.03 all-win) **not met** — next: per-doc train or fewer bundles per union.

---

## F — Module parcels (fMRI-style)

**Hypothesis:** within a cluster, train with **module-local** damage + spatial loss on `(doc_path, section)` parcels.

**Run:** `python tools/build_kb_modules.py` → `manifests/kb-modules.v0.json` · `scripts/run_modules_v0.ps1`

See `design/modules-fmri-analogy-v0.md` · output `examples/exp_f_modules_v1/report.json`

---

## G — Tiered train (easy vs hard bundles)

**Policy:** baseline_mix ≥ 0.85 → cluster DMN only; else cluster + module finetune.

**Run:** `scripts/run_tiered_g_v0.ps1` → `examples/exp_g_tiered_v1/report.json`

See `design/experiment-g-tiered-v1.md` · `manifests/kb-bundle-tiers.v0.json`

---

## Repo

https://github.com/AI-Guiders/casa-ontology-payload
