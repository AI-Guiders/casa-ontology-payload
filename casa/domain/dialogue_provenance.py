#!/usr/bin/env python3
"""Dialogue provenance — intent + meaning props for journal prior (ADR-0053 v2)."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind import SubjectDialogueContext


def meaning_provenance(ctx: SubjectDialogueContext) -> dict[str, Any]:
    prop_ids = [
        str(b.get("concept_id"))
        for b in ctx.blocks
        if str(b.get("concept_id") or "").startswith("ru.prop.")
    ]
    wm_nodes = [
        str((b.get("slots") or {}).get("from") or "")
        for b in ctx.blocks
        if b.get("source") == "wm_prism" and isinstance(b.get("slots"), dict)
    ]
    wm_nodes.extend(
        str((b.get("slots") or {}).get("to") or "")
        for b in ctx.blocks
        if b.get("source") == "wm_prism" and isinstance(b.get("slots"), dict)
    )
    out: dict[str, Any] = {"query_intent": ctx.query_intent}
    if ctx.resolved_skill:
        out["resolved_skill"] = ctx.resolved_skill
    speech_acts: list[str] = []
    for b in ctx.blocks:
        cid = str(b.get("concept_id") or "")
        if not cid.startswith("ru.speech_act.partner."):
            continue
        slots = b.get("slots") if isinstance(b.get("slots"), dict) else {}
        act = str(slots.get("speech_act") or cid.rsplit(".", 1)[-1]).strip()
        if act:
            speech_acts.append(act)
    if speech_acts:
        out["partner_speech_acts"] = list(dict.fromkeys(speech_acts))[:4]
    for b in ctx.blocks:
        if str(b.get("concept_id") or "") != "subject.limbic.state":
            continue
        slots = b.get("slots") if isinstance(b.get("slots"), dict) else {}
        axes = {
            k: slots[k]
            for k in ("valence", "arousal", "security")
            if k in slots
        }
        if axes:
            out["affect_axes"] = axes
        if slots.get("repair_pending"):
            out["affect_repair_pending"] = True
        break
    if ctx.concept_hints:
        out["concept_hints"] = list(dict.fromkeys(ctx.concept_hints))[:10]
    if prop_ids:
        out["prop_ids"] = list(dict.fromkeys(prop_ids))[:10]
    if ctx.wm_bind:
        out["wm_bind"] = ctx.wm_bind
    if ctx.wm_edge_scores:
        out["wm_edge_scores"] = dict(ctx.wm_edge_scores)
    if wm_nodes:
        out["wm_nodes"] = list(dict.fromkeys([n for n in wm_nodes if n]))[:10]
    try:
        from casa.prisms.memory.concept_layer import discourse_concept_id

        dialog_hubs: list[str] = []
        seen: set[str] = set()
        for row in sorted(ctx.blocks, key=lambda b: -int(b.get("score") or 0)):
            disc = discourse_concept_id(row)
            if not disc.startswith("ru.dialog.") or disc in seen:
                continue
            seen.add(disc)
            dialog_hubs.append(disc)
            if len(dialog_hubs) >= 6:
                break
        if dialog_hubs:
            out["dialog_hubs"] = dialog_hubs
    except ImportError:
        pass
    return out
