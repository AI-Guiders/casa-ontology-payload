#!/usr/bin/env python3
"""Lab: strengthen geom-square → math.geom.square when sleep tie with circle persists."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from lab_paths import setup_lab_paths

_REPO, _ = setup_lab_paths(__file__)
from curriculum_lab import CurriculumLabSession


def main() -> None:
    from casa.prisms.visual.bridge_math import reinforce_vis_math_bridge

    lab = CurriculumLabSession(generated_subdir="micro-geom")
    with lab:
        row = reinforce_vis_math_bridge(
            lab.state,
            frame_id="geom-square",
            math_cid="math.geom.square",
            copies=12,
        )
        lab.log({"reinforced": row is not None, "edge": row})


if __name__ == "__main__":
    main()
