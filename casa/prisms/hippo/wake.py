#!/usr/bin/env python3
"""T_wake: surface + teacher correction → hippo episode (auto if wrong)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import load_field_state
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, save_state
from casa.prisms.memory.surface import surface_from_sss
from casa.prisms.hippo.wake_util import needs_self_correction, surface_attempt_from_wake, surface_matches_target


def _load_bundle(store: Path, bundle_path: Path | None) -> dict | None:
    if bundle_path:
        return json.loads(bundle_path.read_text(encoding="utf-8"))
    bs = list((store / "bundles").glob("*.json"))
    if bs:
        return json.loads(bs[0].read_text(encoding="utf-8"))
    return None


def wake_turn(
    state: dict,
    *,
    cue: str,
    lattice_id: str,
    target: str | None = None,
    teacher: str | None = None,
    bundle: dict | None = None,
    auto: bool = True,
    force_episode: bool = False,
    self_correct: bool = False,
) -> dict[str, Any]:
    """One wake tick: surface emit; episode when wrong (teacher, auto, or self-correct)."""
    external = (target or teacher or "").strip()
    state = ensure_prisms(state)
    state["sn"] = {**(state.get("sn") or {}), "mode": "wake", "active_prism": "prism_memory"}

    wake = surface_from_sss(state, lattice_id=lattice_id, prompt=cue)
    report: dict[str, Any] = {"wake": wake, "cue": cue, "lattice_id": lattice_id}

    if self_correct and not external:
        fix, internal = needs_self_correction(wake, cue, lattice_id=lattice_id)
        report["self_correct"] = True
        report["internal_target"] = internal
        correct = internal
        report["matched"] = not fix
    elif external:
        correct = external
        report["self_correct"] = False
        report["internal_target"] = None
        report["matched"] = surface_matches_target(wake, correct, lattice_id=lattice_id)
    else:
        report["matched"] = None
        report["episode"] = None
        report["self_correct"] = False
        return report

    report["surface_attempt"] = surface_attempt_from_wake(wake, lattice_id=lattice_id)
    report["target"] = correct
    if bundle and correct:
        from casa.prisms.memory.memory_prisms import concept_id_for_surface

        known = {str(c.get("concept_id")) for c in bundle.get("claims") or []}
        cid = concept_id_for_surface(bundle, correct, lattice_id=lattice_id)
        report["emergent"] = bool(cid and cid not in known)
    else:
        report["emergent"] = False

    need_episode = force_episode or (not report["matched"] and auto)
    if need_episode:
        ep = append_episode(
            state,
            cue=cue,
            surface_attempt=report["surface_attempt"],
            correct=correct,
            lattice_id=lattice_id,
            bundle=bundle,
        )
        report["episode"] = ep
        report["auto_episode"] = auto and not report["matched"] and not self_correct
        report["self_episode"] = auto and not report["matched"] and self_correct
    else:
        report["episode"] = None
        report["auto_episode"] = False
        report["self_episode"] = False

    report["hippo_pending"] = len(prism_hippo(state)["episodes"])
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--cue", required=True)
    p.add_argument("--lattice", default="L1_syllable")
    p.add_argument("--target", default=None, help="expected form; auto-episode if surface differs")
    p.add_argument("--teacher", default=None, help="alias for --target (always records if set without --auto)")
    p.add_argument("--bundle", type=Path, default=None)
    p.add_argument("--auto", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument(
        "--self-correct",
        action="store_true",
        help="derive target from cue; episode if surface mismatches",
    )
    p.add_argument("--force-episode", action="store_true")
    args = p.parse_args()

    store = args.store_dir.resolve()
    path = store / "field_state.json"

    state = load_field_state(path)
    bundle = _load_bundle(store, args.bundle)
    target = args.target or args.teacher
    auto = args.auto
    if args.teacher and not args.target and not args.auto:
        auto = False

    report = wake_turn(
        state,
        cue=args.cue,
        lattice_id=args.lattice,
        target=target,
        bundle=bundle,
        auto=auto,
        force_episode=args.force_episode,
        self_correct=args.self_correct,
    )
    save_state(path, state)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
