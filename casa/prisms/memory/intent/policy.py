"""Intent Prism — policy, tract identity, and lattice metadata."""

from __future__ import annotations

import json
import re
from typing import Any

from casa.domain.prism_wire import prism_agent
from casa.prisms.memory.agent_prism import create_agent_lattice, ensure_agent_prism

from .model import (
    AGENT_TRACT_CONCEPT_PREFIX,
    AGENT_TRACT_PREFIX,
    DEFAULT_INTENT_LATTICE,
    DEFAULT_INTENT_POLICY,
    INTENT_CONCEPT_PREFIX,
)


def is_agent_tract(intent_id: str) -> bool:
    return str(intent_id or "").startswith(AGENT_TRACT_PREFIX)


def agent_tract_slug(intent_id: str) -> str:
    return str(intent_id or "").removeprefix(AGENT_TRACT_PREFIX)


def format_agent_tract_id(slug: str) -> str:
    clean = re.sub(r"[^a-z0-9_-]+", "-", str(slug or "").lower()).strip("-")
    return f"{AGENT_TRACT_PREFIX}{clean or 'emergent'}"


def agent_tract_concept_id(slug: str) -> str:
    return f"{AGENT_TRACT_CONCEPT_PREFIX}{agent_tract_slug(format_agent_tract_id(slug))}"


def get_intent_policy(state: dict) -> dict[str, Any]:
    policy = json.loads(json.dumps(DEFAULT_INTENT_POLICY))
    block = ensure_agent_prism(state)
    override = block.get("intent_policy")
    if isinstance(override, dict):
        policy.update(override)
    return policy


def intent_root(state: dict) -> dict[str, Any]:
    ensure_agent_prism(state)
    return prism_agent(state).setdefault("intent_lattices", {})


def agent_tracts(state: dict) -> dict[str, Any]:
    ensure_agent_prism(state)
    root = prism_agent(state).setdefault("agent_tracts", {})
    if not isinstance(root, dict):
        root = {}
        prism_agent(state)["agent_tracts"] = root
    return root


def spawn_intent_lattice(state: dict, *, tick: int = 0) -> str:
    lid = DEFAULT_INTENT_LATTICE
    lats = ensure_agent_prism(state).setdefault("lattices", {})
    if lid not in lats:
        create_agent_lattice(
            state,
            lid,
            width=24,
            height=24,
            concept_prefix=INTENT_CONCEPT_PREFIX,
        )
    meta = intent_root(state).setdefault(
        lid,
        {"lattice_id": lid, "spawned_tick": tick, "hypotheses": {}},
    )
    meta.setdefault("hypotheses", {})
    return lid


def list_hypotheses(state: dict) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for meta in intent_root(state).values():
        for hid, row in (meta.get("hypotheses") or {}).items():
            if isinstance(row, dict) and not str(hid).startswith("surprise:"):
                rows.append({"hypothesis_id": hid, **row})
    rows.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
    return rows


def list_agent_tracts(state: dict) -> list[dict[str, Any]]:
    rows = []
    for slug, row in agent_tracts(state).items():
        if isinstance(row, dict):
            rows.append({"slug": slug, **row})
    rows.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
    return rows


def resolve_compose_profile(state: dict, query_intent: str) -> dict[str, Any] | None:
    if not is_agent_tract(query_intent):
        return None
    slug = agent_tract_slug(query_intent)
    row = agent_tracts(state).get(slug)
    if not isinstance(row, dict):
        return {"intent_id": query_intent, "slug": slug, "compose_mode": "field"}
    return {
        "intent_id": query_intent,
        "slug": slug,
        "compose_mode": str(row.get("compose_mode") or "field"),
        "concept_id": str(row.get("concept_id") or agent_tract_concept_id(slug)),
        "cue_tokens": list(row.get("cue_tokens") or []),
        "geometry": list(row.get("geometry") or []),
    }
