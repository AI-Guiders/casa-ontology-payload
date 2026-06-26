from __future__ import annotations

from typing import Any

from casa.prisms.tick.articulation_realize import UtterancePlan
from casa.prisms.tick.discourse.model import DiscourseContext, DiscourseSketch
from casa.prisms.tick.discourse.realizers.blocks import DialogBlockRealizer, GrammarBlockRealizer
from casa.prisms.tick.discourse.render import render_discourse


class GrammarIntentStrategy:
    intent = "grammar"

    def compose(self, plan: UtterancePlan, ctx: DiscourseContext, composer: Any) -> str | None:
        body = self._grammar_discourse(plan, ctx, composer)
        if body:
            return body
        return composer.recall_text(ctx)

    def _grammar_discourse(self, plan: UtterancePlan, ctx: DiscourseContext, composer: Any) -> str | None:
        dialog = DialogBlockRealizer()
        grammar = GrammarBlockRealizer()
        budget = ctx.budget

        for block in ctx.blocks:
            score = int(block.get("score") or 0)
            if score < budget.score_floor:
                break
            cid = str(block.get("concept_id") or "")
            new: list[ClauseSketch] = []
            if cid.startswith("ru.grammar."):
                new = grammar.realize(block, ctx)
            elif any(cid.startswith(p) for p in ("ru.dialog.clarify.", "ru.dialog.honest.")):
                new = dialog.realize(block, ctx)
            if not new:
                continue
            return render_discourse(DiscourseSketch(new, paragraph_after=set()))

        return None
