#!/usr/bin/env python3
"""Auto-curriculum orchestration: mine failures -> draft -> stage -> gate -> promote.

Failure-driven curriculum: find what the field CANNOT do, draft a lesson for each
gap, and stage+gate+promote it. The loop is deterministic; the lesson *generator* is
pluggable — ``default_generator`` turns a mined gap into a minimal teaching lesson,
and the real auto-curriculum plugs an external LLM here to draft richer lessons +
held-out probes (Von Neumann itself stays a non-LLM symbolic field; the LLM only
drafts candidates off the hot path).

  mine_targets(state, probes)  -> gaps the field fails (predict/recall miss)
  generator(target)            -> lesson  (pluggable; LLM in production)
  run_curriculum(state, gaps)  -> stage+gate+promote each; report promoted/rejected
"""

from __future__ import annotations

from typing import Any, Callable

Lesson = dict[str, Any]
Target = dict[str, Any]
Generator = Callable[[Target], "Lesson | None"]


def mine_targets(
    state: dict,
    probes: list[dict[str, Any]],
    *,
    bundle: dict[str, Any] | None = None,
) -> list[Target]:
    """Probes the field FAILS (with injection ablated) — the curriculum's targets.

    Each probe is ``{cue, concept_id, lattice_id, target?}``. This is the concrete
    failure-driven signal; richer miners (soft_miss, impulse threshold, predict-fail
    on live turns) feed the same target shape.
    """
    from casa.eval.held_out_gate import ablate_injection_vectors, score_case

    st = ablate_injection_vectors(state)
    out: list[Target] = []
    for p in probes:
        res = score_case(
            st,
            {
                "lattice": p["lattice_id"],
                "cue": p["cue"],
                "concept_id": p["concept_id"],
                "target": str(p.get("target") or p["cue"]),
            },
            bundle=bundle,
        )
        if not res["pass"]:
            out.append(
                {
                    "cue": p["cue"],
                    "concept_id": p["concept_id"],
                    "lattice_id": p["lattice_id"],
                    "target": str(p.get("target") or p["cue"]),
                    "signal": "predict_fail",
                }
            )
    return out


def default_generator(target: Target) -> Lesson:
    """Deterministic generator: a mined gap -> a minimal teaching lesson.

    The production auto-curriculum replaces this with an LLM that drafts a richer
    lesson (multiple examples, held-out probes, bilingual surfaces) from the gap.
    """
    return {
        "concept_id": target["concept_id"],
        "lattice_id": target["lattice_id"],
        "examples": [{"cue": target["cue"], "correct": target.get("target") or target["cue"]}],
    }


def run_curriculum(
    state: dict,
    targets: list[Target],
    *,
    generator: Generator = default_generator,
    bundle: dict[str, Any] | None = None,
    max_promote: int | None = None,
) -> dict[str, Any]:
    """Draft + stage + gate + promote each target. Mutates ``state`` only on promotes."""
    from casa.curriculum.staging import stage_and_promote

    promoted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for target in targets:
        lesson = generator(target)
        if not lesson:
            continue
        out = stage_and_promote(state, lesson, bundle=bundle)
        row = {"concept_id": target.get("concept_id"), "learned": out["learned"]}
        (promoted if out["promoted"] else rejected).append(row)
        if max_promote is not None and len(promoted) >= max_promote:
            break
    return {
        "promoted": promoted,
        "rejected": rejected,
        "n_promoted": len(promoted),
        "n_rejected": len(rejected),
    }
