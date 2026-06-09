#!/usr/bin/env python3
"""Agent canon lattice — promote/demote immutable law nodes (agent act, ADR-0015)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_journal import search_journal_entries
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.shared.canon_lattice_policy import (
    assert_agent_may_promote,
    assert_concepts_for_lattice,
    host_bootstrap_lattice_ids,
    planned_agent_canon_lattices,
)
from casa.prisms.shared.lattice_names_v1 import canonical_lattice_id
from casa.prisms.shared.store_layout import agent_canon_registry_path
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _empty_registry() -> dict[str, Any]:
    return {"schema_version": 1, "agent_decides_canon": True, "entries": [], "demoted": []}


def load_canon_registry(store_dir: Path) -> dict[str, Any]:
    path = agent_canon_registry_path(store_dir)
    if not path.is_file():
        return _empty_registry()
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc.setdefault("entries", [])
    doc.setdefault("demoted", [])
    return doc


def save_canon_registry(store_dir: Path, doc: dict[str, Any]) -> Path:
    path = agent_canon_registry_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def list_agent_canon_lattices(store_dir: Path) -> dict[str, Any]:
    reg = load_canon_registry(store_dir)
    return {
        "count": len(reg.get("entries") or []),
        "entries": list(reg.get("entries") or []),
        "demoted_count": len(reg.get("demoted") or []),
        "planned_targets": sorted(planned_agent_canon_lattices().keys()),
        "host_bootstrap": sorted(host_bootstrap_lattice_ids()),
    }


def _journal_row(store_dir: Path, journal_id: str | None) -> dict[str, Any] | None:
    if not journal_id:
        return None
    for row in search_journal_entries(store_dir, domain="self", limit=200):
        if str(row.get("id") or "") == journal_id:
            return row
    return None


def _require_confirmed_source(
    store_dir: Path,
    *,
    source_journal_id: str | None,
    allow_unconfirmed: bool,
) -> dict[str, Any] | None:
    if allow_unconfirmed or not source_journal_id:
        return _journal_row(store_dir, source_journal_id)
    row = _journal_row(store_dir, source_journal_id)
    if row is None:
        raise ValueError(f"source journal entry not found: {source_journal_id!r}")
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    if str(meta.get("status") or "") != "confirmed":
        raise ValueError(
            f"source journal {source_journal_id!r} is not confirmed; "
            "agent may still promote after own held-out check with allow_unconfirmed=true"
        )
    return row


def canon_promote_candidates(
    store_dir: Path,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Confirmed journal rows that match planned agent_canon concept prefixes."""
    prefixes: list[str] = []
    for spec in planned_agent_canon_lattices().values():
        for p in spec.get("concept_prefix") or []:
            prefixes.append(str(p))
        mp = spec.get("meta_prefix")
        if mp:
            prefixes.append(str(mp) + ".")
    out: list[dict[str, Any]] = []
    for row in search_journal_entries(store_dir, domain="self", limit=120):
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        if str(meta.get("status") or "") != "confirmed":
            continue
        concepts = [str(c) for c in (row.get("concepts") or []) if c]
        matched = [c for c in concepts if any(c.startswith(p) for p in prefixes)]
        if not matched:
            continue
        targets = []
        for lid, spec in planned_agent_canon_lattices().items():
            pfx = [str(p) for p in (spec.get("concept_prefix") or [])]
            mp = spec.get("meta_prefix")
            if mp:
                pfx.append(str(mp) + ".")
            if any(any(c.startswith(p) for p in pfx) for c in matched):
                targets.append(lid)
        out.append(
            {
                "journal_id": row.get("id"),
                "text": str(row.get("text") or "")[:200],
                "concepts": matched,
                "suggested_lattices": targets,
                "test_cues": meta.get("test_cues") or [],
            }
        )
        if len(out) >= limit:
            break
    return out


