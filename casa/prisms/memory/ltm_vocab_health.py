#!/usr/bin/env python3
"""LTM layout aspect — u16 vocab cap per lattice (kernel aspect `ltm_layout`)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.prisms.memory.l2_remigrate import LTM_VOCAB_U16_MAX, ensure_l2_sharded_for_export, needs_l2_remigrate
from casa.prisms.memory.l3_remigrate import ensure_l3_sharded_for_export, needs_l3_remigrate
from casa.prisms.memory.lexicon_shard import lattice_vocab_size
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices

LTM_VOCAB_WARN_RATIO = 0.9
LTM_VOCAB_WARN_AT = int(LTM_VOCAB_U16_MAX * LTM_VOCAB_WARN_RATIO)

OP_ENSURE_L2_SHARDS = "kernel.ensure_l2_sharded_for_export"
OP_COMPACT_PERSIST = "kernel.compact_persist_store"
OP_L3_PHRASE_SHARD = "kernel.ensure_l3_sharded_for_export"


def scan_ltm_layout(state: dict) -> dict[str, Any]:
    """Scan content lattices for u16 vocab pressure (warn ≥90%, over cap)."""
    state = ensure_prisms(state)
    warn_rows: list[dict[str, Any]] = []
    over_rows: list[dict[str, Any]] = []

    for lid in sorted(memory_lattices(state)):
        lat = memory_lattices(state).get(lid) or {}
        if not isinstance(lat, dict):
            continue
        n = lattice_vocab_size(lat)
        if n == 0:
            continue
        pct = round(100.0 * n / LTM_VOCAB_U16_MAX, 1)
        row: dict[str, Any] = {
            "lattice_id": lid,
            "vocab": n,
            "cap": LTM_VOCAB_U16_MAX,
            "pct_of_cap": pct,
        }
        if n > LTM_VOCAB_U16_MAX:
            row["kernel_op"] = OP_L3_PHRASE_SHARD if lid.startswith("L3_") else OP_ENSURE_L2_SHARDS
            over_rows.append(row)
        elif n >= LTM_VOCAB_WARN_AT:
            row["kernel_op"] = "kernel.plan_re_shard"
            warn_rows.append(row)

    remigrate_l2 = needs_l2_remigrate(state)
    remigrate_l3 = needs_l3_remigrate(state)
    pending_ops: list[str] = []
    if remigrate_l2:
        pending_ops.append(OP_ENSURE_L2_SHARDS)
    if remigrate_l3:
        pending_ops.append(OP_L3_PHRASE_SHARD)
    for row in over_rows:
        op = row.get("kernel_op")
        if op and op not in pending_ops:
            pending_ops.append(str(op))

    return {
        "ok": not over_rows,
        "warn": bool(warn_rows) or remigrate_l2 or remigrate_l3,
        "cap": LTM_VOCAB_U16_MAX,
        "warn_at": LTM_VOCAB_WARN_AT,
        "needs_l2_remigrate": remigrate_l2,
        "needs_l3_remigrate": remigrate_l3,
        "near_cap": warn_rows,
        "over_cap": over_rows,
        "pending_kernel_ops": pending_ops,
    }


def ltm_layout_checks(state: dict, scan: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rep = scan or scan_ltm_layout(state)
    checks: list[dict[str, Any]] = [
        {
            "id": "ltm_vocab_over_cap",
            "aspect": "ltm_layout",
            "ok": not rep["over_cap"],
            "detail": {
                "lattices": rep["over_cap"],
                "cap": rep["cap"],
                "pending_kernel_ops": rep.get("pending_kernel_ops"),
            },
        }
    ]
    if rep["needs_l2_remigrate"]:
        checks.append(
            {
                "id": "ltm_l2_monolith_remigrate",
                "aspect": "ltm_layout",
                "ok": False,
                "warn": True,
                "detail": {"needs_l2_remigrate": True, "kernel_op": OP_ENSURE_L2_SHARDS},
            }
        )
    if rep.get("needs_l3_remigrate"):
        checks.append(
            {
                "id": "ltm_l3_monolith_remigrate",
                "aspect": "ltm_layout",
                "ok": False,
                "warn": True,
                "detail": {"needs_l3_remigrate": True, "kernel_op": OP_L3_PHRASE_SHARD},
            }
        )
    if rep["near_cap"]:
        checks.append(
            {
                "id": "ltm_vocab_soft",
                "aspect": "ltm_layout",
                "ok": True,
                "warn": True,
                "detail": {"warn_at": rep["warn_at"], "lattices": rep["near_cap"]},
            }
        )
    if rep.get("pending_kernel_ops"):
        checks.append(
            {
                "id": "ltm_layout_pending_ops",
                "aspect": "ltm_layout",
                "ok": False if (rep["needs_l2_remigrate"] or rep.get("needs_l3_remigrate")) else True,
                "warn": True,
                "detail": {"kernel_ops": rep["pending_kernel_ops"]},
            }
        )
    return checks


def maintain_ltm_layout(
    state: dict,
    store_dir: Path | None = None,
    *,
    auto_repair_l2: bool = True,
    auto_repair_l3: bool = True,
    auto_compact: bool = False,
    skip_vocab_over: int | None = LTM_VOCAB_U16_MAX,
    on_token_progress: Any = None,
    progress_every: int = 5000,
    report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Repair L2 monolith → shards in RAM; optional compact to store/ltm/."""
    state = ensure_prisms(state)
    before = scan_ltm_layout(state)
    out: dict[str, Any] = {
        "aspect": "ltm_layout",
        "status": "noop",
        "before": before,
        "repaired": [],
        "deferred": [],
    }

    if auto_repair_l2 and before.get("needs_l2_remigrate"):
        rem = ensure_l2_sharded_for_export(state)
        out["repaired"].append({"op": OP_ENSURE_L2_SHARDS, "report": rem})
        out["status"] = "repaired_l2"

    mid = scan_ltm_layout(state)
    if auto_repair_l3 and mid.get("needs_l3_remigrate"):
        rem3 = ensure_l3_sharded_for_export(
            state,
            on_token_progress=on_token_progress,
            progress_every=progress_every,
        )
        out["repaired"].append({"op": OP_L3_PHRASE_SHARD, "report": rem3})
        out["status"] = "repaired_l3" if out["status"] == "noop" else out["status"] + "+l3"

    after = scan_ltm_layout(state)
    out["after"] = after

    for row in after.get("over_cap") or []:
        lid = str(row.get("lattice_id") or "")
        if lid.startswith("L3_") and auto_repair_l3:
            out["deferred"].append(
                {
                    "lattice_id": lid,
                    "reason": "l3_shard_still_over_cap",
                    "kernel_op": OP_L3_PHRASE_SHARD,
                }
            )
        elif not lid.startswith("L3_"):
            out["deferred"].append(
                {
                    "lattice_id": lid,
                    "reason": "single_lattice_over_u16",
                    "kernel_op": row.get("kernel_op"),
                }
            )

    if auto_compact and store_dir is not None:
        from casa.prisms.shared.compact_persist import compact_persist_store

        cp = compact_persist_store(
            store_dir,
            state,
            reason="kernel_ltm_layout_maintain",
            skip_vocab_over=skip_vocab_over,
            remigrate_l2=False,
            remigrate_l3=False,
        )
        out["repaired"].append({"op": OP_COMPACT_PERSIST, "report": cp})
        if out["status"] == "noop":
            out["status"] = "compact_persist"

    unresolved = [
        r
        for r in after.get("over_cap") or []
        if not str(r.get("lattice_id") or "").startswith("L3_")
    ]
    out["ok"] = len(unresolved) == 0
    if unresolved:
        out["status"] = "needs_kernel_ops"
    elif after.get("near_cap"):
        out.setdefault("status", "warn_near_cap")

    if report is not None:
        report["ltm_layout_maintain"] = out
    return out


# Legacy names
ltm_vocab_shard_health = scan_ltm_layout
ltm_vocab_health_checks = ltm_layout_checks
maintain_ltm_vocab_health = maintain_ltm_layout
