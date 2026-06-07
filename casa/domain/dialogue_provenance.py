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
    return out
