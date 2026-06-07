#!/usr/bin/env python3
"""Build discourse sketch from ranked bind blocks."""

from __future__ import annotations

from typing import Any

from casa.prisms.tick.discourse.model import DiscourseContext, DiscourseSketch, PhraseSketch
from casa.prisms.tick.discourse.policy import BlockDiscoursePolicy
from casa.prisms.tick.discourse.realizers.blocks import MorphBlockRealizer, default_block_realizer_registry
from casa.prisms.tick.discourse.realizers.base import BlockRealizerRegistry
from casa.prisms.tick.discourse.render import paragraph_breaks


class DiscourseSketchBuilder:
    def __init__(
        self,
        registry: BlockRealizerRegistry | None = None,
        policy: BlockDiscoursePolicy | None = None,
    ) -> None:
        self._registry = registry or default_block_realizer_registry()
        self._policy = policy or BlockDiscoursePolicy()

    def build(self, ctx: DiscourseContext) -> DiscourseSketch | None:
        budget = ctx.budget
        clauses = []
        clause_scores: list[int] = []
        seen_cid: set[str] = set()
        seen_clause: set[str] = set()

        morph = MorphBlockRealizer.morph_clause(ctx.blocks)
        if morph and ctx.blocks:
            top_score = max(int(b.get("score") or 0) for b in ctx.blocks)
            key = " ".join(morph.pieces).strip().lower()
            if key:
                clauses.append(morph)
                clause_scores.append(top_score)
                seen_clause.add(key)

        for block in ctx.blocks:
            score = int(block.get("score") or 0)
            if score < budget.score_floor:
                break
            cid = str(block.get("concept_id") or "")
            if not cid or cid in seen_cid:
                continue
            if not self._policy.eligible(block, ctx):
                continue
            new = self._registry.realize(block, ctx)
            if not new:
                continue
            for clause in new:
                if not clause or not clause.pieces:
                    continue
                key = " ".join(clause.pieces).strip().lower()
                if not key or key in seen_clause:
                    continue
                seen_clause.add(key)
                clauses.append(clause)
                clause_scores.append(score)
            seen_cid.add(cid)

        if not clauses:
            return None
        return DiscourseSketch(clauses, paragraph_after=paragraph_breaks(clause_scores))


def infer_discourse_sketch(
    blocks: list[dict[str, Any]],
    query: str,
    *,
    stance: str = "partial",
    query_intent: str = "general",
) -> DiscourseSketch | None:
    ctx = DiscourseContext.bind(query, blocks, query_intent=query_intent, stance=stance)
    return DiscourseSketchBuilder().build(ctx)


def infer_phrase_sketch(
    blocks: list[dict[str, Any]],
    query: str,
    *,
    stance: str = "partial",
) -> PhraseSketch | None:
    disc = infer_discourse_sketch(blocks, query, stance=stance)
    if not disc or not disc.clauses:
        return None
    c = disc.clauses[0]
    return PhraseSketch(c.pieces, closing=c.closing)
