from __future__ import annotations

from typing import Any

from casa.prisms.tick.articulation_realize import UtterancePlan
from casa.prisms.tick.discourse.model import DiscourseContext
from casa.prisms.tick.discourse.policy import BlockDiscoursePolicy
from casa.prisms.tick.discourse.render import render_discourse
from casa.prisms.tick.discourse.rewrite import (
    anchors_present,
    passage_fact_anchors,
    rewrite_fact_assembly,
    rewrite_from_props,
)
from casa.prisms.tick.passage import split_passage_query


class RewriteIntentStrategy:
    intent = "rewrite"

    def compose(self, plan: UtterancePlan, ctx: DiscourseContext, composer: Any) -> str | None:
        passage, question = split_passage_query(ctx.query)
        if not passage:
            return composer.field_text(ctx.with_intent("discuss"))

        anchors = passage_fact_anchors(passage)
        prop_rewrite = rewrite_from_props(ctx.blocks, question or ctx.query)
        if prop_rewrite and not BlockDiscoursePolicy._is_formal_passage_sentence(prop_rewrite):
            if not anchors or anchors_present(prop_rewrite, anchors):
                return prop_rewrite

        disc = composer.infer_sketch(ctx.with_intent("rewrite", focus_query=question or ctx.query))
        if disc and disc.clauses:
            out = render_discourse(disc)
            if out and not BlockDiscoursePolicy._is_formal_passage_sentence(out):
                if not anchors or anchors_present(out, anchors):
                    return out

        assembled = rewrite_fact_assembly(passage, question or ctx.query)
        if assembled:
            return assembled
        return composer.recall_text(ctx)
