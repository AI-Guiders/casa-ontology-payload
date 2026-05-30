#!/usr/bin/env python3
"""Record teacher correction → cyl_hippo episode (T_wake)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import append_episode, ensure_prisms, save_state  # type: ignore


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--cue", required=True)
    p.add_argument("--surface-attempt", required=True)
    p.add_argument("--correct", required=True)
    p.add_argument("--lattice", default="L1_syllable")
    p.add_argument("--concept-id", default=None)
    p.add_argument("--bundle", type=Path, default=None)
    args = p.parse_args()

    store = args.store_dir.resolve()
    path = store / "field_state.json"
    state = load_field_state(path)
    if not state:
        raise SystemExit("no field_state; run sss_field.py --init first")

    bundle = None
    if args.bundle:
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    elif (store / "bundles").is_dir():
        bundles = list((store / "bundles").glob("*.json"))
        if bundles:
            bundle = json.loads(bundles[0].read_text(encoding="utf-8"))

    state = ensure_prisms(state)
    ep = append_episode(
        state,
        cue=args.cue,
        surface_attempt=args.surface_attempt,
        correct=args.correct,
        lattice_id=args.lattice,
        concept_id=args.concept_id,
        bundle=bundle,
    )
    save_state(path, state)
    print(json.dumps({"episode": ep, "hippo_pending": len(prism_hippo(state)["episodes"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
