#!/usr/bin/env python3
"""Boost зеркальных spatial id: только правее / ниже (phrase_vis), без canon-кадра."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, PureMetaPhrase, VISUAL, bootstrap, class_dir_for, cli_pure_meta, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_ITEMS = (
    PureMetaPhrase(meta.SPATIAL_RIGHT_OF, "правее", "geom-segments-a-right", "spatial-right-segments"),
    PureMetaPhrase(meta.SPATIAL_BELOW_OF, "ниже", "geom-segments-a-below", "spatial-below-segments"),
)


def main() -> None:
    cli_pure_meta(
        VISUAL,
        _ITEMS,
        summary_file="summary-meta-spatial-mirror-boost.json",
        description=__doc__,
        moment_prefix="meta-spatial-mirror-boost",
        default_rounds=12,
        log_start=lambda rounds, modes, jobs: {
            "stage": "S3-spatial-mirror-boost",
            "frames": [i.frame_id for i in _ITEMS],
            "modes": list(modes),
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
