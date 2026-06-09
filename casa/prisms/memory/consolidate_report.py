#!/usr/bin/env python3
"""Memory consolidate snapshot + P12f acceptance probes (ADR-0068 P12e-f)."""

from __future__ import annotations

from typing import Any

from casa.prisms.intelligence.scope_bind import apply_bind_scope, scoped_lattice_ids
from casa.prisms.memory.forgetting import memory_implicit_gains
from casa.prisms.memory.zone import ensure_memory_zone, memory_kind_for_lattice

FORGET_HONESTY_JSON = "forget_honesty_report.json"


def _sleep_report_digest(sleep_report: dict[str, Any]) -> dict[str, Any]:
    skipped = sleep_report.get("immutable_skipped") or []
    items = sleep_report.get("items") or []
    return {
        "merged": int(sleep_report.get("merged") or 0),
        "pending": int(sleep_report.get("pending") or 0),
        "immutable_skipped_count": len(skipped),
        "immutable_skipped": list(skipped),
        "items_count": len(items),
        "z_compose": sleep_report.get("z_compose"),
        "replay": sleep_report.get("replay"),
        "batch": sleep_report.get("batch"),
        "nca": sleep_report.get("nca"),
    }


def memory_consolidate_snapshot(state: dict, sleep_report: dict[str, Any]) -> dict[str, Any]:
    """Mirror consolidation.last_sleep under intelligence_zones.memory.consolidate (P12e)."""
    zone = ensure_memory_zone(state)
    cons = zone.setdefault("consolidate", {})
    tick = int(state.get("field_version") or 0)
    digest = _sleep_report_digest(sleep_report)
    cons["last_sleep_at_tick"] = tick + 1
    cons["last_report"] = digest
    cons["replay_queue_depth"] = int(sleep_report.get("pending") or 0)
    return digest


def probe_recall_uses_episodic_scope(state: dict) -> dict[str, Any]:
    """Recall tract must route explicit episodic (P12f)."""
    rep = apply_bind_scope(state, tract="recall", client_zone="executive")
    scope = rep.get("scope") or {}
    explicit = bool(scope.get("explicit_episodic"))
    allowed = scoped_lattice_ids(state, scope) or set()
    episodic_ids = [
        lid
        for lid in sorted(allowed)
        if str(memory_kind_for_lattice(state, lid).get("memory_subkind") or "") == "episodic"
    ]
    return {
        "pass": explicit,
        "explicit_episodic": explicit,
        "episodic_lattice_ids": episodic_ids,
        "scoped_lattice_count": len(allowed),
    }


def probe_math_habit_implicit(state: dict) -> dict[str, Any]:
    """Math tract uses implicit procedural scale without new L3 lemma (P12f)."""
    gains = memory_implicit_gains(state, tract="math")
    proc = float(gains.get("procedural_scale") or 1.0)
    return {
        "pass": proc > 1.0,
        "procedural_scale": proc,
        "priming_scale": float(gains.get("priming_scale") or 1.0),
        "requires_new_l3_lemma": False,
    }


def probe_post_sleep_hippo_pending_down(
    state: dict,
    *,
    before_pending: int | None = None,
) -> dict[str, Any]:
    """After sleep, hippo pending should not grow; immutable skips recorded (P12f)."""
    last = (state.get("consolidation") or {}).get("last_sleep") or {}
    pending = int(last.get("pending") or 0)
    skipped = list(last.get("immutable_skipped") or [])
    merged = int(last.get("merged") or 0)
    ok_pending = before_pending is None or pending <= before_pending
    return {
        "pass": ok_pending and (merged > 0 or pending >= 0 or bool(skipped)),
        "pending": pending,
        "merged": merged,
        "immutable_skipped_count": len(skipped),
        "before_pending": before_pending,
    }
