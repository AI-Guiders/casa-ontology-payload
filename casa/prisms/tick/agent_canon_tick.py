#!/usr/bin/env python3
"""Tick-time agent canon promote — when confirmed law holds (self-drive hook)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.domain.mastery_gate import mastery_ready, record_gate_attempt
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.memory.agent_canon_field import enqueue_canon_sleep_episodes, sync_agent_canon_to_field
from casa.prisms.memory.agent_canon_lattice import (
    agent_promote_canon_lattice,
    canon_promote_candidates,
    load_canon_registry,
)
from casa.prisms.shared.canon_lattice_policy import concept_allowed_for_lattice, planned_agent_canon_lattices


def _canon_gate_id(journal_id: str) -> str:
    return f"canon:{str(journal_id or '').strip()}"


def _registry_has_concepts(store_dir: Path, lattice_id: str, concept_ids: list[str]) -> bool:
    reg = load_canon_registry(store_dir)
    row = next((e for e in (reg.get("entries") or []) if e.get("lattice_id") == lattice_id), None)
    if not row:
        return False
    have = {str(c) for c in (row.get("concept_ids") or [])}
    return all(str(c) in have for c in concept_ids)


def _wrong_sibling(concept_id: str) -> str:
    """A deliberately-wrong concept in the same prefix family (negative control)."""
    prefix, _, leaf = str(concept_id).rpartition(".")
    return f"{prefix}.__not_{leaf}__" if prefix else f"__not_{leaf}__"


def verify_canon_candidate(
    state: dict,
    store_dir: Path,
    candidate: dict[str, Any],
    *,
    lattice_id: str | None = None,
    bundle: dict | None = None,
    tick: int = 0,
) -> dict[str, Any]:
    """Held-out gate before promote (ADR-0037/0069).

    Replaces the self-grantable canon-ready tag + mastery-streak bypass: predict on
    HELD-OUT test_cues with the answer-injection vector (claims_nav) ablated, and
    require that a deliberately-wrong sibling concept does NOT surface. Returns
    ``{ready, report, reason}``; the promote ceremony consumes ``report``. Too few
    probes -> not ready (no ungated promotion).
    """
    import hashlib

    from casa.eval.held_out_gate import GateReport, ablate_injection_vectors, promote_candidate_id
    from casa.prisms.tick.predict_tick import predict_tick

    concepts = [str(c) for c in (candidate.get("concepts") or []) if c]
    cues = [str(c) for c in (candidate.get("test_cues") or []) if c]
    lid = str(lattice_id or _pick_lattice(candidate, concepts) or "")
    if not concepts or not lid:
        return {"ready": False, "reason": "no_concepts_or_lattice", "report": None}
    if len(cues) < 2:
        return {"ready": False, "reason": "insufficient_probes", "report": None}

    ordered = sorted(cues, key=lambda c: hashlib.sha1(c.encode("utf-8")).hexdigest())
    held_out = ordered[len(ordered) - max(1, len(ordered) // 2):]
    st = ablate_injection_vectors(state)

    def _surfaces(cue: str, targets: list[str]) -> bool:
        rep = predict_tick(st, cue, modality="t9", bundle=bundle)
        if rep.get("verdict") not in ("pass", "provisional"):
            return False
        hyp = str((rep.get("predict") or {}).get("hypothesis") or rep.get("hypothesis") or "")
        return any(c in hyp or c.split(".")[-1] in hyp.lower() for c in targets)

    passes = sum(1 for cue in held_out if _surfaces(cue, concepts))
    held_score = round(passes / len(held_out), 4)
    wrong = [_wrong_sibling(c) for c in concepts]
    neg_hits = sum(1 for cue in held_out if _surfaces(cue, wrong))
    neg_rate = round(neg_hits / len(held_out), 4)
    negative_control_passed = neg_rate <= 0.34
    passed = bool(held_score >= 1.0 and passes >= 1 and negative_control_passed)

    report = GateReport(
        passed=passed,
        candidate_id=promote_candidate_id(lid, concepts),
        held_out_score=held_score,
        held_out_pass=passes,
        held_out_n=len(held_out),
        baseline_delta=0.0,
        negative_control_passed=negative_control_passed,
        neg_pass_rate=neg_rate,
        provenance={"authority": "held_out_gate_tick", "ablations": ["claims_nav"], "held_out_cues": held_out},
        cases=[],
    )
    return {"ready": passed, "reason": "held_out_gate", "report": report, "gate": _canon_gate_id(str(candidate.get("journal_id") or ""))}


def _journal_rows(store_dir: Path, journal_id: str) -> list[dict[str, Any]]:
    from casa.prisms.memory.agent_journal import search_journal_entries

    return [r for r in search_journal_entries(store_dir, domain="self", limit=200) if r.get("id") == journal_id]


def _pick_lattice(candidate: dict[str, Any], concept_ids: list[str]) -> str | None:
    suggested = [str(x) for x in (candidate.get("suggested_lattices") or []) if x]
    for lid in suggested:
        if all(concept_allowed_for_lattice(lid, c) for c in concept_ids):
            return lid
    for lid in planned_agent_canon_lattices():
        if all(concept_allowed_for_lattice(lid, c) for c in concept_ids):
            return lid
    return None


def maybe_promote_canon_on_tick(
    store_dir: Path,
    state: dict,
    *,
    wm: WorkingMemory | None = None,
    bundle: dict | None = None,
    limit: int = 3,
) -> dict[str, Any] | None:
    """Self-drive: agent promotes confirmed laws to agent_canon when mastery holds."""
    from casa.prisms.shared.canon_lattice_policy import agent_decides_canon

    if not agent_decides_canon():
        return None

    tick = int(wm.tick if wm is not None else state.get("field_version") or 0)
    candidates = canon_promote_candidates(store_dir, limit=limit)
    if not candidates:
        return {"promoted": [], "skipped": True, "reason": "no_candidates"}

    promoted: list[dict[str, Any]] = []
    for cand in candidates:
        concepts = [str(c) for c in (cand.get("concepts") or []) if c]
        lid = _pick_lattice(cand, concepts)
        if not lid:
            continue
        if _registry_has_concepts(store_dir, lid, concepts):
            continue

        verify = verify_canon_candidate(state, store_dir, cand, lattice_id=lid, bundle=bundle, tick=tick)
        if not verify.get("ready"):
            continue

        jid = str(cand.get("journal_id") or "")
        rep = agent_promote_canon_lattice(
            store_dir,
            state,
            {
                "lattice_id": lid,
                "concept_ids": concepts,
                "source_journal_id": jid,
                "reason": f"tick promote (held-out gate): {cand.get('text', '')[:120]}",
            },
            gate_report=verify.get("report"),
            persist=False,
        )
        cue = " · ".join(str(c) for c in (cand.get("test_cues") or [])[:2])
        enqueue_canon_sleep_episodes(
            state,
            lattice_id=lid,
            concept_ids=concepts,
            cue=cue or str(cand.get("text") or "")[:80],
            journal_id=jid,
        )
        sync_agent_canon_to_field(state, store_dir)
        promoted.append({**rep, "verify": verify})

    if not promoted:
        return {"promoted": [], "skipped": True, "reason": "none_ready", "candidates": len(candidates)}
    return {"promoted": promoted, "count": len(promoted)}
