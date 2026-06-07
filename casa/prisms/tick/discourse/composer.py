#!/usr/bin/env python3
"""Subject discourse composer — orchestrates intent strategies and sketch builder."""

from __future__ import annotations

from typing import Any

from casa.prisms.tick.articulation_realize import UtterancePlan
from casa.prisms.tick.discourse.model import DiscourseContext, DiscourseSketch
from casa.prisms.tick.discourse.realizers.blocks import JournalBlockRealizer, default_block_realizer_registry
from casa.prisms.tick.discourse.render import paragraph_breaks, render_discourse
from casa.prisms.tick.discourse.sketch import DiscourseSketchBuilder
from casa.prisms.tick.discourse.slots import BlockSlots
from casa.prisms.tick.discourse.strategies import IntentStrategyRegistry, default_intent_strategies
from casa.prisms.tick.passage import passage_focus_question, split_passage_query

_COMPOSER: SubjectDiscourseComposer | None = None


class SubjectDiscourseComposer:
    """Facade for subject articulation — intent → strategy → sketch/render."""

    def __init__(
        self,
        *,
        sketch_builder: DiscourseSketchBuilder | None = None,
        strategies: dict[str, Any] | None = None,
        registry: IntentStrategyRegistry | None = None,
    ) -> None:
        self._sketch_builder = sketch_builder or DiscourseSketchBuilder()
        self._registry = registry or IntentStrategyRegistry(strategies or default_intent_strategies())
        self._journal_realizer = JournalBlockRealizer()

    def register_strategy(self, intent: str, strategy: Any) -> None:
        self._registry._base[intent] = strategy

    def compose(
        self,
        plan: UtterancePlan,
        query: str,
        blocks: list[dict[str, Any]],
        *,
        query_intent: str,
        stance: str = "partial",
        agent_tract_profile: dict[str, Any] | None = None,
    ) -> str | None:
        ctx = DiscourseContext.bind(
            query,
            blocks,
            query_intent=query_intent,
            stance=stance,
            agent_tract_profile=agent_tract_profile,
        )
        strategy = self._registry.resolve(query_intent, agent_tract_profile)
        return strategy.compose(plan, ctx, self)

    def infer_sketch(self, ctx: DiscourseContext) -> DiscourseSketch | None:
        return self._sketch_builder.build(ctx)

    def infer_text(self, ctx: DiscourseContext) -> str | None:
        disc = self.infer_sketch(ctx)
        if disc and disc.clauses:
            return render_discourse(disc)
        return None

    def field_text(self, ctx: DiscourseContext) -> str | None:
        passage, question = split_passage_query(ctx.query)
        focus = passage_focus_question(ctx.query) if passage else (question or ctx.query)
        focus_ctx = ctx.with_intent(ctx.query_intent, focus_query=focus)
        disc = self.infer_sketch(focus_ctx)
        if not disc or not disc.clauses:
            return self.recall_text(ctx)
        linkers = BlockSlots.meta_linkers(ctx.blocks)
        for i, clause in enumerate(disc.clauses[1:]):
            if not clause.linker and i < len(linkers) and linkers[i]:
                clause.linker = linkers[i]
        return render_discourse(disc)

    def recall_text(self, ctx: DiscourseContext) -> str | None:
        budget = ctx.budget
        clauses = []
        clause_scores: list[int] = []
        for block in ctx.blocks:
            score = int(block.get("score") or 0)
            if score < budget.score_floor:
                break
            if str(block.get("section") or "") != "confirmed" and block.get("source") != "journal":
                continue
            for c in self._journal_realizer.realize(block, ctx):
                clauses.append(c)
                clause_scores.append(score)
        if not clauses:
            return None
        return render_discourse(DiscourseSketch(clauses, paragraph_after=paragraph_breaks(clause_scores)))


def default_composer() -> SubjectDiscourseComposer:
    global _COMPOSER
    if _COMPOSER is None:
        _COMPOSER = SubjectDiscourseComposer()
    return _COMPOSER
