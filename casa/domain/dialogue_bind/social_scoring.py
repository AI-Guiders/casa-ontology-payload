"""Social bind reweight — hints + field overlap + gating only (no per-hub Python tables)."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.partner_scoring import (
    dialog_query_position_boost,
    partner_field_overlap,
    partner_quote_from_block,
    partner_speech_turn,
    social_dialog_slot_allowed,
)
from casa.prisms.memory.concept_layer import discourse_concept_id


def apply_social_block_deltas(
    block: dict[str, Any],
    *,
    query: str,
    ql: str,
    score: int,
    concept_hints: list[str] | None,
    blocks: list[dict[str, Any]],
    partner_speech_query: bool,
) -> int:
    cid = str(block.get("concept_id") or "")
    disc = discourse_concept_id(block)
    slots = block.get("slots") if isinstance(block.get("slots"), dict) else {}

    for hint in concept_hints or []:
        if disc == hint or disc.startswith(f"{hint}.") or hint.startswith(disc):
            score += 24
        elif disc.startswith("ru.dialog.") and hint.startswith("lang.word."):
            lemma = hint.rsplit(".", 1)[-1].lower()
            slot_word = str(
                slots.get("stimulus") or slots.get("word") or slots.get("surface") or ""
            ).lower()
            if lemma and slot_word == lemma:
                score += 22

    if disc.startswith("ru.dialog."):
        field_ov = partner_field_overlap(query, block)
        if field_ov >= 8:
            score += min(32, field_ov * 2)
        if not social_dialog_slot_allowed(
            disc,
            concept_hints=concept_hints,
            query=query,
            block=block,
        ):
            return 0
        score += dialog_query_position_boost(query, block, concept_hints=concept_hints)

    if block.get("source") == "dialogue":
        quote = partner_quote_from_block(block)
        if quote.strip().lower() == ql.strip() and cid != "subject.dialog.partner_recent":
            score += 24
        if cid == "subject.dialog.partner_recent" and quote.strip().lower() == ql.strip():
            score = min(score, 6)
        if quote and partner_speech_turn(
            quote,
            intent="social",
            concept_hints=concept_hints,
            blocks=blocks,
        ):
            score += 36
        elif cid == "subject.dialog.partner_recent":
            score += 16
        if cid == "subject.dialog.self_recent":
            score += 6

    if partner_speech_query and cid.startswith("ru.dialog."):
        score += 4

    return score
