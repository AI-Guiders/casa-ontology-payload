from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.field import looks_like_field_recall
from casa.domain.dialogue_bind.scoring import (
    partner_dialog_bind_overlap,
    partner_quote_from_block,
    partner_speech_turn,
)
from casa.prisms.tick.articulation_realize import UtterancePlan
from casa.prisms.tick.discourse.model import DiscourseContext
from casa.prisms.tick.discourse.policy import BlockDiscoursePolicy
from casa.prisms.tick.discourse.realizers.blocks import DialogBlockRealizer
from casa.prisms.tick.discourse.strategies.base import _SOCIAL_DIALOG_DENY
from casa.prisms.tick.discourse.wm import WmBlockRealizer


def _compose_partner_intro_reply(
    partner_block: dict[str, Any],
    ctx: DiscourseContext,
    composer: Any,
    *,
    dialog: DialogBlockRealizer,
    policy: BlockDiscoursePolicy,
) -> str | None:
    quote = partner_quote_from_block(partner_block)
    if not quote or not partner_speech_turn(
        quote,
        intent=ctx.query_intent,
        concept_hints=ctx.concept_hints,
        blocks=ctx.blocks,
    ):
        return None

    teaching = partner_dialog_bind_overlap(quote, ctx.blocks) >= 8
    budget = ctx.budget
    clauses = []
    scores: list[int] = []

    bind_blocks: list[dict[str, Any]] = []
    for block in ctx.blocks:
        score = int(block.get("score") or 0)
        if score < budget.score_floor:
            break
        if not policy.eligible(block, ctx):
            continue
        cid = str(block.get("concept_id") or "")
        if teaching and cid.startswith("ru.dialog.capabilities"):
            bind_blocks.append(block)
        elif not teaching and cid.startswith("ru.dialog.thanks"):
            bind_blocks.append(block)

    if teaching:
        for block in ctx.blocks:
            score = int(block.get("score") or 0)
            if score < budget.score_floor:
                break
            if not policy.eligible(block, ctx):
                continue
            cid = str(block.get("concept_id") or "")
            if cid.startswith("ru.dialog.thanks"):
                bind_blocks.insert(0, block)
                break

    for block in bind_blocks[:2]:
        extra = dialog.realize(block, ctx)
        take = 1 if teaching and str(block.get("concept_id") or "").startswith("ru.dialog.capabilities") else min(2, len(extra))
        for clause in extra[:take]:
            clauses.append(clause)
            scores.append(int(block.get("score") or 0))

    if not clauses:
        return None
    return composer._render_discourse(clauses, scores)


def _compose_social_dialog_from_bind(
    ctx: DiscourseContext,
    composer: Any,
    *,
    dialog: DialogBlockRealizer,
    policy: BlockDiscoursePolicy,
) -> str | None:
    """Stack ru.dialog blocks by bind score (order already in reweight) until floor."""
    budget = ctx.budget
    seen_cid: set[str] = set()
    seen_clause: set[str] = set()
    clauses = []
    scores: list[int] = []

    for block in ctx.blocks:
        score = int(block.get("score") or 0)
        if score < budget.score_floor:
            break
        cid = str(block.get("concept_id") or "")
        if not cid.startswith("ru.dialog.") or cid in seen_cid:
            continue
        if any(cid.startswith(p) for p in _SOCIAL_DIALOG_DENY):
            continue
        if not policy.eligible(block, ctx):
            continue
        extra = dialog.realize(block, ctx)
        if not extra:
            continue
        for clause in extra:
            key = " ".join(clause.pieces).strip().lower()
            if not key or key in seen_clause:
                continue
            seen_clause.add(key)
            clauses.append(clause)
            scores.append(score)
        seen_cid.add(cid)

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

        for block in ctx.blocks:
            if block.get("concept_id") != "subject.dialog.partner_recent":
                continue
            if not policy.eligible(block, ctx):
                continue
            quote = partner_quote_from_block(block)
            if quote and partner_speech_turn(
                quote,
                intent=ctx.query_intent,
                concept_hints=ctx.concept_hints,
                blocks=ctx.blocks,
            ):
                body = _compose_partner_intro_reply(
                    block,
                    ctx,
                    composer,
                    dialog=dialog,
                    policy=policy,
                )
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
