#!/usr/bin/env python3
"""Ingest body/completions.jsonl on macro tick — percept + agent-owned commit (ADR-0046)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa.body.completion_percept import body_completions_path
from casa.prisms.memory.canon_nca_train import (
    CANON_NCA_FUNCTION_ID,
    agent_commit_canon_nca_completion,
)
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms
from casa.prisms.shared.lattice_names_v1 import canonical_lattice_id
from casa.prisms.shared.store_persist import mark_runtime_dirty


def _session_body_ledger(session: dict[str, Any]) -> dict[str, Any]:
    return session.setdefault("body", {})


def _completion_lattice_id(event: dict[str, Any]) -> str | None:
    body = event.get("body") if isinstance(event.get("body"), dict) else {}
    structured = body.get("structured") if isinstance(body.get("structured"), dict) else {}
    lid = structured.get("lattice_id")
    if lid:
        return canonical_lattice_id(str(lid))
    prov = body.get("provenance") if isinstance(body.get("provenance"), dict) else {}
    if prov.get("lattice_id"):
        return canonical_lattice_id(str(prov["lattice_id"]))
    return None


def _record_completion_episode(state: dict, event: dict[str, Any]) -> dict[str, Any] | None:
    body = event.get("body") if isinstance(event.get("body"), dict) else {}
    summary = str(body.get("summary") or "body completion")
    function_id = str(body.get("function_id") or "")
    ok = bool(body.get("ok"))
    lid = _completion_lattice_id(event) or "schema-math"
    return append_episode(
        state,
        cue=summary[:120],
        surface_attempt=function_id[:120] or "body",
        correct="ok" if ok else "error",
        lattice_id=lid,
        scene="body_completion",
        correction_kind="body_function_result",
        structure_tag="body_function_call",
        episode_source="wake",
        bind_class="open_probe",
    )


def ingest_body_completions_on_tick(
    store_dir: Path,
    state: dict,
    session: dict[str, Any],
) -> dict[str, Any]:
    """Drain new completion percepts; canon NCA → agent commit in RAM (persist on tick boundary)."""
    store_dir = store_dir.resolve()
    state = ensure_prisms(state)
    path = body_completions_path(store_dir)
    ledger = _session_body_ledger(session)
    offset = int(ledger.get("completions_line_offset") or 0)

    if not path.is_file():
        return {"ingested": 0, "committed": 0, "offset": offset}

    lines = path.read_text(encoding="utf-8").splitlines()
    if offset >= len(lines):
        return {"ingested": 0, "committed": 0, "offset": offset}

    new_lines = lines[offset:]
    episodes: list[str] = []
    commits: list[dict[str, Any]] = []

    for raw in new_lines:
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue

        ep = _record_completion_episode(state, event)
        if ep and ep.get("id"):
            episodes.append(str(ep["id"]))

        body = event.get("body") if isinstance(event.get("body"), dict) else {}
        if str(body.get("function_id") or "") != CANON_NCA_FUNCTION_ID:
            continue
        if not body.get("ok"):
            continue
        lid = _completion_lattice_id(event)
        if not lid:
            continue
        rep = agent_commit_canon_nca_completion(store_dir, state, lid, persist=False)
        if rep.get("committed"):
            commits.append(rep)

    ledger["completions_line_offset"] = offset + len(new_lines)
    if episodes or commits:
        mark_runtime_dirty(state)

    return {
        "ingested": len(new_lines),
        "episodes": episodes,
        "committed": len(commits),
        "commits": commits,
        "offset": ledger["completions_line_offset"],
    }
