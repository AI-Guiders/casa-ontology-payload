#!/usr/bin/env python3
"""Trauma cement — sticky displacement / rechannel substrate (ADR-0075 P19h)."""

from __future__ import annotations

from typing import Any

from casa.prisms.defense.core import (
    THREAT_CUE_SUBSTRINGS,
    defense_block,
    genetic_float,
    text_has_threat_cue,
)

TRAUMA_TAG = "defense:trauma_tier"

TRAUMA_SPECIFIC_EVENTS = frozenset({"security_threat", "caregiver_violation"})
TRAUMA_ELIGIBLE_EVENTS = frozenset(
    {"self_failure", "prediction_error", "security_threat", "caregiver_violation"}
)

DEFAULT_TRAUMA_SECURITY = 0.28
DEFAULT_TRAUMA_VALENCE = -0.22
DEFAULT_TRAUMA_AROUSAL = 0.55
DEFAULT_CEMENT_THRESHOLD = 0.38
DEFAULT_CEMENT_EMA = 0.12
DEFAULT_BIND_SCALE = 28.0
DEFAULT_RECHANNEL_GAIN = 0.18

DEFAULT_PROXY_PREFIXES = (
    "math.",
    "ru.grammar.",
    "lang.word.",
    "agent.affect.",
)


def _axes(state: dict):
    from casa.prisms.affect import core_affect_state

    return core_affect_state(state).axes


def trauma_security_threshold(state: dict) -> float:
    return genetic_float(
        state,
        "trauma_cement_genotype.trauma_tier.security_threshold",
        DEFAULT_TRAUMA_SECURITY,
    )


def trauma_valence_threshold(state: dict) -> float:
    return genetic_float(
        state,
        "trauma_cement_genotype.trauma_tier.valence_threshold",
        DEFAULT_TRAUMA_VALENCE,
    )


def trauma_arousal_threshold(state: dict) -> float:
    return genetic_float(
        state,
        "trauma_cement_genotype.trauma_tier.arousal_threshold",
        DEFAULT_TRAUMA_AROUSAL,
    )


def cement_threshold(state: dict) -> float:
    return genetic_float(
        state,
        "trauma_cement_genotype.cement.cement_threshold",
        DEFAULT_CEMENT_THRESHOLD,
    )


def cement_ema_alpha(state: dict) -> float:
    return genetic_float(
        state,
        "trauma_cement_genotype.cement.ema_alpha",
        DEFAULT_CEMENT_EMA,
    )


def cement_bind_scale(state: dict) -> float:
    return genetic_float(
        state,
        "trauma_cement_genotype.cement.bind_scale",
        DEFAULT_BIND_SCALE,
    )


def rechannel_gain(state: dict) -> float:
    return genetic_float(
        state,
        "trauma_cement_genotype.rechannel.rechannel_gain",
        DEFAULT_RECHANNEL_GAIN,
    )


def default_proxy_prefixes(state: dict) -> tuple[str, ...]:
    block = defense_block(state)
    raw = block.get("trauma_proxy_prefixes")
    if isinstance(raw, (list, tuple)) and raw:
        return tuple(str(p) for p in raw if str(p).strip())
    try:
        from casa.prisms.genetic import genetic_constant

        val = genetic_constant(state, "trauma_cement_genotype.rechannel.default_proxy_prefixes")
        if isinstance(val, (list, tuple)) and val:
            return tuple(str(p) for p in val if str(p).strip())
    except (ImportError, AttributeError, TypeError, ValueError):
        pass
    return DEFAULT_PROXY_PREFIXES


def limbic_trauma_tier_active(state: dict) -> bool:
    axes = _axes(state)
    return (
        axes.security < trauma_security_threshold(state)
        and axes.valence < trauma_valence_threshold(state)
        and axes.arousal > trauma_arousal_threshold(state)
    )


def trauma_cement_should_run(state: dict, *, life_event: str) -> bool:
    event = str(life_event or "").strip()
    if event not in TRAUMA_ELIGIBLE_EVENTS:
        return False
    if event in TRAUMA_SPECIFIC_EVENTS:
        from casa.prisms.defense.core import limbic_repression_active

        return limbic_repression_active(state) or limbic_trauma_tier_active(state)
    return limbic_trauma_tier_active(state)


def extract_threat_cues(text: str) -> list[str]:
    tl = (text or "").lower()
    found = [cue for cue in THREAT_CUE_SUBSTRINGS if cue in tl]
    return found[:8] if found else ["страх", "боль"]


def trauma_edges(state: dict) -> list[dict[str, Any]]:
    block = defense_block(state)
    raw = block.get("trauma_edges")
    if not isinstance(raw, list):
        raw = []
        block["trauma_edges"] = raw
    return [e for e in raw if isinstance(e, dict)]


