#!/usr/bin/env python3
"""Reinforce зеркальных spatial: vis→rightOf / belowOf (tie-break после sleep 4:4)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, VISUAL, bootstrap, class_dir_for, cli_lab_main, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_MIRROR = (
    ("geom-segments-a-right", meta.SPATIAL_RIGHT_OF),
    ("geom-segments-a-below", meta.SPATIAL_BELOW_OF),
)


def _run(session, _args) -> None:
    from casa.prisms.visual.bridge_lex import reinforce_vis_lex_bridge

    for frame_id, lex_cid in _MIRROR:
        row = reinforce_vis_lex_bridge(
            session.state,
            frame_id=frame_id,
            lex_cid=lex_cid,
            copies=12,
        )
        session.log({"frame_id": frame_id, "lex_cid": lex_cid, "reinforced": row is not None})


def main() -> None:
    cli_lab_main(
        VISUAL,
        _run,
        summary_file="summary-meta-spatial-mirror-reinforce.json",
        description=__doc__,
    )


if __name__ == "__main__":
    main()