def agent_promote_canon_lattice(
    store_dir: Path,
    state: dict[str, Any],
    request: dict[str, Any],
    *,
    persist: bool = True,
    allow_unconfirmed: bool = False,
) -> dict[str, Any]:
    """Freeze concept ids on agent_canon lattice — agent decision, not teacher approve."""
    lattice_id = canonical_lattice_id(str(request.get("lattice_id") or ""))
    spec = assert_agent_may_promote(lattice_id)
    concept_ids = [str(c) for c in (request.get("concept_ids") or []) if c]
    assert_concepts_for_lattice(lattice_id, concept_ids)

    source_id = str(request.get("source_journal_id") or request.get("journal_id") or "").strip() or None
    source = _require_confirmed_source(
        store_dir, source_journal_id=source_id, allow_unconfirmed=allow_unconfirmed
    )
    if source and not concept_ids:
        concept_ids = [str(c) for c in (source.get("concepts") or []) if c]
        assert_concepts_for_lattice(lattice_id, concept_ids)

    reason = str(request.get("reason") or "").strip()
    reg = load_canon_registry(store_dir)
    entries: list[dict[str, Any]] = list(reg.get("entries") or [])
    now = _utc_now()
    merged_ids = sorted(set(concept_ids))
    existing = next((e for e in entries if e.get("lattice_id") == lattice_id), None)
    if existing:
        prev = [str(c) for c in (existing.get("concept_ids") or [])]
        merged_ids = sorted(set(prev + merged_ids))
        existing.update(
            {
                "concept_ids": merged_ids,
                "updated_at": now,
                "reason": reason or existing.get("reason"),
                "source_journal_id": source_id or existing.get("source_journal_id"),
            }
        )
        entry_row = existing
    else:
        entry_row = {
            "lattice_id": lattice_id,
            "stability": "agent_canon",
            "semantic": spec.get("semantic"),
            "concept_ids": merged_ids,
            "promoted_at": now,
            "source_journal_id": source_id,
            "reason": reason,
        }
        entries.append(entry_row)
    reg["entries"] = entries
    save_canon_registry(store_dir, reg)

    journal_text = reason or (
        f"Закрепил на canon lattice {lattice_id}: {', '.join(merged_ids)}."
    )
    remember = agent_remember(
        store_dir,
        state,
        {
            "kind": "observation",
            "text": journal_text,
            "concepts": merged_ids,
            "tags": ["canon-promote", f"canon:{lattice_id}"],
            "links": [source_id] if source_id else [],
            "data": {"lattice_id": lattice_id, "concept_ids": merged_ids, "act": "promote"},
        },
        scope="self",
        persist=False,
    )

    result = {
        "promoted": True,
        "lattice_id": lattice_id,
        "stability": "agent_canon",
        "concept_ids": merged_ids,
        "registry_path": str(agent_canon_registry_path(store_dir)),
        "journal_id": remember.get("journal_id"),
        "source_journal_id": source_id,
    }
    from casa.prisms.memory.agent_canon_field import enqueue_canon_sleep_episodes, sync_agent_canon_to_field

    enqueue_canon_sleep_episodes(
        state,
        lattice_id=lattice_id,
        concept_ids=merged_ids,
        cue=reason or journal_text[:80],
        journal_id=source_id,
    )
    sync_agent_canon_to_field(state, store_dir)
    from casa.prisms.memory.write_gate import record_earned_postulate

    sem = str(spec.get("semantic") or "")
    domain = "math" if "math" in sem or lattice_id.startswith("math-") else "lang"
    if "logic" in sem:
        domain = "logic"
    theory_id = str(spec.get("theory_id") or lattice_id)
    earned = record_earned_postulate(
        state,
        lattice_id=lattice_id,
        domain=domain,
        theory_id=theory_id,
        concept_ids=merged_ids,
        source="promote_canon",
    )
    result["earned_theory"] = earned
    from casa.prisms.memory.canon_nca_train import agent_requests_nca_train_after_canon

    nca_req = agent_requests_nca_train_after_canon(
        store_dir,
        lattice_id,
        reason="agent_canon_promote",
        journal_id=source_id,
    )
    result["nca_train"] = nca_req

    if persist:
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state, force=True)
    return result


def agent_demote_canon_lattice(
    store_dir: Path,
    state: dict[str, Any],
    request: dict[str, Any],
    *,
    persist: bool = True,
) -> dict[str, Any]:
    """Move agent_canon entry back to experiential — agent decision only."""
    lattice_id = canonical_lattice_id(str(request.get("lattice_id") or ""))
    if lattice_id in host_bootstrap_lattice_ids():
        raise ValueError(f"cannot demote host bootstrap lattice {lattice_id!r}")

    drop_ids = {str(c) for c in (request.get("concept_ids") or []) if c}
    reason = str(request.get("reason") or "").strip()
    reg = load_canon_registry(store_dir)
    entries: list[dict[str, Any]] = list(reg.get("entries") or [])
    target = next((e for e in entries if e.get("lattice_id") == lattice_id), None)
    if target is None:
        raise ValueError(f"no agent_canon entry for lattice {lattice_id!r}")

    all_ids = [str(c) for c in (target.get("concept_ids") or []) if c]
    if drop_ids:
        kept = [c for c in all_ids if c not in drop_ids]
    else:
        kept = []
        drop_ids = set(all_ids)
    demoted_snapshot = dict(target)
    demoted_snapshot["demoted_at"] = _utc_now()
    demoted_snapshot["demote_reason"] = reason
    if drop_ids:
        demoted_snapshot["demoted_concept_ids"] = sorted(drop_ids)

    demoted: list[dict[str, Any]] = list(reg.get("demoted") or [])
    if not kept:
        entries = [e for e in entries if e.get("lattice_id") != lattice_id]
        demoted.append(demoted_snapshot)
    else:
        target["concept_ids"] = kept
        target["updated_at"] = _utc_now()
        if drop_ids:
            partial = dict(demoted_snapshot)
            partial["concept_ids"] = sorted(drop_ids)
            demoted.append(partial)

    reg["entries"] = entries
    reg["demoted"] = demoted
    save_canon_registry(store_dir, reg)

    remember = agent_remember(
        store_dir,
        state,
        {
            "kind": "observation",
            "text": reason or f"Снял с canon lattice {lattice_id}.",
            "concepts": sorted(drop_ids) if drop_ids else kept,
            "tags": ["canon-demote", f"canon:{lattice_id}"],
            "data": {"lattice_id": lattice_id, "act": "demote", "remaining": kept},
        },
        scope="self",
        persist=False,
    )

    from casa.prisms.memory.agent_canon_field import sync_agent_canon_to_field

    sync_agent_canon_to_field(state, store_dir)
    if kept:
        from casa.prisms.memory.canon_nca_train import agent_requests_nca_train_after_canon

        result_nca = agent_requests_nca_train_after_canon(
            store_dir,
            lattice_id,
            reason="agent_canon_demote_partial",
            journal_id=remember.get("journal_id"),
        )
    else:
        result_nca = None

    result = {
        "demoted": True,
        "lattice_id": lattice_id,
        "remaining_concept_ids": kept,
        "journal_id": remember.get("journal_id"),
        "nca_train": result_nca,
    }
    if persist:
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state, force=True)
    return result
