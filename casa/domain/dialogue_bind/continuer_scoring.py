"""Continuer bind deltas — focus block from dialogue ring, not compose substring rules."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.partner_scoring import continuer_active, partner_field_overlap


def apply_continuer_bind_deltas(
    blocks: list[dict[str, Any]],
    query: str,
    *,
    intent: str,
) -> None:
    if intent != "social" or not continuer_active(blocks):
        return
    from casa.prisms.memory.concept_layer import discourse_concept_id

    for block in blocks:
        cid = str(block.get("concept_id") or "")
        if cid == "dialog.context.focus_recent":
            block["score"] = int(block.get("score") or 0) + 72
        elif cid == "subject.dialog.self_recent":
            block["score"] = int(block.get("score") or 0) + 36
        elif cid == "subject.dialog.partner_recent":
            block["score"] = int(block.get("score") or 0) + 28
        else:
            disc = discourse_concept_id(block)
            if disc.startswith(("ru.dialog.affect", "ru.dialog.self", "ru.dialog.capabilities")):
                if partner_field_overlap(query, block) < 8:
                    block["score"] = max(0, int(block.get("score") or 0) - 58)
