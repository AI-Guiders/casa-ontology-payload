#!/usr/bin/env python3
"""S6: meta compare на двух кругах (greater / less)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, PureMetaPhrase, VISUAL, bootstrap, class_dir_for, cli_pure_meta, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_ITEMS = (
    PureMetaPhrase(meta.COMPARE_GREATER, "больше", "geom-circles-left-greater", "compare-greater-circles"),
    PureMetaPhrase(meta.COMPARE_LESS, "меньше", "geom-circles-left-less", "compare-less-circles"),
)


def main() -> None:
    cli_pure_meta(
        VISUAL,
        _ITEMS,
        summary_file="summary-meta-compare-circles-pure.json",
        description=__doc__,
        moment_prefix="meta-compare-circles-pure",
        default_rounds=6,
        log_start=lambda rounds, modes, jobs: {
            "stage": "S6-meta-compare-circles",
            "frames": [i.frame_id for i in _ITEMS],
            "modes": list(modes),
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
