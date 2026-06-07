"""Working-memory bind block collection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.prisms.control.fpn_state import WorkingMemory


def collect_wm_blocks(
    store_dir: Path,
    state: dict,
    wm: WorkingMemory,
    q: str,
    blocks: list[dict[str, Any]],
    query_read: Any,
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any] | None, dict[str, float]]:
    """Returns extra blocks, sources, wm_bind report, wm_edge_scores."""
    from casa.domain.load_governor import cognitive_load_from_state
    from casa.prisms.memory.wm import (
        dialogue_focus_concepts,
        fpn_co_place_hints,
        wm_bind_focus_concepts,
        wm_blocks_for_bind,
    )

    wm_bind_rep: dict[str, Any] | None = None
    wm_edge_scores: dict[str, float] = {}
    extra_blocks: list[dict[str, Any]] = []
    sources: list[str] = []

    load = cognitive_load_from_state(state)
    overloaded = bool(load.get("overloaded"))
    sn = state.get("sn") if isinstance(state.get("sn"), dict) else {}
    surprise_before = int(sn.get("surprise") or 0) or None

    focus = dialogue_focus_concepts(store_dir)
    for cid in query_read.concept_hints[:4]:
        if cid and cid not in focus:
            focus.append(cid)
    for cid in fpn_co_place_hints(wm):
        if cid and cid not in focus:
            focus.append(cid)
    for b in blocks:
        cid = str(b.get("concept_id") or "")
        if cid.startswith(("ru.prop.", "passage.", "math.", "agent.world.")):
            if cid not in focus:
                focus.append(cid)

    wm_bind_rep = wm_bind_focus_concepts(
        state,
        focus,
        tick=int(wm.tick),
        overloaded=overloaded,
        surprise_before=surprise_before,
        surprise_after=surprise_before,
        fpn_hints=fpn_co_place_hints(wm),
    )
    wm_blocks = wm_blocks_for_bind(state, q, k=5)
    if wm_blocks:
        extra_blocks.extend(wm_blocks)
        sources.append("wm_prism")

    return extra_blocks, sources, wm_bind_rep, wm_edge_scores
