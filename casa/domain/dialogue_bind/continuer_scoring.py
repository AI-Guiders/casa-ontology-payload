"""Continuer bind deltas from bundle policy — not compose substring rules."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.dialog_bind_policy import continuer_bind_demote
from casa.domain.dialogue_bind.partner_scoring import continuer_active, partner_field_overlap
from casa.prisms.memory.concept_layer import discourse_concept_id


def apply_continuer_bind_deltas(
    blocks: list[dict[str, Any]],
    query: str,
    *,
    intent: str,
    bundle: dict[str, Any] | None = None,
) -> None:
    if intent != "social" or not continuer_active(blocks):
        return
    demotes = continuer_bind_demote(bundle)
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
            delta = 0
            for prefix, nudge in demotes:
                if cid.startswith(prefix) or disc.startswith(prefix):
                    if partner_field_overlap(query, block) < 8:
                        delta -= nudge
            if delta:
                block["score"] = max(0, int(block.get("score") or 0) + delta)
