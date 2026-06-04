#!/usr/bin/env python3
"""Lab: reinforce numberline-length-pure-2 → math.numberline.length (probe empty on math)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import VISUAL, bootstrap, cli_lab_main

bootstrap(__file__)


def _run(session, _args) -> None:
    from casa.prisms.visual.bridge_math import reinforce_vis_math_bridge

    row = reinforce_vis_math_bridge(
        session.state,
        frame_id="numberline-length-pure-2",
        math_cid="math.numberline.length",
        copies=12,
    )
    session.log({"reinforced": row is not None, "edge": row})


def main() -> None:
    cli_lab_main(
        VISUAL,
        _run,
        summary_file="summary-reinforce-nline-length-pure2.json",
        description=__doc__,
    )


if __name__ == "__main__":
    main()
