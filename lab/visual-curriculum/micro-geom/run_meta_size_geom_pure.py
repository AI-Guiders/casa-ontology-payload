#!/usr/bin/env python3
"""Чистый meta size на геометрии: крупный vs мелкий круг → lang.meta.size.*."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, VISUAL, PureMetaPhrase, bootstrap, class_dir_for, cli_pure_meta, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_ITEMS = (
    PureMetaPhrase(meta.SIZE_LARGE, "большая", "geom-circle-large", "geom-size-large"),
    PureMetaPhrase(meta.SIZE_SMALL, "маленькая", "geom-circle-small", "geom-size-small"),
)


def main() -> None:
    cli_pure_meta(
        VISUAL,
        _ITEMS,
        summary_file="summary-meta-size-geom-pure.json",
        description=__doc__,
        moment_prefix="geom-meta-size-pure",
        default_rounds=6,
        log_start=lambda rounds, modes, jobs: {
            "frames": [item.frame_id for item in _ITEMS],
            "modes": list(modes),
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
