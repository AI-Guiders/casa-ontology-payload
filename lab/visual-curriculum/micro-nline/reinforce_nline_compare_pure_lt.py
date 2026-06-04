#!/usr/bin/env python3
"""Lab: reinforce numberline-compare-pure-2lt3 → math.compare.lt if probe tie persists."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import VISUAL, bootstrap, cli_lab_main

bootstrap(__file__)


def _run(session, _args) -> None:
    from casa.prisms.visual.bridge_math import reinforce_vis_math_bridge

    row = reinforce_vis_math_bridge(
        session.state,
        frame_id="numberline-compare-pure-2lt3",
        math_cid="math.compare.lt",
        copies=12,
    )
    session.log({"reinforced": row is not None, "edge": row})


def main() -> None:
    cli_lab_main(
        VISUAL,
        _run,
        summary_file="summary-reinforce-nline-compare-pure-lt.json",
        description=__doc__,
    )


if __name__ == "__main__":
    main()
