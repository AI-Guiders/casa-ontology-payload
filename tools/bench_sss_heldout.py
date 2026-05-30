#!/usr/bin/env python3
"""Held-out cue bench: surface from field only (claims_nav ablation), no teacher."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from field_write import load_field_state  # type: ignore
from sss_surface_v0 import surface_from_sss  # type: ignore
from sss_cylinders_v0 import ensure_prisms, episode_vote_for_cue  # type: ignore
from sss_wake_util import norm_text, surface_attempt_from_wake, surface_matches_target, top_surface  # type: ignore


def _rank_of(concept_id: str, wake: dict) -> int | None:
    for i, row in enumerate(wake.get("active") or [], start=1):
        if str(row.get("concept_id")) == concept_id:
            return i
    return None


def eval_case(
    state: dict,
    case: dict,
    *,
    bundle: dict,
    top_k: int,
    ablate_claims_nav: bool,
) -> dict[str, Any]:
    st = copy.deepcopy(state)
    if ablate_claims_nav:
        st["claims_nav"] = []
        st["_ablation"] = "claims_nav_off"

    lattice = str(case.get("lattice") or "L1_syllable")
    cue = str(case.get("cue") or "")
    target = str(case.get("target") or "")
    concept_id = str(case.get("concept_id") or "")

    wake = surface_from_sss(st, lattice_id=lattice, prompt=cue)
    top = top_surface(wake)
    rank = _rank_of(concept_id, wake) if concept_id else None
    votes = episode_vote_for_cue(st, bundle, cue, lattice, concept_id) if concept_id else 0
    target_ok = surface_matches_target(wake, target, lattice_id=lattice) if target else False
    top_ok = bool(top and concept_id and str(top["concept_id"]) == concept_id)
    rank_ok = rank is not None and rank <= top_k

    return {
        "id": case.get("id") or cue,
        "cue": cue,
        "target": target,
        "concept_id": concept_id,
        "top_concept": top,
        "surface_attempt": surface_attempt_from_wake(wake, lattice_id=lattice),
        "rank": rank,
        "votes": votes,
        "top1_match": top_ok,
        "topk_match": rank_ok,
        "target_match": target_ok,
        "pass": top_ok or rank_ok or target_ok,
        "top_k": top_k,
        "active_top": (wake.get("active") or [])[:top_k],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--cases", type=Path, required=True, help="UTF-8 JSON: {cases:[...]} or [...]")
    p.add_argument("--top-k", type=int, default=3)
    p.add_argument("--ablate-claims-nav", action="store_true", default=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    raw = json.loads(args.cases.read_text(encoding="utf-8"))
    cases = raw.get("cases") if isinstance(raw, dict) else raw
    if not isinstance(cases, list):
        raise SystemExit("cases must be a JSON array or {cases: [...]}")

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    state = ensure_prisms(load_field_state(args.store_dir / "field_state.json"))

    results = [
        eval_case(
            state,
            c,
            bundle=bundle,
            top_k=max(1, args.top_k),
            ablate_claims_nav=args.ablate_claims_nav,
        )
        for c in cases
    ]
    passed = sum(1 for r in results if r["pass"])

    report = {
        "store": str(args.store_dir.resolve()),
        "schema_version": state.get("schema_version"),
        "field_version": state.get("field_version"),
        "ablate_claims_nav": args.ablate_claims_nav,
        "top_k": args.top_k,
        "passed": passed,
        "total": len(results),
        "pass_rate": round(passed / len(results), 4) if results else 0.0,
        "cases": results,
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
