"""Affect-driven tone register — bundle slots only, no Russian literals in Python."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from casa.domain.dialogue_bind.dialog_bind_policy import tone_register_slots
from casa.nervous.compose_impulse import record_compose_select, set_discourse_affect_select

if TYPE_CHECKING:
    from casa.prisms.tick.discourse.model import ClauseSketch, DiscourseContext


def _pick_variant(raw: str, seed: float) -> str:
    parts = [p.strip() for p in str(raw or "").split("|") if p.strip()]
    if not parts:
        return ""
    idx = int(abs(seed) * 997) % len(parts)
    return parts[idx]


def affect_register(bias: dict[str, Any], character: dict[str, Any] | None = None) -> str | None:
    """Map limbic + character scalars to a bundle register key, or None for cold-boot legacy."""
    security = float(bias.get("security") or 0.5)
    valence = float(bias.get("valence") or 0.0)
    char = character or {}
    openness = float(char.get("openness") or 0.5)
    directness = float(char.get("directness") or 0.5)

    if bias.get("honest_defer_bias") or security < 0.38:
        return "hedge"
    if security >= 0.62 and valence >= 0.12 and openness >= 0.45:
        return "warm"
    if directness >= 0.62 and security >= 0.45:
        return "assertive"
    if abs(security - 0.5) < 0.07 and abs(valence) < 0.08 and abs(openness - 0.5) < 0.07:
        return None
    return "neutral"


def apply_affect_register(
    clause: ClauseSketch,
    ctx: DiscourseContext,
    *,
    bundle: dict[str, Any] | None = None,
) -> str | None:
    """Apply bundle tone variant to an already-selected clause; returns register key or None."""
    state = ctx.state
    if state is None:
        return None
    from casa.prisms.affect import affect_compose_bias
    from casa.prisms.intelligence.character import ensure_character_zone

    bias = affect_compose_bias(state)
    char = ensure_character_zone(state)
    key = affect_register(bias, char)
    if not key:
        ctx.affect_select = None
        set_discourse_affect_select(state, None)
        return None

    slots = tone_register_slots(bundle)
    seed = float(bias.get("security") or 0.5) + float(bias.get("valence") or 0.0) * 0.5
    opener = _pick_variant(slots.get(f"{key}_opener") or "", seed)
    linker = _pick_variant(slots.get(f"{key}_linker") or "", seed + 0.17)

    if linker and not clause.linker:
        clause.linker = linker
    has_quote_material = any("«" in str(piece) or "»" in str(piece) for piece in clause.pieces)
    first_piece = str(clause.pieces[0] if clause.pieces else "")
    opener_target = (
        len(clause.pieces) == 1
        and len(first_piece.split()) >= 3
        and not first_piece[:1].isupper()
    )
    if opener and opener_target and not has_quote_material:
        clause.pieces = [opener, *list(clause.pieces)]

    ctx.affect_select = key
    set_discourse_affect_select(state, key)
    record_compose_select(
        state,
        "discourse.affect_register",
        zone="emotional",
        selected=[key],
        inputs={
            "security": round(float(bias.get("security") or 0.5), 3),
            "valence": round(float(bias.get("valence") or 0.0), 3),
            "openness": round(float(char.get("openness") or 0.5), 3),
            "directness": round(float(char.get("directness") or 0.5), 3),
        },
    )
    return key
