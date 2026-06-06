#!/usr/bin/env python3
"""Consistency oracle — field_version / journal / db / ltm cross-check (ADR-0041)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa.domain.agent_field import field_db_stats
from casa.domain.journal_wal import load_checkpoint
from casa.domain.store_recovery import is_zeroed_file
from casa.prisms.shared.runtime_checkpoint import _peek_field_version
from casa.prisms.shared.store_layout import field_state_path, ltm_root


def _journal_field_version(store_dir: Path) -> int | None:
    checkpoint = load_checkpoint(store_dir)
    domains = checkpoint.get("domains") or {}
    versions = []
    for dom in domains.values():
        if isinstance(dom, dict) and dom.get("field_version") is not None:
            try:
                versions.append(int(dom["field_version"]))
            except (TypeError, ValueError):
                continue
    return max(versions) if versions else None


def _ltm_shard_issues(store_dir: Path) -> list[str]:
    from casa.domain.store_recovery import load_ltm_pack_manifest

    ltm = ltm_root(store_dir)
    manifest = load_ltm_pack_manifest(ltm, store_dir=store_dir)
    lattices = manifest.get("lattices") or {}
    issues: list[str] = []
    for lid, spec in lattices.items():
        if not isinstance(spec, dict):
            continue
        rel = spec.get("path") or spec.get("file")
        if not rel:
            continue
        path = ltm / str(rel) if not str(rel).startswith("/") else Path(str(rel))
        if path.is_file() and is_zeroed_file(path):
            issues.append(str(lid))
    return issues[:16]


def collect_version_sources(store_dir: Path, state: dict) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    sources: dict[str, Any] = {
        "state": int(state.get("field_version") or 0),
    }
    db = field_db_stats(store_dir)
    sources["field_db"] = db
    if db.get("field_version") is not None:
        sources["field_db_version"] = int(db["field_version"])

    fs = field_state_path(store_dir)
    if fs.is_file():
        fv = _peek_field_version(fs)
        if fv is not None:
            sources["field_state"] = int(fv)

    jfv = _journal_field_version(store_dir)
    if jfv is not None:
        sources["journal_checkpoint"] = jfv

    try:
        from casa.domain.routing import Router

        sources["route_count_state"] = len(Router.bind(state).routes())
    except Exception:
        sources["route_count_state"] = 0
    if db.get("ok"):
        sources["route_count_db"] = int(db.get("routes") or 0)

    return sources


def assess_field_consistency(store_dir: Path, state: dict) -> dict[str, Any]:
    """Compare durable sources; journal lag is warning, db/state split is error."""
    sources = collect_version_sources(store_dir, state)
    mismatches: list[str] = []
    warnings: list[str] = []

    fv_state = int(sources.get("state") or 0)
    fv_db = sources.get("field_db_version")
    fv_fs = sources.get("field_state")
    fv_journal = sources.get("journal_checkpoint")

    if fv_db is not None and fv_db != fv_state:
        mismatches.append(f"field_db:{fv_db}_vs_state:{fv_state}")
    if fv_fs is not None and fv_fs != fv_state:
        mismatches.append(f"field_state:{fv_fs}_vs_state:{fv_state}")
    if fv_journal is not None and fv_journal > fv_state:
        mismatches.append(f"journal_ahead:{fv_journal}_vs_state:{fv_state}")
    elif fv_journal is not None and fv_state - fv_journal > 64:
        warnings.append(f"journal_lag:{fv_journal}_behind_state:{fv_state}")

    rc_state = int(sources.get("route_count_state") or 0)
    rc_db = sources.get("route_count_db")
    if rc_db is not None and rc_db != rc_state:
        mismatches.append(f"routes_db:{rc_db}_vs_state:{rc_state}")

    zeroed = _ltm_shard_issues(store_dir)
    if zeroed:
        mismatches.append(f"ltm_zeroed_shards:{len(zeroed)}")

    ok = not mismatches
    return {
        "schema_version": 1,
        "tool": "consistency_oracle",
        "ok": ok,
        "sources": sources,
        "mismatches": mismatches,
        "warnings": warnings,
        "repair_recommended": bool(mismatches),
    }


def apply_repair_homeostasis(state: dict, report: dict[str, Any]) -> dict[str, Any]:
    """Surprise spike + repair_pending — triggers sleep-merge / NCA path, not crash."""
    if not report.get("repair_recommended"):
        return {"applied": False}

    sn = state.setdefault("sn", {})
    prev = int(sn.get("surprise") or 0)
    sn["surprise"] = max(prev, 100)
    sn["consistency_mismatch"] = True

    cons = state.setdefault("consolidation", {})
    cons["repair_pending"] = True
    cons["repair_reason"] = list(report.get("mismatches") or [])

    return {"applied": True, "surprise": sn["surprise"], "reasons": cons["repair_reason"]}


def persist_consistency_note(store_dir: Path, report: dict[str, Any]) -> None:
    from casa.prisms.control.fpn_state import read_session_meta, write_session_meta

    meta = read_session_meta(store_dir)
    meta["last_consistency_check_ok"] = bool(report.get("ok"))
    meta["last_consistency_mismatches"] = list(report.get("mismatches") or [])
    write_session_meta(store_dir, meta)


def recovery_warnings_from_consistency(store_dir: Path) -> list[str]:
    from casa.prisms.control.fpn_state import read_session_meta

    meta = read_session_meta(store_dir)
    warnings: list[str] = []
    if meta.get("last_consistency_check_ok") is False:
        warnings.append("field_consistency_mismatch")
    if meta.get("last_consistency_mismatches"):
        warnings.append("repair_pending")
    return warnings
