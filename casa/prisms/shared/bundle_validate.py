#!/usr/bin/env python3
"""Validate a KB bundle before it is written to a store (auto-curriculum write-target).

Nothing validates a bundle today, so a malformed (e.g. LLM-drafted) claim can be
written to the live store and silently misroute bind. The runtime weighted-prefix
parser (``speech_act_scoring._parse_weighted_prefixes``) corrupts silently:
  - ``":5"``      -> empty prefix, which matches *every* concept_id via startswith("")
  - ``"hub:5:7"`` -> rsplit mis-splits into the wrong prefix "hub:5"
  - ``"hub:abc"`` -> int() fails, the token is dropped (typo'd boost vanishes)
  - ``"hub:-3"``  -> negative weight inverts a boost into a demote

This gate runs BEFORE any disk write and rejects the whole delta on any
error-level violation, accumulating all of them so the author gets a complete
fix list (Phase 2 of design/CASA-auto-curriculum-plan-v1.md). concept_id
collisions against the live store are reported at ``warn`` level (an intentional
update is allowed; the auto-curriculum can opt to treat them as errors).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

# slots whose values are pipe-joined ``prefix:weight`` lists
_WEIGHTED_SLOTS = ("bind_boost", "bind_demote")


@dataclass(frozen=True)
class WriteCaps:
    max_claims: int = 4000
    max_weight: int = 60
    max_bytes: int = 4_000_000


DEFAULT_WRITE_CAPS = WriteCaps()


def _violation(
    code: str,
    *,
    claim_index: int | None = None,
    field: str | None = None,
    detail: str | None = None,
    severity: str = "error",
) -> dict[str, Any]:
    v: dict[str, Any] = {"code": code, "severity": severity}
    if claim_index is not None:
        v["claim_index"] = claim_index
    if field is not None:
        v["field"] = field
    if detail is not None:
        v["detail"] = detail
    return v


def _validate_weighted(
    raw: Any,
    *,
    claim_index: int,
    field: str,
    caps: WriteCaps,
    out: list[dict[str, Any]],
) -> None:
    if not isinstance(raw, str):
        out.append(_violation("slot_not_str", claim_index=claim_index, field=field, detail=type(raw).__name__))
        return
    for part in (p.strip() for p in raw.split("|")):
        if not part:
            continue
        if ":" not in part:
            continue  # bare prefix -> runtime applies the default weight; fine
        prefix, weight = part.rsplit(":", 1)
        prefix = prefix.strip()
        if not prefix:
            out.append(_violation("empty_prefix", claim_index=claim_index, field=field, detail=part))
            continue
        if ":" in prefix:
            out.append(_violation("multi_colon_prefix", claim_index=claim_index, field=field, detail=part))
            continue
        try:
            w = int(weight.strip())
        except ValueError:
            out.append(_violation("non_int_weight", claim_index=claim_index, field=field, detail=part))
            continue
        if w < 0:
            out.append(_violation("negative_weight", claim_index=claim_index, field=field, detail=part))
        elif w > caps.max_weight:
            out.append(
                _violation("weight_over_cap", claim_index=claim_index, field=field, detail=f"{part} > {caps.max_weight}")
            )


def validate_bundle(
    bundle: Any,
    *,
    live_concept_ids: Any = None,
    caps: WriteCaps = DEFAULT_WRITE_CAPS,
) -> dict[str, Any]:
    """Return ``{ok, violations, claim_count}``. ``ok`` is False on any error-level violation."""
    if not isinstance(bundle, dict):
        return {"ok": False, "violations": [_violation("bundle_not_dict")], "claim_count": 0}
    claims = bundle.get("claims")
    if not isinstance(claims, list):
        return {"ok": False, "violations": [_violation("claims_not_list")], "claim_count": 0}

    out: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for i, c in enumerate(claims):
        if not isinstance(c, dict):
            out.append(_violation("claim_not_dict", claim_index=i, detail=type(c).__name__))
            continue
        cid = c.get("concept_id")
        if not isinstance(cid, str) or not cid.strip():
            out.append(_violation("bad_concept_id", claim_index=i, detail=repr(cid)))
        else:
            cid = cid.strip()
            if cid in seen:
                out.append(_violation("duplicate_concept_id", claim_index=i, detail=cid))
            seen[cid] = i
        text = c.get("text")
        if text is not None and not isinstance(text, str):
            out.append(_violation("bad_text", claim_index=i, detail=type(text).__name__))
        slots = c.get("slots")
        if slots is not None and not isinstance(slots, dict):
            out.append(_violation("bad_slots", claim_index=i, detail=type(slots).__name__))
        elif isinstance(slots, dict):
            for sk in _WEIGHTED_SLOTS:
                if sk in slots:
                    _validate_weighted(slots[sk], claim_index=i, field=sk, caps=caps, out=out)

    if len(claims) > caps.max_claims:
        out.append(_violation("too_many_claims", detail=f"{len(claims)} > {caps.max_claims}"))
    try:
        size = len(json.dumps(bundle, ensure_ascii=False).encode("utf-8"))
        if size > caps.max_bytes:
            out.append(_violation("bundle_too_large", detail=f"{size} > {caps.max_bytes}"))
    except (TypeError, ValueError):
        out.append(_violation("bundle_not_serializable"))

    if live_concept_ids:
        live = {str(x) for x in live_concept_ids}
        for cid, i in seen.items():
            if cid in live:
                out.append(_violation("concept_id_collision", claim_index=i, detail=cid, severity="warn"))

    ok = not any(v.get("severity") == "error" for v in out)
    return {"ok": ok, "violations": out, "claim_count": len(claims)}
