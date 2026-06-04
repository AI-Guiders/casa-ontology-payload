#!/usr/bin/env python3
"""S4f: meta параллельно / перпендикулярно."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, PureMetaPhrase, VISUAL, bootstrap, class_dir_for, cli_pure_meta, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_ITEMS = (
    PureMetaPhrase(meta.LINES_PARALLEL, "параллельно", "geom-lines-parallel", "lines-parallel"),
    PureMetaPhrase(meta.LINES_PERPENDICULAR, "перпендикулярно", "geom-lines-perpendicular", "lines-perp"),
)


def main() -> None:
    cli_pure_meta(
        VISUAL,
        _ITEMS,
        summary_file="summary-meta-geom-orientation-pure.json",
        description=__doc__,
        moment_prefix="meta-geom-orientation-pure",
        default_rounds=6,
        log_start=lambda rounds, modes, jobs: {
            "stage": "S4f-meta-geom-orientation",
            "frames": [i.frame_id for i in _ITEMS],
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
