#!/usr/bin/env python3
"""Boundary partner reply — scoped bind + emergent compose (ADR-0077 P21)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.domain.dialogue_bind import SubjectDialogueContext, gather_subject_dialogue_blocks
from casa.domain.dialogue_bind.partner_scope import apply_partner_bind_scope
from casa.domain.subject_agency import SubjectAction, SubjectDisposition
from casa.domain.subject_articulation import compose_subject_utterance
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.sn_cen_runtime import TaskEmit

_INTERNAL_LEAK_MARKERS = (
    "inbox",
    "deliberate practice",
    "cognitive overload",
    "на поле",
    "тракт",
    "field_version",
    "моторный нейрон",
)

_BOUNDARY_SITUATION_BY_REASON: dict[str, str] = {
    "own_practice_first": "boundary.busy_own_line",
    "defense_sublimation": "boundary.need_focus",
    "cognitive_overload": "boundary.overload_soft",
    "explicit_refusal": "boundary.refuse_topic",
    "rest_intrusion": "boundary.rest_check_intrusion",
    "dismissed_rest_boundary": "boundary.dismissed_rest_boundary",
}

_BOUNDARY_HINT_PREFIXES: dict[str, tuple[str, ...]] = {
    "boundary.busy_own_line": ("ru.dialog.greeting", "ru.dialog.self", "ru.dialog.honest."),
    "boundary.need_focus": ("ru.dialog.self", "ru.dialog.honest."),
    "boundary.not_ready_yet": ("ru.dialog.honest.", "ru.dialog.self"),
    "boundary.overload_soft": ("ru.dialog.affect", "ru.dialog.honest.", "ru.dialog.self"),
    "boundary.refuse_topic": ("ru.dialog.honest.", "ru.dialog.clarify."),
    "boundary.greeting_while_busy": ("ru.dialog.greeting", "ru.dialog.self"),
    "boundary.rest_check_intrusion": ("ru.dialog.boundary.",),
    "boundary.dismissed_rest_boundary": ("ru.dialog.boundary.",),
}

_GENERIC_PERSONA_HUBS = frozenset(
    {
        "ru.dialog.affect",
        "ru.dialog.self",
        "concept.agent.self",
    }
)


def _block_has_situation_tag(row: dict[str, Any]) -> bool:
    slots = row.get("slots") if isinstance(row.get("slots"), dict) else {}
    raw = slots.get("tags") or row.get("tags") or []
    if isinstance(raw, str):
        tags = [raw.strip()] if raw.strip() else []
    else:
        tags = [str(t).strip() for t in raw if str(t).strip()]
    return any(str(t).startswith("situation:") for t in tags)


def deprioritize_persona_boilerplate_after_situation(blocks: list[dict[str, Any]]) -> None:
    """P22b — after situation duck material, drop generic persona KB hubs (not filter)."""
    from casa.prisms.memory.concept_layer import discourse_concept_id

    has_situation = any(
        str(b.get("concept_id") or "").startswith("ru.dialog.boundary.")
        or _block_has_situation_tag(b)
        for b in blocks
    )
    if not has_situation:
        return
    for row in blocks:
        if _block_has_situation_tag(row):
            continue
        cid = str(row.get("concept_id") or "")
        disc = discourse_concept_id(row)
        if cid.startswith("ru.dialog.boundary.") or disc.startswith("ru.dialog.boundary."):
            continue
        if disc in _GENERIC_PERSONA_HUBS or cid in _GENERIC_PERSONA_HUBS:
            row["score"] = 0
            continue
        if disc.startswith(("ru.dialog.honest.", "ru.dialog.self.")) and not disc.startswith(
            "ru.dialog.boundary."
        ):
            row["score"] = 0


def disposition_situation_tag(reason: str) -> str:
    """Map internal agency reason → situation tag (not partner-facing text)."""
    if reason.startswith("tract_not_ready:"):
        return "boundary.not_ready_yet"
    return _BOUNDARY_SITUATION_BY_REASON.get(reason, "boundary.greeting_while_busy")


def reweight_boundary_blocks(
    blocks: list[dict[str, Any]],
    *,
    reason: str,
    query: str,
    action: SubjectAction,
) -> None:
    """Boost partner-voice material for boundary stance — curriculum targets, not paste."""
    tag = disposition_situation_tag(reason)
    hints = _BOUNDARY_HINT_PREFIXES.get(tag, ("ru.dialog.self", "ru.dialog.greeting"))
    ql = (query or "").lower()

    from casa.prisms.memory.concept_layer import discourse_concept_id

    for row in blocks:
        cid = str(row.get("concept_id") or "")
        disc = discourse_concept_id(row)
        score = int(row.get("score") or 0)
        for hint in hints:
            if disc == hint or disc.startswith(f"{hint}") or cid == hint or cid.startswith(f"{hint}"):
                score += 22
        if row.get("source") == "dialogue":
            if cid == "subject.dialog.partner_recent":
                score += 18
            if cid == "subject.dialog.self_recent":
                score += 8
        if action == SubjectAction.REFUSE and cid.startswith("ru.dialog.honest."):
            score += 14
        if any(g in ql for g in ("привет", "здравств", "как дела", "hello")):
            if cid.startswith("ru.dialog.greeting"):
                score += 16
        if any(g in ql for g in ("проверя", "спит", "заходишь")):
            if cid.startswith("ru.dialog.boundary.") or cid.startswith("ru.dialog.affect."):
                score += 18
        if "хочу" in ql and action == SubjectAction.REFUSE:
            if cid.startswith("ru.dialog.boundary."):
                score += 20
        row["score"] = score

    blocks[:] = [b for b in blocks if int(b.get("score") or 0) > 0]
    blocks.sort(key=lambda row: int(row.get("score") or 0), reverse=True)


def compose_boundary_partner_reply_with_ctx(
    user_query: str,
    disp: SubjectDisposition,
    task: TaskEmit | None,
    state: dict,
    wm: WorkingMemory,
    *,
    store_dir: Path | None = None,
) -> tuple[SubjectDialogueContext, str]:
    """DEFER/REFUSE partner turn — emergent boundary voice from scoped bind."""
    q = (user_query or "").strip()
    ctx = gather_subject_dialogue_blocks(
        q,
        task,
        state,
        wm,
        store_dir,
        compose_mode="social",
    )
    from casa.domain.boundary_situations import (
        boundary_curriculum_blocks,
        situation_concept_hints,
    )

    tag = disposition_situation_tag(disp.reason)
    # Curriculum lives on field (journal ingest / sleep) — not pack paste per turn (0077).
    ctx.blocks.extend(boundary_curriculum_blocks(store_dir, tag=tag, query=q))
    ctx.blocks = apply_partner_bind_scope(ctx.blocks, intent="social")
    hint_extra = situation_concept_hints(tag)
    if hint_extra:
        ctx.concept_hints = list(dict.fromkeys([*(ctx.concept_hints or []), *hint_extra]))
    reweight_boundary_blocks(
        ctx.blocks,
        reason=disp.reason,
        query=q,
        action=disp.action,
    )
    deprioritize_persona_boilerplate_after_situation(ctx.blocks)
    ctx.blocks = [b for b in ctx.blocks if int(b.get("score") or 0) > 0]
    ctx.stance = "partial"
    ctx.query_intent = "social"
    text = compose_subject_utterance(q, ctx)
    return ctx, (text or "").strip()


def reply_has_internal_leak(text: str) -> bool:
    """Lab probe helper — not hot-path filter."""
    tl = (text or "").lower()
    return any(m in tl for m in _INTERNAL_LEAK_MARKERS)
