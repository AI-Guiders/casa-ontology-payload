#!/usr/bin/env python3
"""Limbic value tags for lattice_value (CASA-ADR-0010, R5).

Maps surprise, teacher correction kind, and task relevance into a scalar priority
tag used by replay_buffer_v0 (value_weight) and sleep ordering (P9).

Pure functions on plain dicts — field realization stamps `value.*` concepts on
`lattice_value` and mirrors the scalar on consolidation.replay_buffer records.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from typing import Any, Iterable

# Teacher-committed corrections rank above passive surprise.
CORRECTION_VALUE: dict[str, float] = {
    "script_rule": 1.5,
    "morph_surface": 1.2,
    "ortho_surface": 1.0,
    "wait_prefix": 0.0,
    "lexical_ask": 0.0,
}

SURPRISE_UNIT = 0.15
TASK_RELEVANCE_BONUS = 0.3
MAX_VALUE = 3.0


def value_from_surprise(surprise: Iterable[str] | None) -> float:
    """Bottom-up salience magnitude from unpredicted concepts (P8 feed)."""
    n = len(list(surprise or []))
    return min(MAX_VALUE, n * SURPRISE_UNIT)


def value_from_correction(correction_kind: str | None) -> float:
    """Teacher-emphasis tag — only committed correction kinds carry weight."""
    if not correction_kind:
        return 0.0
    return CORRECTION_VALUE.get(str(correction_kind), 0.0)


def value_from_task(*, task_relevant: bool = False, goal_match: bool = False) -> float:
    """FPN goal alignment bonus."""
    if goal_match:
        return TASK_RELEVANCE_BONUS + 0.2
    if task_relevant:
        return TASK_RELEVANCE_BONUS
    return 0.0


def episode_value(
    *,
    surprise: Iterable[str] | None = None,
    correction_kind: str | None = None,
    task_relevant: bool = False,
    goal_match: bool = False,
) -> float:
    """Combined scalar for replay / sleep priority (P9)."""
    v = value_from_surprise(surprise)
    v += value_from_correction(correction_kind)
    v += value_from_task(task_relevant=task_relevant, goal_match=goal_match)
    return round(min(MAX_VALUE, v), 3)


def tag_surface_error(result: dict[str, Any], *, task_relevant: bool = False) -> float:
    """Derive value from a surface_error_v0 classify() result."""
    surprise_set = {result.get("axis", "")} if result.get("surprise") else set()
    return episode_value(
        surprise=surprise_set,
        correction_kind=result.get("correction_kind"),
        task_relevant=task_relevant,
    )


def tag_replay_record(record: dict[str, Any], *, surprise: Iterable[str] | None = None) -> float:
    """Fill value on a replay_buffer record from its fields."""
    v = episode_value(
        surprise=surprise,
        correction_kind=record.get("correction_kind"),
        task_relevant=bool(record.get("task_relevant")),
    )
    record["value"] = v
    return v


def main() -> int:
    p = argparse.ArgumentParser(description="lattice_value tag demo (CASA-ADR-0010 R5)")
    p.add_argument("--correction-kind", default="ortho_surface")
    p.add_argument("--surprise-count", type=int, default=2)
    p.add_argument("--task-relevant", action="store_true")
    args = p.parse_args()

    surprise = [f"unexpected.{i}" for i in range(max(0, args.surprise_count))]
    v = episode_value(
        surprise=surprise,
        correction_kind=args.correction_kind,
        task_relevant=args.task_relevant,
    )
    print(json.dumps({"value": v, "surprise_n": len(surprise), "correction_kind": args.correction_kind}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
