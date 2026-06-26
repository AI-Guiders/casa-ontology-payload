#!/usr/bin/env python3
"""L0–L5 slot composer — assemble partner surface from lexical material (ADR-0081).

Situation labels and hub ids are provenance only. Compose reads slot *pieces*
(modifier, surface, predicate_lemma, object_lemma, …) and optional field overlay.
"""

from __future__ import annotations

from typing import Any

from casa.prisms.tick.discourse.render import capitalize_sentence
from casa.prisms.tick.discourse.slots import BlockSlots

_L3_PIECE_KEYS = (
    "modifier",
    "stance",
    "referent",
    "role",
    "surface",
    "predicate_lemma",
)


def read_lexical_slots(block: dict[str, Any]) -> dict[str, str]:
    return BlockSlots.read(block)


def minimal_formula_response(slots: dict[str, str], tokens: set[str]) -> str | None:
    stimulus = str(slots.get("stimulus") or slots.get("word") or "").strip().lower()
    response = str(slots.get("response") or slots.get("response_informal") or "").strip()
    if stimulus and response and stimulus in tokens:
        return response
    return None


def l3_pieces(
    slots: dict[str, str],
    *,
    object_overlay: str = "",
    relation_marker: str = "",
) -> list[str]:
    pieces: list[str] = []
    for key in _L3_PIECE_KEYS:
        value = str(slots.get(key) or "").strip()
        if value:
            pieces.append(value)
    obj = str(object_overlay or slots.get("object_lemma") or "").strip()
    if obj:
        if relation_marker and object_overlay:
            pieces.append(f"{relation_marker} {object_overlay}".strip())
        else:
            pieces.append(obj)
    limit = str(slots.get("limit_kind") or "").strip()
    if limit:
        pieces.append(limit)
    return pieces


def slots_composable(slots: dict[str, str], tokens: set[str]) -> bool:
    if minimal_formula_response(slots, tokens):
        return True
    if len(l3_pieces(slots)) >= 2:
        return True
    surface = str(slots.get("surface") or slots.get("word") or "").strip()
    return bool(surface)


def compose_lexical_slots(
    slots: dict[str, str],
    *,
    tokens: set[str],
    has_question_mark: bool = False,
    object_overlay: str = "",
    relation_marker: str = "",
) -> str | None:
    """Render one efferent line from lexical slot material."""
    formula = minimal_formula_response(slots, tokens)
    if formula:
        body = capitalize_sentence(formula.strip())
        return body if body.endswith((".", "!", "?")) else f"{body}."

    pieces = l3_pieces(
        slots,
        object_overlay=object_overlay,
        relation_marker=relation_marker,
    )
    if len(pieces) >= 2:
        text = capitalize_sentence(" ".join(pieces))
        if has_question_mark and text.endswith("?"):
            text = text.rstrip("?") + "."
        return text if text.endswith((".", "!", "?")) else f"{text}."

    surface = str(slots.get("surface") or slots.get("word") or "").strip()
    if surface and surface.lower() in tokens:
        text = capitalize_sentence(surface)
        return text if text.endswith((".", "!", "?")) else f"{text}."

    return None


def compose_lexical_block(
    block: dict[str, Any],
    *,
    tokens: set[str],
    has_question_mark: bool = False,
    object_overlay: str = "",
    relation_marker: str = "",
) -> str | None:
    slots = read_lexical_slots(block)
    if not slots_composable(slots, tokens):
        return None
    return compose_lexical_slots(
        slots,
        tokens=tokens,
        has_question_mark=has_question_mark,
        object_overlay=object_overlay,
        relation_marker=relation_marker,
    )


def best_field_overlay(candidates: list[Any]) -> tuple[str, str]:
    """Return (overlay text, relation_marker) from eligible field/context material."""
    for item in sorted(candidates, key=lambda c: int(getattr(c, "score", 0) or 0), reverse=True):
        if not getattr(item, "surface_eligible", False):
            continue
        if getattr(item, "role", "") not in {"field_material", "context", "partner_turn"}:
            continue
        material = getattr(item, "material", None) or []
        text = str(material[0] if material else "").strip(" .!?«»")
        if not text or "?" in text:
            continue
        marker = ""
        prov = getattr(item, "provenance", None) or {}
        if isinstance(prov, dict):
            marker = str(prov.get("relation_marker") or "")
        return text, marker
    return "", ""
