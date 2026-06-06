#!/usr/bin/env python3
"""Boot/sleep repair scheduler — NCA regrow + field sync when repair_pending (ADR-0042)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.domain.agent_field import field_db_stats, load_field_from_db, save_field_to_db
from casa.domain.consistency_oracle import assess_field_consistency
from casa.domain.routing import Router
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices, persist_content_lattices


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repair_pending(state: dict) -> bool:
    cons = state.get("consolidation") if isinstance(state.get("consolidation"), dict) else {}
    return bool(cons.get("repair_pending"))


def _sync_routes_from_db(state: dict, store_dir: Path) -> dict[str, Any] | None:
    stats = field_db_stats(store_dir)
    if not stats.get("ok"):
        return None
    db_state = load_field_from_db(store_dir)
    if db_state is None:
        return None
    db_state = ensure_prisms(db_state)
    routes = Router.bind(db_state).routes()
    Router.bind(state).set_routes(routes)
    fv = int(db_state.get("field_version") or state.get("field_version") or 0)
    state["field_version"] = fv
    save_field_to_db(store_dir, state)
    return {"kind": "sync_routes_from_db", "field_version": fv, "routes": len(routes)}


def _regrow_nca_shards(
    state: dict,
    store_dir: Path,
    *,
    max_shards: int = 8,
    device: str = "cpu",
) -> list[dict[str, Any]]:
    from casa.prisms.memory.nca_repair import nca_regrow_lattice
    from casa.prisms.shared.nca_registry import find_stale_shards, model_path_for_lattice, wire_legacy_nca_paths

    wire_legacy_nca_paths(store_dir, state)
    stale = find_stale_shards(state, store_dir, repair_smoke=False, min_tokens=1)
    if not stale:
        from casa.prisms.memory.lexicon_shard import l2_lexicon_lattice_ids, nca_model_registry

        for lid in l2_lexicon_lattice_ids(state)[:max_shards]:
            if model_path_for_lattice(store_dir, state, lid):
                stale.append({"lattice_id": lid, "reasons": ["repair_pending_sweep"]})

    lattices = memory_lattices(state)
    rows: list[dict[str, Any]] = []
    for item in stale[:max_shards]:
        lid = str(item.get("lattice_id") or "")
        if not lid or lid not in lattices:
            rows.append({"lattice_id": lid, "skipped": True, "reason": "missing_lattice"})
            continue
        model = model_path_for_lattice(store_dir, state, lid)
        if model is None or not model.is_file():
            rows.append({"lattice_id": lid, "skipped": True, "reason": "missing_model"})
            continue
        try:
            rep = nca_regrow_lattice(lattices[lid], model, device=device)
            lattices[lid] = rep["lattice"]
            rows.append(
                {
                    "lattice_id": lid,
                    "ok": True,
                    "w_before": rep.get("w_before"),
                    "w_after": rep.get("w_after"),
                    "reasons": item.get("reasons"),
                }
            )
        except Exception as exc:  # noqa: BLE001 — sleep repair must not abort merge
            rows.append({"lattice_id": lid, "ok": False, "error": str(exc)})

    if rows:
        persist_content_lattices(state, lattices)
        state.setdefault("nca", {})["last_repair"] = {
            "at": _utc_now(),
            "mode": "sleep_regrow",
            "shards": len(rows),
        }
    return rows


def _calm_surprise(state: dict) -> None:
    sn = state.setdefault("sn", {})
    prev = int(sn.get("surprise") or 0)
    if prev >= 100:
        sn["surprise"] = 24
    sn.pop("consistency_mismatch", None)


def _persist_repair_meta(store_dir: Path, report: dict[str, Any]) -> None:
    from casa.prisms.control.fpn_state import read_session_meta, write_session_meta

    meta = read_session_meta(store_dir)
    meta["last_consistency_repair_at"] = report.get("at")
    meta["last_consistency_repair_ok"] = bool(report.get("ok"))
    meta["last_consistency_repair_steps"] = len(report.get("steps") or [])
    write_session_meta(store_dir, meta)


def run_consistency_repair_on_sleep(
    state: dict,
    store_dir: Path,
    *,
    max_nca_shards: int = 8,
    device: str = "cpu",
) -> dict[str, Any]:
    """Run after hippo merge when consolidation.repair_pending is set."""
    store_dir = store_dir.resolve()
    cons = state.setdefault("consolidation", {})
    reasons = list(cons.get("repair_reason") or [])
    steps: list[dict[str, Any]] = []

    if any("field_db" in r or "routes_db" in r for r in reasons):
        step = _sync_routes_from_db(state, store_dir)
        if step:
            steps.append(step)

    nca_rows = _regrow_nca_shards(state, store_dir, max_shards=max_nca_shards, device=device)
    if nca_rows:
        steps.append({"kind": "nca_regrow", "shards": nca_rows})

    after = assess_field_consistency(store_dir, state)
    critical = [
        m
        for m in after.get("mismatches") or []
        if "field_db" in m or "routes_db" in m or "ltm_zeroed" in m
    ]
    cons["repair_pending"] = bool(critical)
    cons["repair_reason"] = critical if critical else []
    cons["last_repair_at"] = _utc_now()
    if critical:
        _calm_surprise(state)
    else:
        _calm_surprise(state)
        cons.pop("repair_deferred", None)

    report: dict[str, Any] = {
        "schema_version": 1,
        "tool": "consistency_repair_on_sleep",
        "at": cons["last_repair_at"],
        "trigger_reasons": reasons,
        "steps": steps,
        "nca_shards": len(nca_rows),
        "after_consistency": after,
        "ok": not critical,
    }
    cons["last_repair_report"] = {
        "at": report["at"],
        "ok": report["ok"],
        "steps": len(steps),
        "nca_shards": len(nca_rows),
    }
    _persist_repair_meta(store_dir, report)
    return report
