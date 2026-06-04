#!/usr/bin/env python3
"""S1b: math.compare.gt/lt на чистых кадрах lesson-27 (6 раундов, чередование gt/lt)."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import NLINE, bootstrap, cli_json_batch

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
_FRAMES = (
    ("nline-compare-pure-3gt2", "nline-compare-pure-3gt2.json"),
    ("nline-compare-pure-2lt3", "nline-compare-pure-2lt3.json"),
)
MICRO = [
    (f"{stem}-r{r}", js)
    for r in range(1, 7)
    for stem, js in _FRAMES
]


def main() -> None:
    cli_json_batch(
        NLINE,
        _STEPS,
        MICRO,
        summary_file="summary-nline-compare-pure.json",
        description=__doc__,
        log_start={"stage": "S1b-math-compare-pure", "rounds": 6, "moments": len(MICRO)},
    )


if __name__ == "__main__":
    main()
