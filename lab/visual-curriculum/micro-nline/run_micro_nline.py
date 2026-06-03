#!/usr/bin/env python3
"""Run five nline-set micro-moments (one vis+math per sleep)."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import NLINE, bootstrap, cli_json_batch

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
MICRO = [
    ("nline-micro-intersect", "nline-micro-intersect.json"),
    ("nline-micro-union", "nline-micro-union.json"),
    ("nline-micro-subset", "nline-micro-subset.json"),
    ("nline-micro-disjoint", "nline-micro-disjoint.json"),
    ("nline-micro-a-only", "nline-micro-a-only.json"),
]


def main() -> None:
    cli_json_batch(NLINE, _STEPS, MICRO, summary_file="summary.json", description=__doc__)


if __name__ == "__main__":
    main()
