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


def _candidate_explicit_ready(row: dict[str, Any]) -> bool:
    tags = [str(t) for t in (row.get("tags") or [])]
    return "canon-ready" in tags


def verify_canon_candidate(
    state: dict,
    store_dir: Path,
    candidate: dict[str, Any],
    *,
    bundle: dict | None = None,
    tick: int = 0,
) -> dict[str, Any]:
    """Agent held-out check before promote — predict on test_cues, mastery streak."""
    jid = str(candidate.get("journal_id") or "")
    if not jid:
        return {"ready": False, "reason": "no_journal_id"}

    gate = _canon_gate_id(jid)
    if mastery_ready(state, gate, min_streak=2):
        return {"ready": True, "reason": "mastery_streak", "gate": gate}

    for row in _journal_rows(store_dir, jid):
        if _candidate_explicit_ready(row):
            record_gate_attempt(state, gate, passed=True, tick=tick, store_dir=store_dir)
            record_gate_attempt(state, gate, passed=True, tick=tick, store_dir=store_dir)
            return {"ready": True, "reason": "tag_canon_ready", "gate": gate}

    concepts = [str(c) for c in (candidate.get("concepts") or [])]
    cues = [str(c) for c in (candidate.get("test_cues") or []) if c]
    if not cues:
        return {"ready": False, "reason": "no_test_cues", "gate": gate}

    from casa.prisms.tick.predict_tick import predict_tick

    passed_cue = False
    for cue in cues[:4]:
        rep = predict_tick(state, cue, modality="t9", bundle=bundle)
        if rep.get("verdict") not in ("pass", "provisional"):
            continue
        hyp = str(rep.get("hypothesis") or rep.get("top_concept") or "")
        if any(c in hyp or c.split(".")[-1] in hyp.lower() for c in concepts):
            passed_cue = True
            break
    record_gate_attempt(state, gate, passed=passed_cue, tick=tick, store_dir=store_dir)
    if mastery_ready(state, gate, min_streak=2):
        return {"ready": True, "reason": "predict_mastery", "gate": gate}
    return {"ready": False, "reason": "mastery_pending", "gate": gate, "last_cue_pass": passed_cue}


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

        verify = verify_canon_candidate(state, store_dir, cand, bundle=bundle, tick=tick)
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
                "reason": f"tick promote ({verify.get('reason')}): {cand.get('text', '')[:120]}",
            },
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
