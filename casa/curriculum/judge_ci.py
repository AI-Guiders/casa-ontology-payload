#!/usr/bin/env python3
"""Bootstrap confidence intervals for the headline NUN-Bench metrics.

A single point estimate on 635 records won't survive review — «kernel 0.452 zero-risk vs
LLM 0.41» and «FPR 0.000 vs 0.11» need intervals. We resample the per-item results with
replacement (paired bootstrap over benchmark items) and recompute each metric on every
resample; the reported CI is the 2.5/97.5 percentile band over B resamples.

Metrics bootstrapped per judge: recall (caught / injected errors, on answered items), FPR
(false alarms / controls), precision, answered rate, and the zero-risk coverage operating
point (the longest margin-ranked all-correct prefix as a fraction of all items — the
paper's key number). The bootstrap is seeded, so the intervals are reproducible.
"""

from __future__ import annotations

import random
from typing import Any

from casa.curriculum.judge_metrics import _aggregate


def _per_item(truth: dict, judgments: dict[str, list[dict]]) -> list[dict]:
    """One flat record per benchmark item: label, majority verdict, correctness, margin.
    A list (not a dict) so the bootstrap can resample WITH replacement (duplicate items)."""
    out = []
    for i, recs in judgments.items():
        if i not in truth:
            continue
        a = _aggregate(recs)
        answered = a["verdict"] != "abstain"
        is_error = truth[i]["label"] == "error"
        out.append({
            "id": i, "is_error": is_error, "answered": answered,
            "says_error": a["verdict"] == "error",
            "correct": answered and (a["verdict"] == "error") == is_error,
            "margin": a["margin"], "confidence": a["confidence"],
        })
    return out


def _metrics(items: list[dict]) -> dict[str, float | None]:
    """Point metrics from a (possibly resampled) item list."""
    n = len(items)
    answered = [r for r in items if r["answered"]]
    errors = [r for r in answered if r["is_error"]]
    controls = [r for r in answered if not r["is_error"]]
    caught = [r for r in errors if r["says_error"]]
    fa = [r for r in controls if r["says_error"]]

    # zero-risk coverage: longest all-correct prefix in margin-desc order, over ALL items
    ranked = sorted(answered, key=lambda r: (-r["margin"], -r["confidence"], r["id"]))
    prefix = 0
    for r in ranked:
        if r["correct"]:
            prefix += 1
        else:
            break
    return {
        "answered": len(answered) / n if n else None,
        "recall": len(caught) / len(errors) if errors else None,
        "fpr": len(fa) / len(controls) if controls else None,
        "precision": len(caught) / (len(caught) + len(fa)) if (caught or fa) else None,
        "zero_risk_coverage": prefix / n if n else None,
    }


def _percentile(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    if not xs:
        return float("nan")
    k = (len(xs) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def bootstrap_ci(truth_rows: list[dict], judgments: dict[str, list[dict]], *,
                 n_boot: int = 2000, seed: int = 20260703,
                 alpha: float = 0.05) -> dict[str, Any]:
    """Point estimate + percentile CI for each headline metric of one judge."""
    truth = {r["id"]: r for r in truth_rows}
    items = _per_item(truth, judgments)
    point = _metrics(items)

    rng = random.Random(seed)
    n = len(items)
    draws: dict[str, list[float]] = {k: [] for k in point}
    for _ in range(n_boot):
        sample = [items[rng.randrange(n)] for _ in range(n)]
        m = _metrics(sample)
        for k, v in m.items():
            if v is not None:
                draws[k].append(v)

    out = {}
    for k, v in point.items():
        band = draws[k]
        out[k] = {
            "point": round(v, 4) if v is not None else None,
            "lo": round(_percentile(band, alpha / 2), 4) if band else None,
            "hi": round(_percentile(band, 1 - alpha / 2), 4) if band else None,
        }
    out["_n_items"] = n
    out["_n_boot"] = n_boot
    return out


def _fmt(ci: dict) -> str:
    if ci.get("point") is None:
        return "—"
    return f"{ci['point']:.3f} [{ci['lo']:.3f}, {ci['hi']:.3f}]"


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    from pathlib import Path

    from casa.curriculum.judge import load_benchmark
    from casa.curriculum.judge_metrics import load_judgments
    from casa.curriculum.render import ensure_utf8_console

    ensure_utf8_console()
    ap = argparse.ArgumentParser(description="Bootstrap CIs for NUN-Bench headline metrics.")
    ap.add_argument("--bench", default="lab/nunbench/v0.1.2/nunbench-v0.1.2-public.jsonl")
    ap.add_argument("--judgments-dir", default=".scratch/judgments-v0.1.2")
    ap.add_argument("--split", default="public", choices=["public", "heldout", "all"])
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args(argv)

    rows = load_benchmark(args.bench, split=args.split)
    groups = load_judgments(sorted(Path(args.judgments_dir).glob("*.jsonl")))
    results = {}
    for (model, prompt), judged in sorted(groups.items()):
        name = model if prompt == "kernel" else f"{model} [{prompt}]"
        results[name] = bootstrap_ci(rows, judged, n_boot=args.n_boot)

    cols = ["recall", "fpr", "precision", "answered", "zero_risk_coverage"]
    print("| judge | " + " | ".join(cols) + " |")
    print("|" + "---|" * (len(cols) + 1))
    for name in sorted(results):
        r = results[name]
        print("| " + name + " | " + " | ".join(_fmt(r[c]) for c in cols) + " |")
    print(f"\n95% percentile CI, {args.n_boot} bootstrap resamples over "
          f"{next(iter(results.values()))['_n_items']} items.")
    if args.out_json:
        Path(args.out_json).write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
        print(f"→ {args.out_json}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
