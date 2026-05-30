#!/usr/bin/env python3
"""Measure concept votes on memory lattice (before/after sleep comparison)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms, episode_vote_for_cue, hippo_episodes  # type: ignore


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--concept-id", default=None)
    p.add_argument("--target", type=Path, default=None, help="UTF-8 JSON: concept_id, lattice, cue")
    p.add_argument("--lattice", default="L1_syllable")
    p.add_argument("--cue", default="м а")
    args = p.parse_args()

    target = {}
    if args.target:
        target = json.loads(args.target.read_text(encoding="utf-8"))
    concept_id = args.concept_id or target.get("concept_id") or "syllable.ма"
    lattice = target.get("lattice") or args.lattice
    cue = target.get("cue") or args.cue

    store = args.store_dir.resolve()
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    state = ensure_prisms(load_field_state(store / "field_state.json"))
    votes = episode_vote_for_cue(state, bundle, cue, lattice, concept_id)

    print(
        json.dumps(
            {
                "concept_id": concept_id,
                "lattice": lattice,
                "votes": votes,
                "hippo_pending": len([e for e in hippo_episodes(state) if not e.get("consolidated")]),
                "field_version": state.get("field_version"),
                "schema_version": state.get("schema_version"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
