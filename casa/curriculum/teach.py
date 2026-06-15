#!/usr/bin/env python3
"""Structured teaching tool — the usable core of the auto-curriculum.

Teach a concept (a vocabulary mapping or a generalizing rule) by sanctioned
learning, then verify it honestly:

  - vocabulary / recall  : does the field surface the concept for the taught
    surface(s)?  (memorization — no generalization to gate)
  - rule / generalization: does it pass the held-out gate on UNSEEN cues?
    (generalization — the held-out gate applies)

This is the engine. An LLM that drafts lessons + held-out probes (Phase 3) is the
simplified UX layered on top; here a lesson is supplied as structured data.

A "lesson" is::

    {
      "concept_id": "math.num.eleven",
      "lattice_id": "schema-math",
      "examples":  [{"cue": "11", "correct": "11"}, ...],   # taught (sanctioned)
      "held_out":  [{"cue": "11", "target": "eleven"}, ...] # optional, for rules
    }

Bilingual vocabulary is taught by giving the same concept surfaces in both scripts
(e.g. ``lang.word.eleven`` examples with cues "eleven" and "одиннадцать"), which the
field records as ``concept|names|surface`` edges in either language — the substrate
for concept-mediated RU<->EN term translation.
"""

from __future__ import annotations

from typing import Any


def teach(
    state: dict,
    *,
    concept_id: str,
    lattice_id: str,
    examples: list[dict[str, Any]],
    bundle: dict[str, Any] | None = None,
    held_out: list[dict[str, Any]] | None = None,
    policy: Any = None,
) -> dict[str, Any]:
    """Teach ``concept_id`` from ``examples`` and verify. Returns a report dict.

    With ``held_out`` -> verify generalization via the held-out gate (rules);
    ``policy`` (a GatePolicy) sets the rigor — a bigger lesson can demand more
    held-out passes. Without ``held_out`` -> verify recall on the taught cues
    (vocabulary).
    """
    from casa.eval.held_out_gate import (
        DEFAULT_GATE_POLICY,
        ablate_injection_vectors,
        candidate_id_for,
        gate_decision,
        score_case,
    )
    from casa.prisms.memory.memory_prisms import append_episode, run_sleep

    bundle = bundle or {"claims": [], "graph": {"edges": []}}
    taught: list[str] = []
    for ex in examples:
        cue = str(ex.get("cue") or "")
        if not cue:
            continue
        append_episode(
            state,
            cue=cue,
            surface_attempt=str(ex.get("surface_attempt") or "?"),
            correct=str(ex.get("correct") or cue),
            lattice_id=lattice_id,
            concept_id=concept_id,
            scene=str(ex.get("scene") or "teach"),
            # sanctioned earned-write: the held-out gate authorizes any later canon promote
            structure_tag="self_promote",
        )
        taught.append(cue)
    run_sleep(state, bundle)

    if held_out:
        probe_bank = {
            "cases": [
                {
                    "lattice": lattice_id,
                    "cue": str(h.get("cue") or ""),
                    "concept_id": concept_id,
                    "target": str(h.get("target") or ""),
                }
                for h in held_out
                if h.get("cue")
            ]
        }
        report = gate_decision(
            state,
            None,
            probe_bank,
            bundle=bundle,
            candidate_id=candidate_id_for([{"concept_id": concept_id}]),
            policy=policy or DEFAULT_GATE_POLICY,
        )
        return {
            "concept_id": concept_id,
            "mode": "held_out_gate",
            "learned": report.passed,
            "report": report.as_dict(),
        }

    # recall verification (vocabulary): injection ablated, the field must surface the
    # concept for each taught cue from the field alone.
    st = ablate_injection_vectors(state)
    recall: dict[str, bool] = {}
    for ex in examples:
        cue = str(ex.get("cue") or "")
        if not cue:
            continue
        res = score_case(
            st,
            {"lattice": lattice_id, "cue": cue, "concept_id": concept_id, "target": str(ex.get("correct") or "")},
            bundle=bundle,
        )
        recall[cue] = bool(res["pass"])
    return {
        "concept_id": concept_id,
        "mode": "recall",
        "learned": bool(recall) and all(recall.values()),
        "recall": recall,
    }
