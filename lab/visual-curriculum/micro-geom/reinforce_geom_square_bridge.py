#!/usr/bin/env python3
"""Lab: strengthen geom-square → math.geom.square when sleep tie with circle persists."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import VISUAL, bootstrap, cli_lab_main


def _run(session, _args) -> None:
    from casa.prisms.visual.bridge_math import reinforce_vis_math_bridge

    row = reinforce_vis_math_bridge(
        session.state,
        frame_id="geom-square",
        math_cid="math.geom.square",
        copies=12,
    )
    session.log({"reinforced": row is not None, "edge": row})


bootstrap(__file__)


def main() -> None:
    cli_lab_main(VISUAL, _run, summary_file="summary-reinforce-geom-square.json", description=__doc__)


if __name__ == "__main__":
    main()
