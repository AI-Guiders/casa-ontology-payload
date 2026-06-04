#!/usr/bin/env python3
"""S2: meta compare «больше/меньше» на кадрах numberline compare."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, PureMetaPhrase, VISUAL, bootstrap, class_dir_for, cli_pure_meta, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_ITEMS = (
    PureMetaPhrase(meta.COMPARE_GREATER, "больше", "numberline-compare-3gt2", "compare-greater-nline"),
    PureMetaPhrase(meta.COMPARE_LESS, "меньше", "numberline-compare-2lt3", "compare-less-nline"),
)


def main() -> None:
    cli_pure_meta(
        VISUAL,
        _ITEMS,
        summary_file="summary-meta-compare-nline-pure.json",
        description=__doc__,
        moment_prefix="meta-compare-nline-pure",
        default_rounds=6,
        log_start=lambda rounds, modes, jobs: {
            "stage": "S2-meta-compare-nline",
            "frames": [i.frame_id for i in _ITEMS],
            "modes": list(modes),
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
