#!/usr/bin/env python3
"""Dialogue provenance — intent + meaning props for journal prior (ADR-0053 v2)."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind import SubjectDialogueContext


def _rank_bind_candidates(ctx: SubjectDialogueContext) -> list[dict[str, Any]]:
    """Rank dialogue bind candidates — shared by bind_trace and impulse summary."""
    from casa.domain.dialogue_bind.partner_scoring import partner_field_overlap, partner_quote_from_block
    from casa.domain.dialogue_bind.speech_act_scoring import active_speech_act_slots
    from casa.prisms.memory.concept_layer import discourse_concept_id

    query = ""
    for row in ctx.blocks:
        if str(row.get("concept_id") or "") == "subject.dialog.partner_recent":
            query = partner_quote_from_block(row)
            break

    route_hints: list[str] = []
    slots = active_speech_act_slots(ctx.blocks)
    if slots.get("route_hints"):
        route_hints = [p.strip() for p in str(slots["route_hints"]).split("|") if p.strip()]

    def _hint_rank(hub: str) -> int:
        for index, prefix in enumerate(route_hints):
            if hub.startswith(prefix):
                return index
        return len(route_hints) + 9

    ranked: list[tuple[int, int, int, dict[str, Any]]] = []
    for row in ctx.blocks:
        cid = str(row.get("concept_id") or "")
        hub = str(row.get("bind_hub") or discourse_concept_id(row))
        if not hub.startswith("ru.dialog."):
            continue
        if not (cid.startswith("ru.dialog.") or row.get("bind_hub")):
            continue
        score = int(row.get("score") or 0)
        overlap = partner_field_overlap(query, row) if query else 0
        phrase = ""
        row_slots = row.get("slots") if isinstance(row.get("slots"), dict) else {}
        if row_slots:
            phrase = str(row_slots.get("phrase") or row.get("text") or "")[:120]
        trace_row = {
            "winner_concept_id": cid,
            "winner_bind_hub": hub,
            "winner_score": score,
            "winner_source": str(row.get("source") or ""),
        }
        if phrase:
            trace_row["winner_phrase"] = phrase
        ranked.append((score, -overlap, _hint_rank(hub), trace_row))

    if not ranked:
        return []
    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [item[3] for item in ranked]


def bind_trace(ctx: SubjectDialogueContext) -> dict[str, Any]:
    """Top bind winner for verify — route-hint tie-break, not list order."""
    rows = _rank_bind_candidates(ctx)
    return rows[0] if rows else {}


def bind_trace_ranked(ctx: SubjectDialogueContext, *, top: int = 3) -> dict[str, Any]:
    """Winner + runner-up rows for impulse summary (ADR-0080)."""
    rows = _rank_bind_candidates(ctx)
    if not rows:
        return {"candidate_count": 0}
    return {
        "candidate_count": len(rows),
        "winner": rows[0],
        "runner_up": rows[1 : 1 + int(top)],
    }


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
    trace = bind_trace(ctx)
    if trace:
        out["bind_trace"] = trace
    return out
