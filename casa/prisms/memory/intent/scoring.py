"""Intent Prism — tract boost scoring."""

from __future__ import annotations

import re
from typing import Any

from .policy import agent_tracts, get_intent_policy, is_agent_tract, list_hypotheses


def tokenize(text: str) -> set[str]:
    return {
        t.lower()
        for t in re.findall(r"[\w\u0400-\u04FF]+", text, flags=re.UNICODE)
        if len(t) > 2
    }


def geometry_signature(query: str) -> tuple[str, ...]:
    from casa.prisms.tick.tract import geometry_signals

    geo = geometry_signals(query)
    return tuple(sorted(k for k, v in geo.items() if v))


def hypothesis_id(tract_id: str, geo_sig: tuple[str, ...]) -> str:
    base = tract_id.replace(":", "-")
    geo_part = "-".join(geo_sig[:4]) or "none"
    return f"{base}:{geo_part}"[:64]


def surprise_key(geo_sig: tuple[str, ...]) -> str:
    return f"surprise:{'-'.join(geo_sig[:5]) or 'none'}"[:64]


def score_row_match(row: dict[str, Any], geo_sig: tuple[str, ...], tokens: set[str]) -> int:
    stored_geo = tuple(row.get("geometry") or ())
    geo_hit = len(set(stored_geo) & set(geo_sig))
    cue = set(row.get("cue_tokens") or [])
    cue_hit = len(cue & tokens)
    tract_id = str(row.get("tract_id") or "")
    if tract_id == "social" and cue_hit == 0:
        return 0
    sigma = float(row.get("score") or 0)
    if geo_hit == 0 and cue_hit == 0:
        return 0
    return int(min(32, sigma * 22 + geo_hit * 7 + cue_hit * 6))


def intent_tract_boosts(state: dict, query: str) -> dict[str, int]:
    if not query.strip():
        return {}
    policy = get_intent_policy(state)
    geo_sig = geometry_signature(query)
    from casa.prisms.tick.passage import passage_focus_question

    tokens = tokenize(passage_focus_question(query) or query)
    boosts: dict[str, int] = {}
    cap = int(policy.get("max_boost_per_tract") or 28)
    min_b = int(policy.get("min_boost") or 4)

    for row in list_hypotheses(state):
        tract_id = str(row.get("tract_id") or "")
        if not tract_id or is_agent_tract(tract_id):
            continue
        boost = score_row_match(row, geo_sig, tokens)
        if boost >= min_b:
            boosts[tract_id] = min(cap, boosts.get(tract_id, 0) + boost)

    for slug, row in agent_tracts(state).items():
        if not isinstance(row, dict):
            continue
        from .policy import format_agent_tract_id

        intent_id = str(row.get("intent_id") or format_agent_tract_id(slug))
        boost = score_row_match(row, geo_sig, tokens)
        cue_hit = len(set(row.get("cue_tokens") or []) & tokens)
        if cue_hit >= 2:
            boost = max(boost, 16 + cue_hit * 5)
        sigma = float(row.get("score") or 0)
        boost = int(boost + sigma * 14)
        if boost >= min_b:
            tract_cap = cap + 12 if is_agent_tract(intent_id) else cap
            boosts[intent_id] = min(tract_cap, boost)

    return boosts
