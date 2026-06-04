#!/usr/bin/env python3
"""S5: meta «ширина» на geom-rectangle-width."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, PureMetaPhrase, VISUAL, bootstrap, class_dir_for, cli_pure_meta, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_ITEMS = (PureMetaPhrase(meta.MEASURE_WIDTH, "ширина", "geom-rectangle-width", "measure-width"),)


def main() -> None:
    cli_pure_meta(
        VISUAL,
        _ITEMS,
        summary_file="summary-meta-measure-width-pure.json",
        description=__doc__,
        moment_prefix="meta-measure-width-pure",
        default_rounds=6,
        log_start=lambda rounds, modes, jobs: {
            "stage": "S5-meta-measure-width",
            "frames": [i.frame_id for i in _ITEMS],
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
