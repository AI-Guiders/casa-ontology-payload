#!/usr/bin/env python3
"""Carrier (body) health — subsystem status for the subject (ADR-0037)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.domain.hypothesis_queue import open_hypothesis_count
from casa.domain.load_governor import assess_cognitive_load
from casa.domain.self_model import self_model_summary
from casa.prisms.control.fpn_state import WorkingMemory
from casa.domain.prism_wire import prism_hippo


def assess_carrier_health(
    state: dict,
    wm: WorkingMemory | None = None,
    *,
    store_dir: Path | None = None,
    include_nca: bool = False,
) -> dict[str, Any]:
    """Panel 2: can the carrier act? wiring, vegetative, life support."""
    wm = wm or WorkingMemory()
    load = assess_cognitive_load(state, wm)
    hippo = prism_hippo(state)
    pending = sum(1 for e in hippo.get("episodes") or [] if not e.get("consolidated"))
    cons = state.get("consolidation") if isinstance(state.get("consolidation"), dict) else {}
    ticks_since_sleep = int(cons.get("ticks_since_sleep") or 0)
    sn = state.get("sn") if isinstance(state.get("sn"), dict) else {}
    self_check = sn.get("self_check") if isinstance(sn.get("self_check"), dict) else {}

    act_rollout = sn.get("last_act_rollout") if isinstance(sn.get("last_act_rollout"), dict) else {}
    decode_ok = int(state.get("field_version") or 0) > 0

    stale_nca = 0
    if include_nca and store_dir is not None:
        try:
            from casa.prisms.shared.nca_registry import find_stale_shards

            stale_nca = len(find_stale_shards(state, store_dir.resolve(), repair_smoke=False, min_tokens=1))
        except Exception:
            stale_nca = -1

    warnings: list[str] = []
    if store_dir is not None:
        from casa.domain.store_recovery import recovery_warnings_from_session

        warnings.extend(recovery_warnings_from_session(store_dir))
        from casa.domain.journal_wal import recovery_warnings_from_session as journal_wal_warnings

        warnings.extend(journal_wal_warnings(store_dir))
    if load.get("overloaded"):
        warnings.append("cognitive_overload")
    if pending >= 8:
        warnings.append("hippo_backlog")
    if ticks_since_sleep >= 20 and pending > 0:
        warnings.append("sleep_debt")
    if self_check.get("defer_cen"):
        warnings.append("defer_cen_metacog")
    if stale_nca > 5:
        warnings.append("nca_stale_shards")

    subsystems = {
        "decode": {
            "ok": decode_ok,
            "field_version": int(state.get("field_version") or 0),
        },
        "wiring": {
            "sn_mode": sn.get("last_sn_mode") or wm.mode,
            "routing_chain": bool(sn.get("routing_chain")),
            "step_capability": wm.step_capability,
        },
        "act": {
            "last_rollout_skipped": act_rollout.get("skipped"),
            "last_rollout_reason": act_rollout.get("reason"),
        },
        "vegetative": {
            "load": load,
            "hippo_pending": pending,
            "open_hypotheses": open_hypothesis_count(state),
            "ticks_since_sleep": ticks_since_sleep,
        },
        "life_support": {
            "runtime_dirty": bool(state.get("_runtime_dirty")),
            "stale_nca_shards": stale_nca if include_nca else None,
            "self_model": self_model_summary(state),
        },
        "metacog": self_check,
    }

    ok = decode_ok and not load.get("overloaded") and stale_nca <= 5
    return {
        "panel": "body",
        "ok": ok,
        "warnings": warnings,
        "subsystems": subsystems,
    }
