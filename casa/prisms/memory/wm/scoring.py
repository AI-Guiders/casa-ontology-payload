"""Working Memory Prism — edge scoring and tract boosts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .lattice import lattice_meta, wm_root
from .model import PARTNER_CALLBACK_CUES, tokenize
from .policy import get_wm_policy


def partner_callback_hit(query: str, edge: dict[str, Any]) -> bool:
    ql = query.lower()
    if not any(cue in ql for cue in PARTNER_CALLBACK_CUES):
        return False
    qt = tokenize(query)
    for concept in (edge.get("from_concept"), edge.get("to_concept")):
        tail = str(concept or "").rsplit(".", 1)[-1].lower()
        if tail and tail in qt:
            return True
    return False


def compute_edge_score(
    edge: dict[str, Any],
    weights: dict[str, float],
    *,
    turn_paste: float | None,
    query: str | None,
) -> float:
    activations = [int(x) for x in (edge.get("activations") or [])]
    unique_ticks = len(set(activations))
    score = 0.35
    if unique_ticks >= 2:
        score += float(weights.get("reuse", 0.25))
    elif unique_ticks <= 1:
        score += float(weights.get("one_shot", -0.30))

    sb = edge.get("surprise_before")
    sa = edge.get("surprise_after")
    if sb is not None and sa is not None and int(sa) < int(sb):
        score += float(weights.get("surprise_drop", 0.20))

    mods = set(edge.get("modalities") or [])
    if len(mods.intersection({"dialogue", "text", "vis", "math"})) >= 2:
        score += float(weights.get("cross_cue", 0.20))

    if query and partner_callback_hit(query, edge):
        edge["partner_hits"] = int(edge.get("partner_hits") or 0) + 1
        score += float(weights.get("partner_callback", 0.15))

    if turn_paste is not None:
        if turn_paste > 0.5:
            score += float(weights.get("high_paste", -0.25))
        else:
            score += float(weights.get("anti_paste", 0.10))

    return max(0.0, min(1.0, round(score, 4)))


def score_wm_edges(
    state: dict,
    *,
    tick: int,
    turn_paste: float | None = None,
    edge_ids: list[str] | None = None,
    store_dir: Path | None = None,
    query: str | None = None,
    surprise_before: int | None = None,
    surprise_after: int | None = None,
) -> dict[str, float]:
    policy = get_wm_policy(state, store_dir)
    weights = policy.get("score_weights") or {}
    snapshot: dict[str, float] = {}
    root = wm_root(state)
    targets = edge_ids or []
    if not targets:
        for meta in root.values():
            targets.extend(list((meta.get("edges") or {}).keys()))

    for lid, meta in root.items():
        edges = meta.get("edges") or {}
        for eid in list(targets):
            edge = edges.get(eid)
            if not edge:
                continue
            if turn_paste is not None and tick in (edge.get("activations") or []):
                edge["paste_turns"] = int(edge.get("paste_turns") or 0) + 1
                if turn_paste > 0.5:
                    edge["high_paste_turns"] = int(edge.get("high_paste_turns") or 0) + 1
            if surprise_before is not None and edge.get("surprise_before") is None:
                edge["surprise_before"] = int(surprise_before)
            if surprise_after is not None:
                edge["surprise_after"] = int(surprise_after)
            sigma = compute_edge_score(edge, weights, turn_paste=turn_paste, query=query)
            edge["score"] = sigma
            snapshot[eid] = sigma
            theta_hold = float(policy.get("theta_hold", 0.45))
            if sigma >= theta_hold and edge.get("tier") == "scratch":
                edge["tier"] = "episode_candidate"
        meta["last_tick"] = tick
    return snapshot


def wm_tract_boosts(state: dict, query: str) -> dict[str, int]:
    from .bind import wm_blocks_for_bind

    blocks = wm_blocks_for_bind(state, query, k=3)
    if not blocks:
        return {}
    top = max(int(b.get("score") or 0) for b in blocks)
    if top < 12:
        return {}
    boost = min(28, top // 2 + 4)
    ql = query.lower()
    if any(m in ql for m in ("позици", "почему", "связ", "контекст", "продолж", "говорил", "напомни")):
        return {"discuss": boost, "social": boost // 2, "journal": boost // 3}
    if any(b.get("slots", {}).get("tier") == "episode" for b in blocks if isinstance(b.get("slots"), dict)):
        return {"journal": boost // 2, "recall": boost}
    return {"social": boost, "general": boost // 3}
