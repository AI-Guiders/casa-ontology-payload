#!/usr/bin/env python3
"""S3: meta compare на двух отрезках A/B — равны / длиннее / короче (не «больше/меньше»)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, PureMetaPhrase, VISUAL, bootstrap, class_dir_for, cli_pure_meta, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_ITEMS = (
    PureMetaPhrase(meta.COMPARE_EQUAL, "равны", "geom-segments-equal", "compare-equal-segments"),
    PureMetaPhrase(meta.COMPARE_GREATER, "длиннее", "geom-segments-a-longer", "compare-longer-segments"),
    PureMetaPhrase(meta.COMPARE_LESS, "короче", "geom-segments-a-shorter", "compare-shorter-segments"),
)


def main() -> None:
    cli_pure_meta(
        VISUAL,
        _ITEMS,
        summary_file="summary-meta-compare-segments-pure.json",
        description=__doc__,
        moment_prefix="meta-compare-segments-pure",
        default_rounds=6,
        log_start=lambda rounds, modes, jobs: {
            "stage": "S3-meta-compare-segments",
            "frames": [i.frame_id for i in _ITEMS],
            "surfaces": [i.surface for i in _ITEMS],
            "modes": list(modes),
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
