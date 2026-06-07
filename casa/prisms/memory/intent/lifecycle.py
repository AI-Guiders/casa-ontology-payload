"""Intent Prism — turn and sleep lifecycle hooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_prism import save_agent_prism
from casa.prisms.memory.memory_prisms import ensure_prisms

from .model import COMPOSE_MODES, DEFAULT_INTENT_LATTICE, slug_from_tokens
from .policy import (
    agent_tract_slug,
    agent_tracts,
    format_agent_tract_id,
    get_intent_policy,
    intent_root,
    is_agent_tract,
    spawn_intent_lattice,
)
from .scoring import geometry_signature, hypothesis_id, surprise_key, tokenize


def spawn_emergent_tract(
    state: dict,
    *,
    geo_sig: tuple[str, ...],
    cue_tokens: list[str],
    tick: int,
    compose_mode: str = "field",
) -> dict[str, Any]:
    slug = slug_from_tokens(cue_tokens)
    existing = agent_tracts(state)
    base = slug
    n = 2
    while slug in existing:
        slug = f"{base}-{n}"
        n += 1
    intent_id = format_agent_tract_id(slug)
    from .policy import agent_tract_concept_id

    row = {
        "intent_id": intent_id,
        "slug": slug,
        "concept_id": agent_tract_concept_id(slug),
        "geometry": list(geo_sig),
        "cue_tokens": list(cue_tokens),
        "compose_mode": compose_mode if compose_mode in COMPOSE_MODES else "field",
        "score": 0.68,
        "tier": "emergent",
        "spawned_tick": tick,
    }
    existing[slug] = row
    return row


def maybe_spawn_emergent_from_surprise(
    state: dict,
    *,
    query: str,
    winner_intent: str,
    tick: int,
    bind_top: int,
) -> dict[str, Any] | None:
    policy = get_intent_policy(state)
    min_bind = int(policy.get("emergent_general_min_bind") or 18)
    threshold = int(policy.get("emergent_activation_threshold") or 3)
    if winner_intent != "general" or bind_top < min_bind:
        return None

    geo_sig = geometry_signature(query)
    root = intent_root(state)[DEFAULT_INTENT_LATTICE]
    hyps: dict[str, Any] = root.setdefault("hypotheses", {})
    sk = surprise_key(geo_sig)
    surprise = hyps.setdefault(
        sk,
        {
            "tract_id": "general",
            "geometry": list(geo_sig),
            "cue_tokens": sorted(tokenize(query))[:16],
            "score": 0.2,
            "activations": 0,
            "tier": "surprise_counter",
        },
    )
    surprise["activations"] = int(surprise.get("activations") or 0) + 1
    surprise["last_tick"] = tick
    surprise["score"] = min(1.0, float(surprise.get("score") or 0.2) + 0.1)

    if int(surprise.get("activations") or 0) < threshold:
        return None

    tokens = list(surprise.get("cue_tokens") or [])
    row = spawn_emergent_tract(state, geo_sig=geo_sig, cue_tokens=tokens, tick=tick)
    hyps.pop(sk, None)
    return row


def intent_after_partner_turn(
    state: dict,
    query: str,
    winner_intent: str,
    *,
    tick: int,
    ranked: list[Any] | None = None,
    bind_top: int = 0,
) -> dict[str, Any]:
    ensure_prisms(state)
    spawn_intent_lattice(state, tick=tick)
    policy = get_intent_policy(state)
    geo_sig = geometry_signature(query)
    tokens = sorted(tokenize(query))[:16]
    root = intent_root(state)[DEFAULT_INTENT_LATTICE]
    hyps: dict[str, Any] = root.setdefault("hypotheses", {})

    emergent = maybe_spawn_emergent_from_surprise(
        state,
        query=query,
        winner_intent=winner_intent,
        tick=tick,
        bind_top=bind_top,
    )

    tract_for_hyp = winner_intent
    if is_agent_tract(winner_intent):
        slug = agent_tract_slug(winner_intent)
        row = agent_tracts(state).get(slug)
        if isinstance(row, dict):
            sigma = float(row.get("score") or 0.5) + 0.06
            row["score"] = min(1.0, sigma)
            row["last_tick"] = tick
        return {
            "tract_id": winner_intent,
            "agent_tract": slug,
            "score": row.get("score") if isinstance(row, dict) else None,
            "hypotheses": len([h for h in hyps if not str(h).startswith("surprise:")]),
        }

    hid = hypothesis_id(tract_for_hyp, geo_sig)
    row = hyps.setdefault(
        hid,
        {
            "tract_id": tract_for_hyp,
            "geometry": list(geo_sig),
            "cue_tokens": tokens,
            "score": 0.28,
            "activations": [],
            "tier": "scratch",
        },
    )
    row["tract_id"] = tract_for_hyp
    row["last_tick"] = tick
    sigma = float(row.get("score") or 0.28) + 0.08
    if ranked and len(ranked) > 1:
        margin = int(getattr(ranked[0], "score", 0) or 0) - int(getattr(ranked[1], "score", 0) or 0)
        if margin >= 10:
            sigma += 0.04
    if winner_intent == "general" and bind_top >= int(policy.get("emergent_general_min_bind") or 18):
        sigma += 0.06
    row["score"] = min(1.0, sigma)
    acts = list(row.get("activations") or [])
    acts.append({"tick": tick, "bind_top": bind_top})
    row["activations"] = acts[-12:]

    max_h = int(policy.get("max_hypotheses") or 48)
    plain = {k: v for k, v in hyps.items() if not str(k).startswith("surprise:")}
    if len(plain) > max_h:
        drop = sorted(plain.items(), key=lambda kv: float((kv[1] or {}).get("score") or 0))[: len(plain) - max_h]
        for k, _ in drop:
            hyps.pop(k, None)

    out: dict[str, Any] = {
        "hypothesis_id": hid,
        "tract_id": tract_for_hyp,
        "score": row["score"],
        "hypotheses": len(plain),
    }
    if emergent:
        out["emergent_tract"] = emergent.get("intent_id")
    return out


def intent_on_sleep_boundary(state: dict, store_dir: Path | None = None) -> dict[str, Any]:
    """Decay weak hypotheses; scratch → episode tier."""
    policy = get_intent_policy(state)
    decay = float(policy.get("theta_decay") or 0.12)
    hold = float(policy.get("theta_hold") or 0.38)
    root = intent_root(state).get(DEFAULT_INTENT_LATTICE) or {}
    hyps: dict[str, Any] = dict(root.get("hypotheses") or {})
    kept: dict[str, Any] = {}
    episodes = 0
    pruned = 0
    for hid, row in hyps.items():
        if not isinstance(row, dict):
            continue
        if str(hid).startswith("surprise:"):
            pruned += 1
            continue
        sigma = float(row.get("score") or 0) - decay
        if sigma < hold:
            pruned += 1
            continue
        row = dict(row)
        row["score"] = sigma
        if sigma >= float(policy.get("theta_promote") or 0.62) * 0.9:
            row["tier"] = "episode"
            episodes += 1
        kept[hid] = row
    root["hypotheses"] = kept
    if store_dir is not None:
        save_agent_prism(store_dir, state)
    return {"kept": len(kept), "pruned": pruned, "episodes": episodes, "agent_tracts": len(agent_tracts(state))}
