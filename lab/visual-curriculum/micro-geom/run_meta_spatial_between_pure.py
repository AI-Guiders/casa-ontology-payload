#!/usr/bin/env python3
"""S3d: meta «между» — A,B,C на оси и 1,2,3 на прямой."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, PureMetaPhrase, VISUAL, bootstrap, class_dir_for, cli_pure_meta, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_ITEMS = (
    PureMetaPhrase(meta.SPATIAL_BETWEEN, "между", "geom-points-b-between-ac", "between-points-abc"),
    PureMetaPhrase(meta.SPATIAL_BETWEEN, "между", "numberline-2-between-1-3", "between-nline-123"),
)


def main() -> None:
    cli_pure_meta(
        VISUAL,
        _ITEMS,
        summary_file="summary-meta-spatial-between-pure.json",
        description=__doc__,
        moment_prefix="meta-spatial-between-pure",
        default_rounds=6,
        log_start=lambda rounds, modes, jobs: {
            "stage": "S3d-meta-spatial-between",
            "frames": [i.frame_id for i in _ITEMS],
            "modes": list(modes),
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
