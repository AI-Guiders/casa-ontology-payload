#!/usr/bin/env python3
"""Character field dent on repression — latent trace without hot recall (ADR-0074 P19f)."""

from __future__ import annotations

from typing import Any

from casa.prisms.defense.core import defense_block


def character_consolidate_repression(
    state: dict,
    *,
    domain: str = "social",
    tract: str = "discuss",
    event: str = "",
    axes: dict[str, float] | None = None,
    tick: int = 0,
) -> dict[str, Any]:
    """Slow EMA dent in domain×tract bias — memory blocked but character learns shape."""
    from casa.prisms.intelligence.character import ensure_character_zone

    zone = ensure_character_zone(state)
    alpha = float(zone.get("ema_alpha") or 0.05)
    matrix: dict[str, dict[str, float]] = zone.setdefault("bias_matrix", {})
    dom = matrix.setdefault(str(domain), {})
    cur = float(dom.get(str(tract)) or 1.0)
    valence = float((axes or {}).get("valence") or -0.1)
    dent = alpha * max(0.04, min(0.12, -valence * 0.25))
    new_val = max(0.5, cur - dent)
    dom[str(tract)] = round(new_val, 5)

    dents = list(zone.get("repression_dents") or [])
    dents.append(
        {
            "domain": domain,
            "tract": tract,
            "bias": new_val,
            "event": str(event or "")[:64],
            "tick": int(tick),
        }
    )
    zone["repression_dents"] = dents[-32:]

    rep = {
        "domain": domain,
        "tract": tract,
        "bias": new_val,
        "dent": round(dent, 5),
    }
    defense_block(state)["character_dent_last"] = rep
    return rep


def character_bias_for_tract(state: dict, *, domain: str, tract: str) -> float:
    from casa.prisms.intelligence.character import ensure_character_zone

    zone = ensure_character_zone(state)
    matrix = zone.get("bias_matrix") or {}
    dom = matrix.get(str(domain)) if isinstance(matrix, dict) else None
    if isinstance(dom, dict):
        raw = dom.get(str(tract))
        if raw is not None:
            return float(raw)
    return 1.0
