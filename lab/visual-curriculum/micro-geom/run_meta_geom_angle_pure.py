#!/usr/bin/env python3
"""S4e: meta углы — один кадр, один sleep."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, PureMetaPhrase, VISUAL, bootstrap, class_dir_for, cli_pure_meta, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_ITEMS = (
    PureMetaPhrase(meta.ANGLE, "угол", "geom-angle-generic", "angle-generic"),
    PureMetaPhrase(meta.ANGLE_RIGHT, "прямой угол", "geom-angle-right", "angle-right"),
    PureMetaPhrase(meta.ANGLE_ACUTE, "острый угол", "geom-angle-acute", "angle-acute"),
    PureMetaPhrase(meta.ANGLE_OBTUSE, "тупой угол", "geom-angle-obtuse", "angle-obtuse"),
)


def main() -> None:
    cli_pure_meta(
        VISUAL,
        _ITEMS,
        summary_file="summary-meta-geom-angle-pure.json",
        description=__doc__,
        moment_prefix="meta-geom-angle-pure",
        default_rounds=6,
        log_start=lambda rounds, modes, jobs: {
            "stage": "S4e-meta-geom-angle",
            "frames": [i.frame_id for i in _ITEMS],
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
