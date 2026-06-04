#!/usr/bin/env python3
"""S5: центр и радиус круга (math.geom.center / .radius)."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import VISUAL, bootstrap, cli_json_batch

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
MICRO = [
    ("geom-micro-center", "geom-micro-center.json"),
    ("geom-micro-radius", "geom-micro-radius.json"),
]


def main() -> None:
    cli_json_batch(
        VISUAL,
        _STEPS,
        MICRO,
        summary_file="summary-geom-center-radius.json",
        description=__doc__,
        log_start={"stage": "S5-center-radius"},
    )


if __name__ == "__main__":
    main()