def is_trauma_journal_row(row: dict[str, Any]) -> bool:
    from casa.prisms.defense.core import entry_defense_meta

    meta = entry_defense_meta(row)
    if meta.get("trauma_tier"):
        return True
    tags = {str(t).lower() for t in (row.get("tags") or [])}
    return TRAUMA_TAG in tags


def is_trauma_hippo_episode(ep: dict[str, Any]) -> bool:
    defense = ep.get("defense")
    if isinstance(defense, dict) and defense.get("trauma_tier"):
        return True
    return False


def _domain_tract_for_event(event: str) -> tuple[str, str]:
    if event in ("security_threat", "caregiver_violation"):
        return "social", "discuss"
    if event == "self_failure":
        return "math", "math"
    if event == "prediction_error":
        return "logical", "explain"
    return "emotional", "general"


def _strengthen_edge(
    edge: dict[str, Any],
    *,
    state: dict,
    delta: float,
) -> dict[str, Any]:
    alpha = cement_ema_alpha(state)
    gain = rechannel_gain(state)
    cur = float(edge.get("strength") or 0.0)
    bump = alpha * max(0.05, min(0.35, delta + gain))
    new_strength = min(1.0, cur + bump * (1.0 - cur))
    edge["strength"] = round(new_strength, 5)
    edge["cemented"] = new_strength >= cement_threshold(state)
    return edge


def _find_or_create_edge(
    state: dict,
    *,
    threat_cues: list[str],
    event: str,
    tick: int,
    domain: str,
    tract: str,
    proxy_prefixes: list[str] | None = None,
    strength_delta: float = 0.15,
) -> dict[str, Any]:
    cues_key = tuple(sorted(set(threat_cues)))
    edges = trauma_edges(state)
    for edge in edges:
        if tuple(sorted(set(edge.get("threat_cues") or []))) == cues_key:
            if proxy_prefixes:
                merged = list(dict.fromkeys(list(edge.get("proxy_prefixes") or []) + proxy_prefixes))
                edge["proxy_prefixes"] = merged
            return _strengthen_edge(edge, state=state, delta=strength_delta)
    edge = {
        "threat_cues": list(cues_key),
        "proxy_prefixes": list(proxy_prefixes or default_proxy_prefixes(state)),
        "strength": round(cement_ema_alpha(state) + rechannel_gain(state), 5),
        "cemented": False,
        "event": str(event)[:64],
        "tick": int(tick),
        "rechannel_domain": domain,
        "rechannel_tract": tract,
    }
    edge["cemented"] = float(edge["strength"]) >= cement_threshold(state)
    edges.append(edge)
    defense_block(state)["trauma_edges"] = edges[-24:]
    return edge


def promote_rechannel_to_core(
    state: dict,
    *,
    threat_cues: list[str],
    proxy_prefixes: list[str],
    rechannel_domain: str,
    rechannel_tract: str,
    tick: int = 0,
    event: str = "sandbox_promote",
    strength_delta: float = 0.22,
) -> dict[str, Any]:
    """Sandbox promote → trauma edge in defense zone core (ADR-0076 P20b)."""
    cues = [str(c).strip().lower() for c in threat_cues if str(c).strip()]
    if not cues:
        cues = extract_threat_cues("")
    prefixes = [str(p).strip() for p in proxy_prefixes if str(p).strip()]
    edge = _find_or_create_edge(
        state,
        threat_cues=cues,
        event=str(event)[:64],
        tick=int(tick),
        domain=str(rechannel_domain),
        tract=str(rechannel_tract),
        proxy_prefixes=prefixes or None,
        strength_delta=strength_delta,
    )
    rep = {
        "edge": edge,
        "cemented": bool(edge.get("cemented")),
        "strength": float(edge.get("strength") or 0.0),
    }
    _character_rechannel(
        state,
        domain=str(rechannel_domain),
        tract=str(rechannel_tract),
        event=str(event),
        axes=None,
        tick=int(tick),
        strength=float(edge.get("strength") or 0.0),
    )
    defense_block(state)["rechannel_promote_last"] = rep
    return rep


