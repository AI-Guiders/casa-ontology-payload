#!/usr/bin/env python3
"""S3b: meta spatial «левее/правее» на двух отрезках A/B (одинаковая длина)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, PureMetaPhrase, VISUAL, bootstrap, class_dir_for, cli_pure_meta, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_ITEMS = (
    PureMetaPhrase(meta.SPATIAL_LEFT_OF, "левее", "geom-segments-a-left", "spatial-left-segments"),
    PureMetaPhrase(meta.SPATIAL_RIGHT_OF, "правее", "geom-segments-a-right", "spatial-right-segments"),
)


def main() -> None:
    cli_pure_meta(
        VISUAL,
        _ITEMS,
        summary_file="summary-meta-spatial-segments-pure.json",
        description=__doc__,
        moment_prefix="meta-spatial-segments-pure",
        default_rounds=6,
        log_start=lambda rounds, modes, jobs: {
            "stage": "S3b-meta-spatial-segments",
            "frames": [i.frame_id for i in _ITEMS],
            "surfaces": [i.surface for i in _ITEMS],
            "modes": list(modes),
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
