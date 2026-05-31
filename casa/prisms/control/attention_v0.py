#!/usr/bin/env python3
"""Top-down attention spotlight for control-attention (CASA-ADR-0010, R4).

DAN answers: *which* concepts / shards / lattice regions to amplify on this tick.
SN keeps bottom-up salience (including prediction error via P8); DAN is the
goal-driven projector from FPN (P6) that yields a sparse mask for read/rollout
(P7 → DMN / L2 / predict).

Digest-level v0 — deterministic, testable without CUDA. Field realization stamps
`dan.spotlight.*` tokens on `lattice_dan` and applies the mask before windowed
NCA rollout.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Callable, Iterable

from casa.prisms.control import predict_v0 as lp


def as_set(items: Iterable[str] | None) -> set[str]:
    return lp.as_digest(items)


def spotlight(
    goal: Iterable[str],
    universe: Iterable[str],
    *,
    salience: Iterable[str] | None = None,
    min_keep: int = 1,
) -> set[str]:
    """Build a top-down mask: goal ∩ universe, plus salient concepts, plus goal stem neighbors."""
    g = as_set(goal)
    u = as_set(universe)
    s = as_set(salience) if salience else set()
    mask = (g & u) | (s & u)

    for concept in g:
        stem = concept.rsplit(".", 1)[0] if "." in concept else concept
        for c in u:
            if c.startswith(stem):
                mask.add(c)

    if len(mask) < min_keep and u:
        mask |= set(sorted(u)[: min(min_keep, len(u))])
    return mask


def apply_mask(digest: Iterable[str], mask: Iterable[str]) -> set[str]:
    """Sparse read: digest filtered by DAN spotlight."""
    return as_set(digest) & as_set(mask)


def sparse_ratio(full: Iterable[str], mask: Iterable[str]) -> float:
    """Fraction of digest concepts kept — lower means sparser compute."""
    f = as_set(full)
    if not f:
        return 0.0
    return len(apply_mask(f, mask)) / len(f)


def evaluate_spotlight(
    trajectory: list[Iterable[str]],
    *,
    goal_at: Callable[[set[str], int], set[str]] | None = None,
) -> dict:
    """Walk a trajectory; spotlight from FPN goal against accumulated memory universe."""
    digests = [as_set(d) for d in trajectory]
    ratios: list[float] = []
    kept_errors: list[float] = []
    model = lp.fit_transitions(digests)
    memory: set[str] = set()

    for i, cur in enumerate(digests[:-1]):
        nxt = digests[i + 1]
        memory |= cur | nxt
        goal = nxt if goal_at is None else goal_at(nxt, i)
        mask = spotlight(goal, memory, salience=cur)
        ratios.append(sparse_ratio(memory, mask))
        sparse_cur = apply_mask(cur, mask)
        pred = lp.predict_next(sparse_cur, model)
        kept_errors.append(lp.prediction_error(pred, nxt))

    mean_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    mean_err = sum(kept_errors) / len(kept_errors) if kept_errors else 0.0
    return {
        "steps": len(ratios),
        "mean_sparse_ratio": round(mean_ratio, 4),
        "mean_error_under_mask": round(mean_err, 4),
        "sparse_enough": mean_ratio < 0.85,
        "still_predictive": mean_err < 0.5,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="lattice_dan spotlight (CASA-ADR-0010 R4)")
    p.add_argument("--trajectory", type=Path, default=None, help='json {"trajectory": [...]}')
    args = p.parse_args()

    if args.trajectory:
        data = json.loads(args.trajectory.read_text(encoding="utf-8"))
        traj = data.get("trajectory") or []
    else:
        from casa.cli.bench.bench_predict_error_v0 import synthetic_trajectory

        traj = synthetic_trajectory()

    report = evaluate_spotlight(traj)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["sparse_enough"] and report["still_predictive"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