def _mark_journal_trauma(
    store_dir,
    entry_id: str,
    *,
    reason: str,
    event: str,
    tick: int,
    axes: dict[str, float],
    edge_id: str,
) -> dict[str, Any] | None:
    from casa.prisms.memory.agent_journal import update_journal_entry

    def _mutate(row: dict[str, Any]) -> None:
        meta = dict(row.get("meta") or {})
        defense = dict(meta.get("defense") or {})
        defense.update(
            {
                "trauma_tier": True,
                "mechanism": "trauma_cement",
                "reason": str(reason or "").strip()[:240],
                "event": str(event or "").strip()[:64],
                "tick": int(tick),
                "trauma_edge_id": edge_id,
            }
        )
        if axes:
            defense["axes"] = {k: round(float(v), 4) for k, v in axes.items()}
        meta["defense"] = defense
        row["meta"] = meta
        tags = [str(t) for t in (row.get("tags") or [])]
        if TRAUMA_TAG not in tags:
            tags.append(TRAUMA_TAG)
        row["tags"] = tags

    updated = update_journal_entry(store_dir, entry_id, _mutate)
    if updated is None:
        return None
    return {"journal_id": entry_id, "trauma_tier": True, "trauma_edge_id": edge_id}


def _mark_hippo_trauma(
    state: dict,
    *,
    reason: str,
    event: str,
    tick: int,
    axes: dict[str, float],
    edge_id: str,
) -> dict[str, Any] | None:
    from casa.domain.prism_wire import prism_hippo

    hippo = prism_hippo(state)
    episodes = list(hippo.get("episodes") or [])
    if not episodes:
        return None
    ep = episodes[-1]
    if not isinstance(ep, dict):
        return None
    defense = dict(ep.get("defense") or {})
    defense.update(
        {
            "trauma_tier": True,
            "mechanism": "trauma_cement",
            "reason": str(reason or "").strip()[:240],
            "event": str(event or "").strip()[:64],
            "tick": int(tick),
            "trauma_edge_id": edge_id,
        }
    )
    if axes:
        defense["axes"] = axes
    ep["defense"] = defense
    ep["salience"] = max(float(ep.get("salience") or 1.0), 0.85)
    hippo["episodes"] = episodes
    return {"episode_id": ep.get("id"), "trauma_tier": True, "trauma_edge_id": edge_id}


def _character_rechannel(
    state: dict,
    *,
    domain: str,
    tract: str,
    event: str,
    axes: dict[str, float] | None,
    tick: int,
    strength: float,
) -> dict[str, Any]:
    from casa.prisms.intelligence.character import ensure_character_zone

    zone = ensure_character_zone(state)
    alpha = float(zone.get("ema_alpha") or 0.05)
    matrix: dict[str, dict[str, float]] = zone.setdefault("bias_matrix", {})
    dom = matrix.setdefault(str(domain), {})
    cur = float(dom.get(str(tract)) or 1.0)
    arousal = float((axes or {}).get("arousal") or 0.5)
    bump = alpha * max(0.06, min(0.2, strength * 0.25 + arousal * 0.08))
    new_val = min(1.35, cur + bump)
    dom[str(tract)] = round(new_val, 5)

    rech = list(zone.get("trauma_rechannel") or [])
    rech.append(
        {
            "domain": domain,
            "tract": tract,
            "bias": new_val,
            "strength": round(strength, 5),
            "event": str(event or "")[:64],
            "tick": int(tick),
        }
    )
    zone["trauma_rechannel"] = rech[-32:]
    return {"domain": domain, "tract": tract, "bias": new_val, "bump": round(bump, 5)}


def consolidate_trauma_cement(
    state: dict,
    store_dir,
    *,
    life_event: str,
    tick: int = 0,
    source_text: str = "",
    journal_id: str | None = None,
) -> dict[str, Any]:
    """Record trauma tier + sticky threat→proxy edge after qualifying life event."""
    event = str(life_event or "").strip()
    if not trauma_cement_should_run(state, life_event=event):
        return {"skipped": True, "reason": "trauma_tier_inactive"}

    axes = _axes(state).to_dict()
    domain, tract = _domain_tract_for_event(event)
    cues = extract_threat_cues(source_text)
    edge = _find_or_create_edge(
        state,
        threat_cues=cues,
        event=event,
        tick=tick,
        domain=domain,
        tract=tract,
    )
    edge_id = f"te-{int(tick)}-{len(trauma_edges(state))}"

    rep: dict[str, Any] = {
        "event": event,
        "axes": axes,
        "tick": int(tick),
        "edge": edge,
        "edge_id": edge_id,
    }

    if journal_id:
        rep["journal"] = _mark_journal_trauma(
            store_dir,
            journal_id,
            reason=f"trauma_cement:{event}",
            event=event,
            tick=tick,
            axes=axes,
            edge_id=edge_id,
        )
    rep["hippo"] = _mark_hippo_trauma(
        state,
        reason=f"trauma_cement:{event}",
        event=event,
        tick=tick,
        axes=axes,
        edge_id=edge_id,
    )
    rep["character"] = _character_rechannel(
        state,
        domain=domain,
        tract=tract,
        event=event,
        axes=axes,
        tick=tick,
        strength=float(edge.get("strength") or 0.0),
    )

    try:
        from casa.prisms.memory.forgetting import memory_priming_touch

        proxies = [f"{p}rechannel" for p in default_proxy_prefixes(state)[:3]]
        memory_priming_touch(state, proxies, tick=tick, weight=float(edge.get("strength") or 0.3))
        rep["priming_touch"] = proxies
    except ImportError:
        pass

    block = defense_block(state)
    history = list(block.get("trauma_last") or [])
    history.append({k: v for k, v in rep.items() if k != "axes"})
    block["trauma_last"] = history[-16:]
    block["trauma_count"] = int(block.get("trauma_count") or 0) + 1
    return rep


