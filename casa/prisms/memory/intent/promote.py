"""Intent Prism — hypothesis promotion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_prism import save_agent_prism
from casa.prisms.shared.store_layout import agent_manifest_path

from .model import COMPOSE_MODES, DEFAULT_INTENT_LATTICE, slug_from_tokens
from .policy import (
    agent_tract_concept_id,
    agent_tract_slug,
    agent_tracts,
    format_agent_tract_id,
    get_intent_policy,
    intent_root,
)


def promote_intent_hypothesis(
    state: dict,
    hypothesis_id: str,
    *,
    target: str = "agent",
    slug: str | None = None,
    compose_mode: str = "field",
    store_dir: Path | None = None,
    persist: bool = False,
) -> dict[str, Any]:
    """Promote scratch hypothesis → agent.tract.* or pending ru.tract.* canon claim."""
    policy = get_intent_policy(state)
    root = intent_root(state).get(DEFAULT_INTENT_LATTICE) or {}
    hyps = root.get("hypotheses") or {}
    row = hyps.get(hypothesis_id)
    if not isinstance(row, dict):
        raise ValueError(f"hypothesis not found: {hypothesis_id}")
    if float(row.get("score") or 0) < float(policy.get("theta_promote") or 0.62):
        raise ValueError(f"hypothesis score {row.get('score')} below theta_promote")

    cues = "|".join(list(row.get("cue_tokens") or [])[:12])
    geo_req = list(row.get("geometry") or [])[:1]
    geo_slot = geo_req[0] if geo_req else ""

    if target == "canon":
        host_slug = slug or slug_from_tokens(list(row.get("cue_tokens") or []))
        claim = {
            "concept_id": f"ru.tract.{host_slug}",
            "slots": {
                "cue_words": cues.replace("|", ","),
            },
        }
        if geo_slot:
            claim["slots"]["requires_geometry"] = geo_slot
        pending: list[dict[str, Any]] = []
        if store_dir is not None:
            path = agent_manifest_path(store_dir)
            manifest = {}
            if path.is_file():
                manifest = json.loads(path.read_text(encoding="utf-8"))
            pending = list(manifest.get("pending_tract_claims") or [])
            pending.append(claim)
            manifest["pending_tract_claims"] = pending
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        hyps.pop(hypothesis_id, None)
        return {"target": "canon", "claim": claim, "pending_count": len(pending)}

    use_slug = slug or slug_from_tokens(list(row.get("cue_tokens") or []))
    intent_id = format_agent_tract_id(use_slug)
    promoted = {
        "intent_id": intent_id,
        "slug": agent_tract_slug(intent_id),
        "concept_id": agent_tract_concept_id(use_slug),
        "geometry": list(row.get("geometry") or []),
        "cue_tokens": list(row.get("cue_tokens") or []),
        "compose_mode": compose_mode if compose_mode in COMPOSE_MODES else "field",
        "score": float(row.get("score") or 0.62),
        "tier": "promoted",
        "hypothesis_id": hypothesis_id,
    }
    agent_tracts(state)[promoted["slug"]] = promoted
    hyps.pop(hypothesis_id, None)
    if persist and store_dir is not None:
        save_agent_prism(store_dir, state)
    return {"target": "agent", "tract": promoted}
