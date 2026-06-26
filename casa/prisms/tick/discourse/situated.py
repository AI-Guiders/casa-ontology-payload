"""Situated social compose — bind-winner + linker when thread focus is active."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.affect_surface import apply_affect_register
from casa.domain.dialogue_bind.dialog_bind_policy import continuer_linker
from casa.domain.dialogue_bind.partner_scoring import (
    continuer_active,
    thread_continuation_active,
    thread_continuer_turn,
)
from casa.nervous.compose_impulse import record_compose_select
from casa.prisms.tick.discourse.meta_glue_guard import (
    dialogue_thread_carries,
    referent_prop_from_blocks,
    should_suppress_dialog_script_efferent,
)
from casa.prisms.tick.discourse.model import DiscourseContext
from casa.prisms.tick.discourse.policy import BlockDiscoursePolicy
from casa.prisms.tick.discourse.realizers.blocks import DialogBlockRealizer
from casa.prisms.tick.discourse.strategies.base import _SOCIAL_DIALOG_DENY


def _situated_thread_open(blocks: list[dict[str, Any]], query: str) -> bool:
    """Dialogue ring carries thread — no speech-act class gate."""
    if referent_prop_from_blocks(blocks):
        return continuer_active(blocks) or thread_continuation_active(blocks, query)
    if not continuer_active(blocks):
        return False
    if thread_continuer_turn(blocks, query):
        return True
    return thread_continuation_active(blocks, query)


def _situated_winner_priority(block: dict[str, Any]) -> tuple[int, int]:
    """Live thread: partner/dialogue substance before phatic ru.dialog hubs."""
    from casa.prisms.memory.concept_layer import discourse_concept_id

    cid = discourse_concept_id(block)
    source = str(block.get("source") or "")
    lane = 0
    if cid == "subject.dialog.partner_recent" or cid == "subject.limbic.state":
        lane = 4
    elif cid.startswith("subject."):
        lane = 3
    elif cid == "dialog.context.focus_recent":
        lane = 0
    elif source == "dialogue":
        lane = 2
    elif cid.startswith("ru.dialog.honest.") or cid.startswith("ru.dialog.self"):
        lane = 2
    elif cid.startswith("ru.dialog."):
        lane = 1
    return (lane, int(block.get("score") or 0))


def _minimal_formula_matches(block: dict[str, Any], ctx: DiscourseContext) -> bool:
    slots = block.get("slots") if isinstance(block.get("slots"), dict) else {}
    stimulus = str(slots.get("stimulus") or slots.get("word") or "").strip().lower()
    response = str(slots.get("response") or slots.get("response_informal") or "").strip()
    return bool(stimulus and response and stimulus in ctx.tokens)


def compose_situated_thread(
    ctx: DiscourseContext,
    composer: Any,
    *,
    dialog: DialogBlockRealizer,
    policy: BlockDiscoursePolicy,
) -> str | None:
    """focus/referent thread: bind-winner + linker; skip meta-glue when referent carries."""
    from casa.prisms.memory.concept_layer import discourse_concept_id

    referent = referent_prop_from_blocks(ctx.blocks)
    if not _situated_thread_open(ctx.blocks, ctx.query):
        return None

    linker = continuer_linker()
    budget = ctx.budget
    potentials: list[dict[str, Any]] = []
    skipped_meta: list[str] = []
    candidates: list[dict[str, Any]] = []
    thread_carries = dialogue_thread_carries(ctx.blocks)

    for block in ctx.blocks:
        score = int(block.get("score") or 0)
        if score < budget.score_floor:
            break
        cid = discourse_concept_id(block)
        if cid.startswith("ru.dialog."):
            if any(cid.startswith(p) for p in _SOCIAL_DIALOG_DENY):
                continue
            if not policy.eligible(block, ctx):
                continue
            if _minimal_formula_matches(block, ctx):
                pass
            elif should_suppress_dialog_script_efferent(
                block, ctx.blocks, query=ctx.query, concept_hints=ctx.concept_hints
            ):
                skipped_meta.append(cid)
                potentials.append({"concept_id": cid, "score": score, "suppressed": "dialog_script"})
                continue
        elif block.get("source") not in ("journal", "dialogue", "limbic"):
            continue
        elif not policy.eligible(block, ctx):
            continue
        else:
            if cid and not cid.startswith(("ru.prop.", "subject.", "dialog.context.")):
                continue

        potentials.append({"concept_id": cid or str(block.get("source")), "score": score})
        candidates.append(block)

    if thread_carries:
        candidates.sort(
            key=lambda row: (
                1 if _minimal_formula_matches(row, ctx) else 0,
                *_situated_winner_priority(row),
            ),
            reverse=True,
        )
    else:
        candidates.sort(key=lambda row: int(row.get("score") or 0), reverse=True)

    winner_block: dict[str, Any] | None = None
    winner_score = 0
    winner_clause = None

    for block in candidates:
        score = int(block.get("score") or 0)
        cid = discourse_concept_id(block)
        if cid.startswith("subject."):
            continue
        clauses = dialog.realize(block, ctx)
        if not clauses:
            continue
        head = clauses[0]
        if cid.startswith("ru.dialog."):
            head.linker = linker
        apply_affect_register(head, ctx)
        winner_block = block
        winner_score = score
        winner_clause = head
        break

    if winner_block is None or winner_clause is None:
        return None

    winner_cid = discourse_concept_id(winner_block) or str(winner_block.get("concept_id") or "")
    record_compose_select(
        ctx.state,
        "discourse.situated_thread",
        zone="social",
        selected=[winner_cid],
        potentials=potentials[:6],
        rejected_above_floor=max(0, len(potentials) - 1),
        inputs={
            "linker": linker,
            "referent_prop": referent,
            "thread_carries": thread_carries,
            "skipped_meta_glue": skipped_meta[:4],
        },
    )
    return composer._render_discourse([winner_clause], [winner_score])
