#!/usr/bin/env python3
"""Promote bootstrap capability/applicability routes when probe mastery streak is ready."""

from __future__ import annotations

import argparse
import json

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, lab_session

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--min-streak", type=int, default=2)
    args = p.parse_args()

    from casa.domain.emergent_promote import promote_pending_bootstrap_routes

    lab = lab_session(LITERACY, micro_dir=_MICRO, store_id=args.store)
    lab.load()
    rows = promote_pending_bootstrap_routes(lab.state, min_mastery_streak=int(args.min_streak))
    if rows:
        lab.save(sync_ltm=False)
    print(
        json.dumps(
            {
                "promoted_batches": len(rows),
                "routes": [r.promoted for r in rows],
                "skipped": [r.skipped for r in rows],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
