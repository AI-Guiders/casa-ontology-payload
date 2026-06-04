#!/usr/bin/env python3
"""S3c: meta spatial «выше/ниже» на двух отрезках A/B (одинаковая длина, общий x)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, PureMetaPhrase, VISUAL, bootstrap, class_dir_for, cli_pure_meta, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_ITEMS = (
    PureMetaPhrase(meta.SPATIAL_ABOVE_OF, "выше", "geom-segments-a-above", "spatial-above-segments"),
    PureMetaPhrase(meta.SPATIAL_BELOW_OF, "ниже", "geom-segments-a-below", "spatial-below-segments"),
)


def main() -> None:
    cli_pure_meta(
        VISUAL,
        _ITEMS,
        summary_file="summary-meta-spatial-vertical-pure.json",
        description=__doc__,
        moment_prefix="meta-spatial-vertical-pure",
        default_rounds=6,
        log_start=lambda rounds, modes, jobs: {
            "stage": "S3c-meta-spatial-vertical",
            "frames": [i.frame_id for i in _ITEMS],
            "surfaces": [i.surface for i in _ITEMS],
            "modes": list(modes),
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
