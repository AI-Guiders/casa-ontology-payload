#!/usr/bin/env python3
"""Memory forgetting hooks — speed-1 priming @ tick (ADR-0070 P15b / ADR-0068 P12d)."""

from __future__ import annotations

from typing import Any

from casa.prisms.memory.zone import ensure_memory_zone

DEFAULT_PRIMING_ALPHA = 0.2
PRIMING_FLOOR = 0.01
PRIMING_BOOST_SCALE = 10


def _priming_block(state: dict) -> dict[str, Any]:
    zone = ensure_memory_zone(state)
    implicit = zone.setdefault("implicit", {})
    prim = implicit.setdefault("priming", {})
    if not isinstance(prim.get("cells"), dict):
        prim["cells"] = {}
    prim.setdefault("alpha_retain", DEFAULT_PRIMING_ALPHA)
    prim.setdefault("bind_decay_halflife_ticks", 6)
    return prim


def priming_alpha_retain(state: dict) -> float:
    """α for speed-1 decay; genetic_constant override reserved for P6c."""
    prim = (ensure_memory_zone(state).get("implicit") or {}).get("priming") or {}
    raw = prim.get("alpha_retain")
    if raw is not None:
        return float(raw)
    try:
        from casa.prisms.genetic.zone import genetic_constant

        val = genetic_constant(state, "forgetting.implicit.priming_alpha_retain")
        if val is not None:
            return float(val)
    except (ImportError, AttributeError, TypeError, ValueError):
        pass
    return DEFAULT_PRIMING_ALPHA


def memory_priming_decay(state: dict, *, tick: int | None = None) -> dict[str, Any]:
    """Speed-1: activation[t+1] = α × activation[t] on implicit priming cells."""
    prim = _priming_block(state)
    alpha = priming_alpha_retain(state)
    prim["alpha_retain"] = alpha
    cells: dict[str, float] = {str(k): float(v) for k, v in (prim.get("cells") or {}).items() if k}
    decayed = 0
    kept: dict[str, float] = {}
    for cid, act in cells.items():
        new_act = act * alpha
        if new_act >= PRIMING_FLOOR:
            kept[cid] = round(new_act, 6)
        else:
            decayed += 1
    prim["cells"] = kept
    fv = int(tick if tick is not None else state.get("field_version") or 0)
    prim["last_decay_tick"] = fv
    prim["decayed_last"] = decayed
    prim["active_count"] = len(kept)
    rep = {
        "alpha_retain": alpha,
        "decayed": decayed,
        "active_count": len(kept),
        "tick": fv,
    }
    forget = state.setdefault("forgetting", {})
    forget["speed1_last"] = rep
    return rep


def memory_priming_touch(
    state: dict,
    concept_ids: list[str],
    *,
    tick: int | None = None,
    weight: float = 1.0,
) -> dict[str, Any]:
    """Refresh priming activation after bind (re-bind resets flash)."""
    prim = _priming_block(state)
    cells: dict[str, float] = dict(prim.get("cells") or {})
    touched = 0
    w = max(0.0, float(weight))
    for raw in concept_ids:
        cid = str(raw or "").strip()
        if not cid:
            continue
        cells[cid] = max(float(cells.get(cid) or 0), w)
        touched += 1
    prim["cells"] = cells
    fv = int(tick if tick is not None else state.get("field_version") or 0)
    prim["last_activation_tick"] = fv
    prim["active_count"] = len(cells)
    return {"touched": touched, "active_count": len(cells), "tick": fv}


def memory_priming_boost_block_scores(state: dict, blocks: list[dict[str, Any]]) -> int:
    """Apply residual priming as bind score boost (implicit flash → explicit bind)."""
    prim = (ensure_memory_zone(state).get("implicit") or {}).get("priming") or {}
    cells = prim.get("cells") or {}
    if not cells:
        return 0
    boosted = 0
    for row in blocks:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("concept_id") or "")
        act = float(cells.get(cid) or 0)
        if act < PRIMING_FLOOR:
            continue
        base = int(row.get("score") or 0)
        row["score"] = base + int(act * PRIMING_BOOST_SCALE)
        row["priming_boost"] = round(act, 4)
        boosted += 1
    return boosted


def memory_implicit_gains(state: dict, *, tract: str = "general") -> dict[str, Any]:
    """Tract-scoped scales for priming / procedural bind (P12d)."""
    tract_key = str(tract or "general").strip().lower()
    alpha = priming_alpha_retain(state)
    gains: dict[str, Any] = {
        "tract": tract_key,
        "priming_alpha_retain": alpha,
        "priming_scale": 1.0,
        "procedural_scale": 1.0,
    }
    if tract_key in ("math", "schema", "predict"):
        gains["procedural_scale"] = 1.15
    if tract_key in ("social", "discuss", "recall", "journal", "general"):
        gains["priming_scale"] = 1.2
    if tract_key == "math":
        gains["priming_scale"] = 0.9
    meta = state.setdefault("meta", {})
    meta["memory_implicit_gains"] = gains
    return gains


def memory_priming_record_bind(
    state: dict,
    blocks: list[dict[str, Any]],
    *,
    tick: int | None = None,
    top_n: int = 12,
    min_score: int = 5,
) -> dict[str, Any]:
    """After bind: boost from prior priming, then touch winners for next tick."""
    boosted = memory_priming_boost_block_scores(state, blocks)
    ranked = sorted(
        [b for b in blocks if isinstance(b, dict) and int(b.get("score") or 0) >= min_score],
        key=lambda r: int(r.get("score") or 0),
        reverse=True,
    )
    cids = [str(r.get("concept_id") or "") for r in ranked[:top_n] if r.get("concept_id")]
    touch = memory_priming_touch(state, cids, tick=tick, weight=1.0)
    return {"boosted": boosted, **touch}
