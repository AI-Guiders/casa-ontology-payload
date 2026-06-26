"""Continuer bind deltas from bundle policy — decay + field overlap, not flat +72."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.dialog_bind_policy import (
    continuer_bind_demote,
    thread_carry_params,
)
from casa.domain.dialogue_bind.partner_scoring import continuer_active, partner_field_overlap
from casa.prisms.memory.concept_layer import discourse_concept_id


def _focus_slots(block: dict[str, Any]) -> dict[str, str]:
    slots = block.get("slots")
    if not isinstance(slots, dict):
        return {}
    return {str(k): str(v) for k, v in slots.items()}


def apply_continuer_bind_deltas(
    blocks: list[dict[str, Any]],
    query: str,
    *,
    intent: str,
    bundle: dict[str, Any] | None = None,
) -> None:
    if intent != "social" or not continuer_active(blocks):
        return
    params = thread_carry_params(bundle)
    base = int(params["carry_base"])
    decay_per_age = float(params["decay_per_age"])
    ov_cap = int(params["ov_cap"])
    ov_mul = int(params["ov_mul"])
    demotes = continuer_bind_demote(bundle)

    focus_block: dict[str, Any] | None = None
    for block in blocks:
        if str(block.get("concept_id") or "") == "dialog.context.focus_recent":
            focus_block = block
            break

    focus_slots = _focus_slots(focus_block) if focus_block else {}
    thread_age = int(focus_slots.get("thread_age") or 0)
    stored_ov = int(focus_slots.get("thread_overlap") or 0)
    decay = max(0.25, 1.0 - thread_age * decay_per_age)
    on_topic = stored_ov >= 8 or partner_field_overlap(query, focus_block or {}) >= 8

    for block in blocks:
        cid = str(block.get("concept_id") or "")
        if cid == "dialog.context.focus_recent":
            ov = max(stored_ov, partner_field_overlap(query, block))
            delta = round(base * decay) + min(ov_cap, ov * ov_mul)
            block["score"] = int(block.get("score") or 0) + delta
        elif cid == "subject.dialog.self_recent":
            if on_topic:
                block["score"] = int(block.get("score") or 0) + 36
        elif cid == "subject.dialog.partner_recent":
            if on_topic:
                block["score"] = int(block.get("score") or 0) + 28
        elif cid == "dialog.context.referent":
            block["score"] = int(block.get("score") or 0) + round(base * decay * 0.6) + 18
        else:
            disc = discourse_concept_id(block)
            delta = 0
            for prefix, nudge in demotes:
                if cid.startswith(prefix) or disc.startswith(prefix):
                    if partner_field_overlap(query, block) < 8:
                        delta -= nudge
            if delta:
                block["score"] = max(0, int(block.get("score") or 0) + delta)
