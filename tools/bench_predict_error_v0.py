#!/usr/bin/env python3
"""Gate: lattice_predict rollout beats the no-rollout baseline (CASA-ADR-0010 R3).

Criterion (ADR-0010, R3): the predicted next-digest must be closer to the
observed next-digest than the no-rollout baseline (persistence). Deterministic,
CI-friendly like test_predictor_smoke; exits non-zero when predict fails to win.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import predict_tick_v0 as pt


def synthetic_trajectory(n_ticks: int = 60, n_topics: int = 8, seed: int = 7) -> list[list[str]]:
    """A learnable topic-walk: the active topic advances each tick.

    Persistence cannot win because the digest changes almost every tick, but the
    transition (topic_i -> topic_{i+1}) is stationary and learnable. A stable
    'detail' concept appears with low probability to keep digests >1 concept.
    """
    rng = random.Random(seed)
    topics = [f"topic.{i}" for i in range(n_topics)]
    trajectory: list[list[str]] = []
    for t in range(n_ticks):
        topic = topics[t % n_topics]
        digest = [f"{topic}.core"]
        if rng.random() < 0.3:
            digest.append(f"{topic}.detail")
        trajectory.append(sorted(digest))
    return trajectory


def run(trajectory: list, *, train_frac: float = 0.7, top: int = 1) -> dict:
    digests = [pt.as_digest(d) for d in trajectory]
    split = max(2, int(len(digests) * train_frac))
    model = pt.fit_transitions(digests[:split])
    held_out = digests[split - 1:]
    predict_eval = pt.evaluate(held_out, model, predictor=pt.predict_next, top=top)
    baseline_eval = pt.evaluate(held_out, model, predictor=pt.predict_persistence, top=top)
    return {
        "transitions_eval": predict_eval["transitions"],
        "predict_mean_error": round(predict_eval["mean_error"], 4),
        "baseline_mean_error": round(baseline_eval["mean_error"], 4),
        "predict_total_surprise": predict_eval["total_surprise"],
        "improved": predict_eval["mean_error"] < baseline_eval["mean_error"],
    }


def main() -> int:
    p = argparse.ArgumentParser(description="lattice_predict error bench (CASA-ADR-0010 R3)")
    p.add_argument("--trajectory", type=Path, default=None, help='json {"trajectory": [[concept_id,...], ...]}')
    p.add_argument("--train-frac", type=float, default=0.7)
    p.add_argument("--top", type=int, default=1)
    args = p.parse_args()

    if args.trajectory:
        data = json.loads(args.trajectory.read_text(encoding="utf-8"))
        trajectory = data.get("trajectory") or []
    else:
        trajectory = synthetic_trajectory()

    report = run(trajectory, train_frac=args.train_frac, top=args.top)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["improved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
