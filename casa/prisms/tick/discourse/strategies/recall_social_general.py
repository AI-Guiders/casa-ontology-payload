from __future__ import annotations

from typing import Any

from casa.prisms.tick.articulation_realize import UtterancePlan
from casa.prisms.tick.discourse.model import DiscourseContext, DiscourseSketch
from casa.prisms.tick.discourse.policy import BlockDiscoursePolicy
from casa.prisms.tick.discourse.realizers.blocks import DialogBlockRealizer
from casa.prisms.tick.discourse.render import render_discourse
from casa.prisms.tick.discourse.strategies.base import _SOCIAL_DIALOG_DENY
from casa.prisms.tick.discourse.wm import WmBlockRealizer


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
        policy = BlockDiscoursePolicy()
        dialog = DialogBlockRealizer()
        wm = WmBlockRealizer()
        budget = ctx.budget
        brief = ctx.partner_is_brief()
        top_block: dict | None = None

        for block in ctx.blocks:
            score = int(block.get("score") or 0)
            if score < budget.score_floor:
                break
            if not policy.eligible(block, ctx):
                continue
            if block.get("source") == "wm_prism":
                top_block = block
                break
            cid = str(block.get("concept_id") or "")
            if not cid.startswith("ru.dialog."):
                continue
            if any(cid.startswith(p) for p in _SOCIAL_DIALOG_DENY):
                continue
            top_block = block
            break

        if not top_block:
            return None

        if top_block.get("source") == "wm_prism":
            clauses = wm.realize(top_block, ctx, allow_tail=not brief)
        else:
            clauses = dialog.realize(top_block, ctx)
        if not clauses:
            return None
        return render_discourse(DiscourseSketch(clauses, paragraph_after=set()))


class GeneralIntentStrategy:
    intent = "general"

    def compose(self, plan: UtterancePlan, ctx: DiscourseContext, composer: Any) -> str | None:
        return composer.infer_text(ctx)
