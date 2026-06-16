from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.affect_surface import apply_affect_register
from casa.domain.dialogue_bind.field import looks_like_field_recall
from casa.prisms.tick.articulation_realize import UtterancePlan
from casa.prisms.tick.discourse.model import DiscourseContext
from casa.prisms.tick.discourse.policy import BlockDiscoursePolicy
from casa.prisms.tick.discourse.realizers.blocks import DialogBlockRealizer
from casa.prisms.tick.discourse.strategies.base import _SOCIAL_DIALOG_DENY
from casa.prisms.tick.discourse.wm import WmBlockRealizer


def _compose_social_dialog_from_bind(
    ctx: DiscourseContext,
    composer: Any,
    *,
    dialog: DialogBlockRealizer,
    policy: BlockDiscoursePolicy,
) -> str | None:
    """Render bind-ranked ru.dialog utterances — field competition, not speech-act hub paste."""
    from casa.prisms.memory.concept_layer import discourse_concept_id
    from casa.prisms.tick.discourse.meta_glue_guard import should_suppress_dialog_script_efferent

    budget = ctx.budget
    hub_limit = 1 if ctx.partner_is_brief() else 2
    seen_hub: set[str] = set()
    seen_clause: set[str] = set()
    clauses = []
    scores: list[int] = []
    skipped_meta: list[str] = []

    for block in ctx.blocks:
        score = int(block.get("score") or 0)
        floor = budget.score_floor if not seen_hub else max(4, budget.score_floor - 40)
        if score < floor:
            continue
        cid = discourse_concept_id(block)
        hub = str(block.get("bind_hub") or cid)
        if not cid.startswith("ru.dialog.") or hub in seen_hub:
            continue
        if any(cid.startswith(p) for p in _SOCIAL_DIALOG_DENY):
            continue
        if not policy.eligible(block, ctx):
            continue
        if should_suppress_dialog_script_efferent(
            block, ctx.blocks, query=ctx.query, concept_hints=ctx.concept_hints
        ):
            skipped_meta.append(cid)
            continue
        extra = dialog.realize(block, ctx)
        if not extra:
            continue
        for clause in extra:
            key = " ".join(clause.pieces).strip().lower()
            if not key or key in seen_clause:
                continue
            apply_affect_register(clause, ctx)
            seen_clause.add(key)
            clauses.append(clause)
            scores.append(score)
        seen_hub.add(hub)
        if len(seen_hub) >= hub_limit:
            break

    if clauses:
        from casa.nervous.compose_impulse import record_compose_select
        from casa.prisms.memory.concept_layer import discourse_concept_id

        top_hub = ""
        for block in ctx.blocks:
            cid = discourse_concept_id(block)
            if cid.startswith("ru.dialog.") and int(block.get("score") or 0) >= budget.score_floor:
                top_hub = cid
                break
        record_compose_select(
            ctx.state,
            "discourse.social_bind",
            zone="social",
            selected=[top_hub] if top_hub else [],
            inputs={
                "clause_count": len(clauses),
                "skipped_meta_glue": skipped_meta[:4],
            },
        )

    if not clauses:
        return None
    return composer._render_discourse(clauses, scores)


class RecallIntentStrategy:
    intent = "recall"

    def compose(self, plan: UtterancePlan, ctx: DiscourseContext, composer: Any) -> str | None:
        body = composer.field_text(ctx.with_intent("discuss"))
        if body:
            return body
        return composer.recall_text(ctx)


class SocialIntentStrategy:
    intent = "social"

    def compose(self, plan: UtterancePlan, ctx: DiscourseContext, composer: Any) -> str | None:
        if looks_like_field_recall(ctx.query):
            explain_ctx = ctx.with_intent("explain")
            body = composer.recall_text(explain_ctx)
            if body:
                return body

        policy = BlockDiscoursePolicy()
        dialog = DialogBlockRealizer()
        wm = WmBlockRealizer()
        budget = ctx.budget
        brief = ctx.partner_is_brief()

        from casa.prisms.tick.discourse.situated import compose_situated_thread

        body = compose_situated_thread(ctx, composer, dialog=dialog, policy=policy)
        if body:
            return body

        body = _compose_social_dialog_from_bind(ctx, composer, dialog=dialog, policy=policy)
        if body:
            return body

        wm_block: dict | None = None
        for block in ctx.blocks:
            score = int(block.get("score") or 0)
            if score < budget.score_floor:
                break
            if not policy.eligible(block, ctx):
                continue
            if block.get("source") == "wm_prism" and wm_block is None:
                wm_block = block

        if not wm_block:
            body = composer.infer_text(ctx)
            if body:
                return body
            return None
        clauses = wm.realize(wm_block, ctx, allow_tail=not brief)
        if not clauses:
            return None
        score = int(wm_block.get("score") or 0)
        return composer._render_discourse(clauses, [score] * len(clauses))


class GeneralIntentStrategy:
    intent = "general"

    def compose(self, plan: UtterancePlan, ctx: DiscourseContext, composer: Any) -> str | None:
        if looks_like_field_recall(ctx.query):
            from casa.prisms.tick.discourse.strategies.explain import ExplainIntentStrategy

            return ExplainIntentStrategy().compose(plan, ctx.with_intent("explain"), composer)
        return composer.infer_text(ctx)