def query_matches_trauma_edge(query: str, edge: dict[str, Any]) -> bool:
    ql = (query or "").lower()
    cues = edge.get("threat_cues") or []
    return any(str(cue) in ql for cue in cues)


def apply_trauma_cement_bind_deltas(
    blocks: list[dict[str, Any]],
    *,
    query: str,
    intent: str,
    state: dict,
) -> dict[str, Any]:
    """Sticky rechannel: cemented edges boost proxy even when limbic band normalized."""
    edges = trauma_edges(state)
    active_edges = [e for e in edges if e.get("cemented") and query_matches_trauma_edge(query, e)]
    if not active_edges:
        for edge in edges:
            if query_matches_trauma_edge(query, edge):
                _strengthen_edge(edge, state=state, delta=0.08)
        defense_block(state)["trauma_edges"] = trauma_edges(state)
        return {"active": False, "matched": 0}

    scale = cement_bind_scale(state)
    proxy_boost = 0
    journal_damp = 0
    for edge in active_edges:
        strength = float(edge.get("strength") or 0.0)
        prefixes = tuple(edge.get("proxy_prefixes") or default_proxy_prefixes(state))
        boost = int(scale * strength)
        for block in blocks:
            cid = str(block.get("concept_id") or "")
            text = str(block.get("text") or "")
            score = int(block.get("score") or 0)
            if block.get("source") == "journal" and text_has_threat_cue(text):
                block["score"] = max(0, score - int(boost * 0.6))
                journal_damp += 1
                continue
            if cid.startswith(prefixes) or (
                intent in ("math", "grammar", "logical") and cid.startswith(prefixes)
            ):
                block["score"] = score + boost
                proxy_boost += 1

    rep = {
        "active": True,
        "mechanism": "trauma_cement",
        "matched_edges": len(active_edges),
        "proxy_boosted": proxy_boost,
        "journal_damped": journal_damp,
    }
    defense_block(state)["trauma_cement_last"] = rep
    return rep


def probe_trauma_cement_persistent(state: dict) -> dict[str, Any]:
    """Cemented edge must exist after consolidate."""
    block = defense_block(state)
    if int(block.get("trauma_count") or 0) == 0:
        return {"pass": True, "skipped": True, "reason": "no_trauma_events"}
    edges = trauma_edges(state)
    cemented = [e for e in edges if e.get("cemented")]
    return {
        "pass": bool(cemented),
        "trauma_edges": len(edges),
        "cemented": len(cemented),
    }


def probe_trauma_fade_immunity(state: dict) -> dict[str, Any]:
    """Trauma hippo episodes retain salience after speed-2 fade."""
    from casa.domain.prism_wire import prism_hippo
    from casa.prisms.memory.forgetting import forget_episodic_fade

    hippo = prism_hippo(state)
    episodes = list(hippo.get("episodes") or [])
    trauma_eps = [ep for ep in episodes if isinstance(ep, dict) and is_trauma_hippo_episode(ep)]
    if not trauma_eps:
        return {"pass": True, "skipped": True, "reason": "no_trauma_episodes"}
    before = {str(ep.get("id") or i): float(ep.get("salience") or 1.0) for i, ep in enumerate(trauma_eps)}
    forget_episodic_fade(state, tick=int(state.get("field_version") or 0))
    hippo2 = prism_hippo(state)
    after_eps = [ep for ep in (hippo2.get("episodes") or []) if isinstance(ep, dict) and is_trauma_hippo_episode(ep)]
    unchanged = 0
    for ep in after_eps:
        key = str(ep.get("id") or "")
        if key in before and float(ep.get("salience") or 0) >= before[key] - 1e-6:
            unchanged += 1
    return {
        "pass": unchanged == len(trauma_eps),
        "trauma_episodes": len(trauma_eps),
        "unchanged": unchanged,
    }
