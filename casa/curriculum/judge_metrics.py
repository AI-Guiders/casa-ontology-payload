#!/usr/bin/env python3
"""NUN-Bench metrics — from raw judge verdicts to the paper's tables, no hand-edited numbers.

Consumes the JSONL files ``judge`` writes (one per model × run) plus the frozen benchmark
(ground truth), and emits every reported number in one deterministic pass:

  recall per error class — is the dangerous error caught at all (binary), and is it named
                           as the right class (exact);
  FPR / precision        — false alarms on untouched controls;
  consistency@k          — unanimity across the k same-temperature runs, plus mean
                           pairwise agreement (the stability story);
  risk–coverage          — sweep the vote-margin threshold: answer only when the judge is
                           self-consistent enough, abstain otherwise. The kernel enters
                           the same curve through its NATIVE abstention (uncheckable) —
                           that single honest point is the thesis of the paper;
  cost/latency           — tokens and wall-time per verdict.

Verdict aggregation is majority vote over valid runs; «invalid» replies never vote and
an all-invalid item counts as abstention (reported, not hidden).
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

CLASSES = ("polarity", "quantity", "unit", "entity")


def load_judgments(paths: list[str | Path]) -> dict[tuple[str, str], dict[str, list[dict]]]:
    """Group raw records by (model, prompt_version) → id → [runs]."""
    groups: dict[tuple[str, str], dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for p in paths:
        with Path(p).open(encoding="utf-8") as f:
            for ln in f:
                if ln.strip():
                    r = json.loads(ln)
                    groups[(r["model"], r["prompt_version"])][r["id"]].append(r)
    return groups


def _aggregate(recs: list[dict]) -> dict[str, Any]:
    """Majority vote across runs; margin = how lopsided the vote was (0 = split, 1 = all)."""
    valid = [r for r in recs if r["verdict"] in ("equivalent", "error")]
    if not valid:
        return {"verdict": "abstain", "error_class": None, "margin": 0.0, "confidence": 0.0,
                "n_valid": 0, "unanimous": False}
    err = [r for r in valid if r["verdict"] == "error"]
    # tie-break toward «error»: for a safety validator the costly miss is the false pass
    says_error = bool(err) and len(err) * 2 >= len(valid)
    side = err if says_error else [r for r in valid if r["verdict"] == "equivalent"]
    klass = None
    if says_error:  # the most-voted class among error votes
        counts = defaultdict(int)
        for r in err:
            counts[r["error_class"] or "other"] += 1
        klass = max(sorted(counts), key=lambda k: counts[k])
    return {
        "verdict": "error" if says_error else "equivalent", "error_class": klass,
        "margin": abs(2 * len(err) - len(valid)) / len(valid),
        "confidence": sum(r["confidence"] for r in side) / len(side),
        "n_valid": len(valid),
        "unanimous": len({r["verdict"] for r in valid}) == 1,
    }


def evaluate(truth_rows: list[dict], judgments: dict[str, list[dict]]) -> dict[str, Any]:
    """All metrics for one judge over one benchmark split."""
    truth = {r["id"]: r for r in truth_rows}
    agg = {i: _aggregate(rs) for i, rs in judgments.items() if i in truth}
    scored = list(agg.items())
    answered = [(i, a) for i, a in scored if a["verdict"] != "abstain"]

    def correct(i: str, a: dict) -> bool:
        return (a["verdict"] == "error") == (truth[i]["label"] == "error")

    errors = [(i, a) for i, a in answered if truth[i]["label"] == "error"]
    controls = [(i, a) for i, a in answered if truth[i]["label"] == "equivalent"]
    caught = [(i, a) for i, a in errors if a["verdict"] == "error"]
    false_alarms = [(i, a) for i, a in controls if a["verdict"] == "error"]

    per_class: dict[str, Any] = {}
    for k in CLASSES:
        k_err = [(i, a) for i, a in errors if truth[i]["error_class"] == k]
        k_caught = [(i, a) for i, a in k_err if a["verdict"] == "error"]
        per_class[k] = {
            "n": len(k_err),
            "recall": round(len(k_caught) / len(k_err), 4) if k_err else None,
            "exact_class": round(sum(1 for i, a in k_caught if a["error_class"] == k)
                                 / len(k_caught), 4) if k_caught else None,
        }

    # risk–coverage: answer only above a vote-margin threshold, abstain below
    ranked = sorted(answered, key=lambda ia: (-ia[1]["margin"], -ia[1]["confidence"], ia[0]))
    curve, seen_cov = [], set()
    for cut in range(len(ranked), 0, -1):
        cov = round(cut / len(scored), 4) if scored else 0.0
        if cov in seen_cov:
            continue
        seen_cov.add(cov)
        take = ranked[:cut]
        risk = round(sum(0 if correct(i, a) else 1 for i, a in take) / len(take), 4)
        curve.append({"coverage": cov, "risk": risk})
    curve.reverse()

    n_runs = max((len(rs) for rs in judgments.values()), default=0)
    multi = [a for _, a in scored if a["n_valid"] >= 2]
    all_recs = [r for rs in judgments.values() for r in rs]
    n_err_all = sum(1 for i, _ in scored if truth[i]["label"] == "error")
    n_ctl_all = sum(1 for i, _ in scored if truth[i]["label"] == "equivalent")
    return {
        "items": len(scored),
        "runs": n_runs,
        "answered": round(len(answered) / len(scored), 4) if scored else 0.0,
        # coverage is label-skewed for an abstaining judge (injections are parseable by
        # construction, controls are wild text) — report it, don't let a table hide it
        "answered_by_label": {
            "error": round(len(errors) / n_err_all, 4) if n_err_all else None,
            "equivalent": round(len(controls) / n_ctl_all, 4) if n_ctl_all else None,
        },
        "recall": round(len(caught) / len(errors), 4) if errors else None,
        "fpr": round(len(false_alarms) / len(controls), 4) if controls else None,
        "precision": round(len(caught) / (len(caught) + len(false_alarms)), 4)
                     if caught or false_alarms else None,
        "per_class": per_class,
        "consistency": {
            "unanimous": round(sum(a["unanimous"] for a in multi) / len(multi), 4) if multi else None,
            "n_multi_run": len(multi),
        },
        "invalid_rate": round(sum(1 for r in all_recs
                                  if r["verdict"] not in ("equivalent", "error", "abstain"))
                              / len(all_recs), 4) if all_recs else 0.0,
        "risk_coverage": curve,
        "cost": {
            "tokens_in": sum(r.get("tokens_in", 0) for r in all_recs),
            "tokens_out": sum(r.get("tokens_out", 0) for r in all_recs),
            "mean_latency_ms": round(sum(r.get("latency_ms", 0) for r in all_recs)
                                     / len(all_recs), 1) if all_recs else 0.0,
        },
    }


def _fmt(x: Any) -> str:
    return "—" if x is None else f"{x:.3f}" if isinstance(x, float) else str(x)


def results_table(results: dict[str, dict[str, Any]]) -> str:
    """The main results table, markdown — one row per judge."""
    head = ("| judge | answered | ans:err | ans:ctl | recall | FPR | precision | "
            + " | ".join(f"R:{k[:3]}" for k in CLASSES) + " | consist@k | invalid |")
    sep = "|" + "---|" * (9 + len(CLASSES))
    lines = [head, sep]
    for name in sorted(results):
        m = results[name]
        by = m["answered_by_label"]
        cells = [name, _fmt(m["answered"]), _fmt(by["error"]), _fmt(by["equivalent"]),
                 _fmt(m["recall"]), _fmt(m["fpr"]), _fmt(m["precision"])]
        cells += [_fmt(m["per_class"][k]["recall"]) for k in CLASSES]
        cells += [_fmt(m["consistency"]["unanimous"]), _fmt(m["invalid_rate"])]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse

    from casa.curriculum.judge import load_benchmark
    from casa.curriculum.render import ensure_utf8_console

    ensure_utf8_console()
    ap = argparse.ArgumentParser(description="Compute NUN-Bench metrics from raw judgments.")
    ap.add_argument("--bench", default=".scratch/opus/nunbench-v0.1.jsonl")
    ap.add_argument("--judgments-dir", default=".scratch/judgments")
    ap.add_argument("--split", default="public", choices=["public", "heldout", "all"])
    ap.add_argument("--out-json", default=None, help="write full metrics (incl. curves) here")
    args = ap.parse_args(argv)

    rows = load_benchmark(args.bench, split=args.split)
    files = sorted(Path(args.judgments_dir).glob("*.jsonl"))
    if not files:
        print(f"no judgment files in {args.judgments_dir}")
        return 2
    groups = load_judgments(files)
    results = {f"{model} [{prompt}]" if prompt not in ("kernel",) else model:
               evaluate(rows, judged)
               for (model, prompt), judged in sorted(groups.items())}

    print(results_table(results))
    if args.out_json:
        Path(args.out_json).write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nfull metrics → {args.out_json}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
