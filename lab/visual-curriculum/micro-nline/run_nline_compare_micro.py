#!/usr/bin/env python3
"""S1: math.compare на числовой прямой (3>2, 2<3)."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import NLINE, bootstrap, cli_json_batch

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
MICRO = [
    ("nline-compare-3gt2", "nline-compare-3gt2.json"),
    ("nline-compare-2lt3", "nline-compare-2lt3.json"),
]


def main() -> None:
    cli_json_batch(
        NLINE,
        _STEPS,
        MICRO,
        summary_file="summary-nline-compare.json",
        description=__doc__,
        log_start={"stage": "S1-math-compare"},
    )


if __name__ == "__main__":
    main()
