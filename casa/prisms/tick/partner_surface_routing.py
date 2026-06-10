#!/usr/bin/env python3
"""Partner surface → concept hints from bundle claims (not Python oracles)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from casa.prisms.tick.tract.claims import slot_cue_hit

_ROUTING_PREFIX = "ru.routing.partner_surface."
_DESIGN_REL = Path("design") / "kb-partner-surface-routing.v1.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _design_routing_claims() -> tuple[dict[str, Any], ...]:
    path = _repo_root() / _DESIGN_REL
    if not path.is_file():
        return ()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    out: list[dict[str, Any]] = []
    for row in raw.get("claims") or []:
        if isinstance(row, dict) and str(row.get("concept_id") or "").startswith(_ROUTING_PREFIX):
            out.append(row)
    return tuple(out)


def partner_surface_routing_claims(bundle: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Routing claims on field; design pack is baseline, store claims override by concept_id."""
    by_id: dict[str, dict[str, Any]] = {
        str(c.get("concept_id") or ""): c for c in _design_routing_claims() if c.get("concept_id")
    }
    if bundle:
        for row in bundle.get("claims") or []:
            if not isinstance(row, dict):
                continue
            cid = str(row.get("concept_id") or "")
            if cid.startswith(_ROUTING_PREFIX):
                by_id[cid] = row
    return list(by_id.values())


def partner_surface_hints(query: str, bundle: dict[str, Any] | None = None) -> list[str]:
    """Match partner turn against routing claims → concept_hints for read/bind."""
    ql = (query or "").strip().lower()
    if not ql:
        return []
    hints: list[str] = []
    for claim in partner_surface_routing_claims(bundle):
        slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
        if slot_cue_hit(ql, slots) <= 0:
            continue
        hint = str(slots.get("route_hint") or claim.get("concept_id") or "").strip()
        if hint:
            hints.append(hint)
    return list(dict.fromkeys(hints))
