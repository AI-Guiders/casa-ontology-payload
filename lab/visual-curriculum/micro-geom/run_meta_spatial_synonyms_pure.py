#!/usr/bin/env python3
"""Синонимы spatial: слева/справа/сверху/снизу → те же id, те же кадры на одной оси."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, PureMetaPhrase, VISUAL, bootstrap, class_dir_for, cli_pure_meta, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_ITEMS = (
    PureMetaPhrase(meta.SPATIAL_LEFT_OF, "слева", "geom-segments-a-left", "syn-left"),
    PureMetaPhrase(meta.SPATIAL_RIGHT_OF, "справа", "geom-segments-a-right", "syn-right"),
    PureMetaPhrase(meta.SPATIAL_ABOVE_OF, "сверху", "geom-segments-a-above", "syn-above"),
    PureMetaPhrase(meta.SPATIAL_BELOW_OF, "снизу", "geom-segments-a-below", "syn-below"),
)


def main() -> None:
    cli_pure_meta(
        VISUAL,
        _ITEMS,
        summary_file="summary-meta-spatial-synonyms-pure.json",
        description=__doc__,
        moment_prefix="meta-spatial-synonyms-pure",
        default_rounds=6,
        log_start=lambda rounds, modes, jobs: {
            "stage": "S3-spatial-synonyms",
            "frames": [i.frame_id for i in _ITEMS],
            "surfaces": [i.surface for i in _ITEMS],
            "modes": list(modes),
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
