#!/usr/bin/env python3
"""Digest-level forward model for control-predict (CASA-ADR-0010, R3).

DMN answers "what we know"; control-predict answers "what we expect next".
understanding-contract makes the predict loop an invariant: roll the model
forward, compare to what actually arrives, and feed the mismatch (prediction
error) back as bottom-up surprise (bridge P8 -> SN).

This module is the first, field-agnostic brick of that organ. It works on
*digests* (a tick's set of concept_ids) instead of the raw NCA grid, so it is
deterministic and testable without CUDA. The eventual field realization rolls
the same CA rule k steps (train_memory_nca --lattice-id lattice_predict); the
contract here -- expected next-digest + error + surprise -- stays the same.

A digest is an iterable of concept_id strings. A trajectory is a list of
digests over macro ticks T.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable


def as_digest(items: Iterable[str] | None) -> set[str]:
    """Normalize an iterable of concept_ids into a clean set."""
    return {str(c).strip() for c in (items or []) if str(c).strip()}


def fit_transitions(trajectory: list[Iterable[str]]) -> dict[str, Any]:
    """Learn successor counts c -> Counter(next-digest concepts) from pairs.

    Pure: no state, no IO. The model is a plain dict so it serializes to JSON.
    """
    succ: dict[str, Counter] = defaultdict(Counter)
    seen: Counter = Counter()
    digests = [as_digest(d) for d in trajectory]
    for cur, nxt in zip(digests, digests[1:]):
        for c in cur:
            succ[c].update(nxt)
            seen[c] += 1
    return {"succ": {c: dict(ctr) for c, ctr in succ.items()}, "seen": dict(seen)}


def predict_next(current: Iterable[str], model: dict, *, top: int = 1) -> set[str]:
    """Expected next-digest: the `top` likeliest successors of each current concept.

    Deterministic tie-break: higher count first, then concept_id ascending.
    """
    succ = model.get("succ", {})
    predicted: set[str] = set()
    for c in as_digest(current):
        ctr = succ.get(c)
        if not ctr:
            continue
        ranked = sorted(ctr.items(), key=lambda kv: (-int(kv[1]), kv[0]))
        for concept, _count in ranked[: max(1, top)]:
            predicted.add(concept)
    return predicted


def rollout(current: Iterable[str], model: dict, *, steps: int = 1, top: int = 1) -> set[str]:
    """Apply predict_next k times to get the expected digest after `steps` ticks."""
    state = as_digest(current)
    for _ in range(max(1, steps)):
        nxt = predict_next(state, model, top=top)
        if not nxt:
            break
        state = nxt
    return state


def predict_persistence(current: Iterable[str], model: dict | None = None, **_: Any) -> set[str]:
    """No-rollout baseline: expect the world to stay exactly as it is."""
    return as_digest(current)


def f1(predicted: Iterable[str], observed: Iterable[str]) -> float:
    """Set F1 between expected and observed digests. Two empty sets score 1.0."""
    p = as_digest(predicted)
    o = as_digest(observed)
    if not p and not o:
        return 1.0
    inter = len(p & o)
    if inter == 0:
        return 0.0
    prec = inter / len(p)
    rec = inter / len(o)
    return 2 * prec * rec / (prec + rec)


def prediction_error(predicted: Iterable[str], observed: Iterable[str]) -> float:
    """1 - F1 in [0, 1]; 0 means a perfect expectation."""
    return 1.0 - f1(predicted, observed)


def surprise(predicted: Iterable[str], observed: Iterable[str]) -> set[str]:
    """Observed concepts that were NOT expected -> bottom-up salience for SN (bridge P8)."""
    return as_digest(observed) - as_digest(predicted)


def evaluate(
    trajectory: list[Iterable[str]],
    model: dict,
    *,
    predictor: Callable[..., set[str]] = predict_next,
    top: int = 1,
) -> dict[str, Any]:
    """Mean one-step prediction error and total surprise over a trajectory."""
    digests = [as_digest(d) for d in trajectory]
    errors: list[float] = []
    total_surprise = 0
    for cur, nxt in zip(digests, digests[1:]):
        pred = predictor(cur, model, top=top)
        errors.append(prediction_error(pred, nxt))
        total_surprise += len(surprise(pred, nxt))
    mean_error = sum(errors) / len(errors) if errors else 0.0
    return {"transitions": len(errors), "mean_error": mean_error, "total_surprise": total_surprise}


def main() -> int:
    p = argparse.ArgumentParser(description="lattice_predict digest forward-model (CASA-ADR-0010 R3)")
    p.add_argument("--trajectory", required=True, type=Path, help='json {"trajectory": [[concept_id,...], ...]}')
    p.add_argument("--train-frac", type=float, default=0.7, help="prefix fraction used to fit the model")
    p.add_argument("--top", type=int, default=1, help="successors kept per current concept")
    p.add_argument("--steps", type=int, default=1, help="rollout horizon for the trailing digest")
    args = p.parse_args()

    data = json.loads(args.trajectory.read_text(encoding="utf-8"))
    traj = [as_digest(d) for d in (data.get("trajectory") or [])]
    split = max(2, int(len(traj) * args.train_frac))
    model = fit_transitions(traj[:split])
    eval_report = evaluate(traj[split - 1:], model, top=args.top)

    report = {
        "ticks": len(traj),
        "fit_on": split,
        "eval": eval_report,
        "next_from_last": sorted(rollout(traj[-1], model, steps=args.steps, top=args.top)) if traj else [],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
