#!/usr/bin/env python3
"""Lab: reinforce geom-circles-left-less → lang.meta.compare.less (S6 tie with greater)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import VISUAL, bootstrap, cli_lab_main

bootstrap(__file__)


def _run(session, _args) -> None:
    from casa.prisms.visual.bridge_lex import reinforce_vis_lex_bridge

    row = reinforce_vis_lex_bridge(
        session.state,
        frame_id="geom-circles-left-less",
        lex_cid="lang.meta.compare.less",
        copies=12,
    )
    session.log({"reinforced": row is not None, "edge": row})


def main() -> None:
    cli_lab_main(
        VISUAL,
        _run,
        summary_file="summary-reinforce-geom-circles-less.json",
        description=__doc__,
    )


if __name__ == "__main__":
    main()
