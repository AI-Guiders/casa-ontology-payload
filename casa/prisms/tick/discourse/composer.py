#!/usr/bin/env python3
"""Subject discourse composer — orchestrates intent strategies and sketch builder."""

from __future__ import annotations

from typing import Any

from casa.prisms.tick.articulation_realize import UtterancePlan
from casa.prisms.tick.discourse.model import ClauseSketch, DiscourseContext, DiscourseSketch
from casa.prisms.tick.discourse.policy import BlockDiscoursePolicy
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
        concept_hints: list[str] | None = None,
        runtime_state: dict | None = None,
    ) -> str | None:
        ctx = DiscourseContext.bind(
            query,
            blocks,
            query_intent=query_intent,
            stance=stance,
            agent_tract_profile=agent_tract_profile,
            concept_hints=concept_hints,
            state=runtime_state,
        )
        strategy = self._registry.resolve(query_intent, agent_tract_profile)
        return strategy.compose(plan, ctx, self)

    def infer_sketch(self, ctx: DiscourseContext) -> DiscourseSketch | None:
        return self._sketch_builder.build(ctx)

    def infer_text(self, ctx: DiscourseContext) -> str | None:
        disc = self.infer_sketch(ctx)
        if not disc or not disc.clauses:
            return None
        scores = [max(1, len(disc.clauses) - i) for i in range(len(disc.clauses))]
        return self._render_discourse(disc.clauses, scores)

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
        if ctx.query_intent == "discuss" and disc.clauses:
            _, question = split_passage_query(ctx.query)
            focus = (question or passage_focus_question(ctx.query)).lower()
            if any(m in focus for m in ("почему", "зачем", "что случил", "что произош")):
                first = disc.clauses[0]
                body = " ".join(first.pieces).lower()
                if not any(m in body for m in ("похоже", "потому", "видимо", "значит", "скорее")):
                    first.pieces = ["Похоже,"] + list(first.pieces)
        return self._render_discourse(
            disc.clauses,
            [max(1, len(disc.clauses) - i) for i in range(len(disc.clauses))],
        )

    @staticmethod
    def _clause_key(clause: ClauseSketch) -> str:
        return " ".join(clause.pieces).strip().lower()

    def _render_discourse(
        self,
        clauses: list[ClauseSketch],
        clause_scores: list[int],
    ) -> str | None:
        """Render sketches — drop only verbatim duplicate clauses, not emergent length."""
        seen: set[str] = set()
        kept: list[ClauseSketch] = []
        kept_scores: list[int] = []
        for c, sc in zip(clauses, clause_scores):
            key = self._clause_key(c)
            if not key or key in seen:
                continue
            seen.add(key)
            kept.append(c)
            kept_scores.append(sc)
        if not kept:
            return None
        return render_discourse(DiscourseSketch(kept, paragraph_after=paragraph_breaks(kept_scores)))

    def _journal_blocks_for_recall(self, ctx: DiscourseContext) -> list[dict[str, Any]]:
        policy = BlockDiscoursePolicy()
        rows = [
            b
            for b in ctx.blocks
            if b.get("source") in ("journal", "dialogue")
            and policy._journal_eligible(b, ctx.query, ctx.query_intent)
        ]
        if not rows:
            rows = [b for b in ctx.blocks if b.get("source") == "journal"]
        if ctx.query.strip():
            matched = [b for b in rows if policy._journal_explain_overlap(b, ctx.query)]
            if matched:
                rows = matched
        rows.sort(
            key=lambda b: (policy.journal_overlap_score(b, ctx.query), int(b.get("score") or 0)),
            reverse=True,
        )
        if rows:
            top = policy.journal_overlap_score(rows[0], ctx.query)
            if top >= 2:
                rows = [b for b in rows if policy.journal_overlap_score(b, ctx.query) >= top - 1]
        return rows

    def recall_text(self, ctx: DiscourseContext) -> str | None:
        budget = ctx.budget
        clauses: list[ClauseSketch] = []
        clause_scores: list[int] = []
        for block in self._journal_blocks_for_recall(ctx):
            score = int(block.get("score") or 0)
            if score < budget.score_floor and not BlockDiscoursePolicy._journal_explain_overlap(block, ctx.query):
                continue
            for c in self._journal_realizer.realize(block, ctx):
                if BlockDiscoursePolicy.journal_overlap_score({"text": " ".join(c.pieces)}, ctx.query) == 0:
                    continue
                clauses.append(c)
                clause_scores.append(score)
            if score < budget.score_floor:
                break
        return self._render_discourse(clauses, clause_scores)


def default_composer() -> SubjectDiscourseComposer:
    global _COMPOSER
    if _COMPOSER is None:
        _COMPOSER = SubjectDiscourseComposer()
    return _COMPOSER
