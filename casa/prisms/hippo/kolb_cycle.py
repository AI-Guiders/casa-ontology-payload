#!/usr/bin/env python3
"""Kolb batch session — math count-row and emergent pattern hub (ADR-0034 B4)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from casa.prisms.memory.memory_prisms import memory_lattices
from casa.prisms.shared.store_persist import mark_runtime_dirty
from casa.prisms.visual.bridge_math import mint_crosslink, math_concept_votes


def _pattern_id(ops: tuple[str, ...]) -> str:
    key = "|".join(sorted(ops))
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"math.pattern.emerged.{digest}"


def _count_row_end(session: dict[str, Any]) -> int:
    return int(session.get("end") or session.get("count_row_end") or 6)


def _kolb_count_row_batch(
    state: dict,
    session: dict[str, Any],
    *,
    bundle: dict | None,
) -> dict[str, Any]:
    """Active experimentation batch: mint pattern hub from math op surprises."""
    start = int(session.get("start") or 1)
    end = _count_row_end(session)
    lats = memory_lattices(state)
    ops: list[str] = []
    for n in range(start, end + 1):
        cid = f"math.num.{n}"
        if math_concept_votes(lats, cid, min_votes=1) > 0:
            ops.append(cid)
    for op in ("math.op.add", "math.op.sub", "math.op.mul"):
        if math_concept_votes(lats, op, min_votes=1) > 0:
            ops.append(op)

    minted: list[dict[str, Any]] = []
    if len(ops) >= 2:
        hub = _pattern_id(tuple(ops))
        for i in range(len(ops) - 1):
            row = mint_crosslink(
                state,
                src=ops[i],
                relation="pattern_step",
                dst=ops[i + 1],
                copies=4,
                provenance="kolb_count_row",
            )
            if row:
                minted.append(row)
        hub_row = mint_crosslink(
            state,
            src=ops[0],
            relation="emerges",
            dst=hub,
            copies=5,
            provenance="kolb_count_row",
        )
        if hub_row:
            minted.append(hub_row)
    else:
        hub = None

    rep = {
        "kind": "kolb_count_row",
        "count_row": {"start": start, "end": end},
        "ops_considered": ops,
        "pattern_hub": hub,
        "minted": minted,
        "surprises": 1 if minted else 0,
        "active_passed": bool(minted),
    }
    mark_runtime_dirty(state)
    return rep


def kolb_cycle(
    state: dict,
    session: dict[str, Any],
    *,
    bundle: dict | None = None,
) -> dict[str, Any] | None:
    """Optional batch Kolb hook (--kolb-session), not every tick."""
    if not session:
        return None
    kind = str(session.get("kind") or "kolb_count_row")
    if kind == "kolb_count_row":
        rep = _kolb_count_row_batch(state, session, bundle=bundle)
    else:
        return {"skipped": True, "reason": f"unknown_kind:{kind}"}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    kolb_meta = state.setdefault("kolb_batch", {})
    if isinstance(kolb_meta, dict):
        kolb_meta.update(
            {
                "last_at": now,
                "last_kind": kind,
                "last_summary": {
                    "surprises": rep.get("surprises"),
                    "active_passed": rep.get("active_passed"),
                },
                "last_pattern_hub": rep.get("pattern_hub"),
            }
        )
    return rep
