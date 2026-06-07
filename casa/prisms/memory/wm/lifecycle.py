"""Working Memory Prism — turn and sleep lifecycle hooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.tick.articulation_realize import paste_ratio

from .lattice import prune_wm_lattice, wm_root
from .policy import get_wm_policy
from .promote import promote_edge_to_hippo_episode
from .scoring import score_wm_edges


def wm_on_sleep_boundary(
    state: dict,
    store_dir: Path | None = None,
) -> dict[str, Any]:
    """Consolidate WM episode candidates → hippo; no auto world promote (ADR-0055)."""
    policy = get_wm_policy(state, store_dir)
    theta_hold = float(policy.get("theta_hold", 0.45))
    promoted_episodes: list[str] = []
    candidates: list[str] = []
    root = wm_root(state)

    for lid, meta in root.items():
        for eid, edge in (meta.get("edges") or {}).items():
            sigma = float(edge.get("score") or 0.0)
            if sigma < theta_hold:
                continue
            if edge.get("hippo_episode_id"):
                continue
            candidates.append(eid)
            ep = promote_edge_to_hippo_episode(state, edge, lattice_id=lid)
            if ep and ep.get("id"):
                promoted_episodes.append(str(ep["id"]))

    prune_rep = prune_wm_lattice(
        state,
        tick=int((state.get("sn") or {}).get("last_tick") or state.get("field_version") or 0),
        store_dir=store_dir,
        aggressive=False,
    )
    return {
        "episode_candidates": candidates,
        "hippo_episodes": promoted_episodes,
        "prune": prune_rep,
    }


def wm_after_partner_turn(
    state: dict,
    store_dir: Path,
    ctx: Any,
    reply_text: str,
    *,
    tick: int,
    overloaded: bool = False,
    activated_edge_ids: list[str] | None = None,
    query: str | None = None,
    surprise_before: int | None = None,
    surprise_after: int | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    pr = paste_ratio(reply_text, getattr(ctx, "blocks", []) or [])
    bind = getattr(ctx, "wm_bind", None) if ctx else None
    if isinstance(bind, dict) and not activated_edge_ids:
        activated_edge_ids = list(bind.get("placed_edges") or [])
    q = query or str(getattr(getattr(ctx, "wm", None), "user_query", "") or "")
    scores = score_wm_edges(
        state,
        tick=tick,
        turn_paste=pr,
        edge_ids=activated_edge_ids,
        store_dir=store_dir,
        query=q,
        surprise_before=surprise_before,
        surprise_after=surprise_after,
    )
    policy = get_wm_policy(state, store_dir)
    every = int(policy.get("prune_every_ticks") or 8)
    if overloaded:
        every = max(1, every // 2)
    prune_rep: dict[str, Any] = {"removed": [], "kept": sum(len(m.get("edges") or {}) for m in wm_root(state).values())}
    if every > 0 and tick > 0 and tick % every == 0:
        prune_rep = prune_wm_lattice(state, tick=tick, store_dir=store_dir, aggressive=overloaded)
    out = {
        "paste_ratio": round(pr, 4),
        "wm_edge_scores": scores,
        "prune": prune_rep,
        "overloaded_frozen": overloaded,
    }
    if persist and store_dir is not None:
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state, force=True)
    return out
