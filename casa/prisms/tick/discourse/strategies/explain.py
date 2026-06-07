from __future__ import annotations

from typing import Any

from casa.prisms.tick.articulation_realize import UtterancePlan, _realize_compare
from casa.prisms.tick.discourse.model import ClauseSketch, DiscourseContext
from casa.prisms.tick.discourse.policy import BlockDiscoursePolicy
from casa.prisms.tick.discourse.realizers.blocks import (
    DialogBlockRealizer,
    GrammarBlockRealizer,
    JournalBlockRealizer,
    LexemeBlockRealizer,
)
from casa.prisms.tick.discourse.wm import WmBlockRealizer


class ExplainIntentStrategy:
    intent = "explain"

    def compose(self, plan: UtterancePlan, ctx: DiscourseContext, composer: Any) -> str | None:
        policy = BlockDiscoursePolicy()
        dialog = DialogBlockRealizer()
        grammar = GrammarBlockRealizer()
        lexeme = LexemeBlockRealizer()
        journal = JournalBlockRealizer()
        wm = WmBlockRealizer()
        budget = ctx.budget
        clauses: list[ClauseSketch] = []
        clause_scores: list[int] = []

        journal_hits = [b for b in ctx.blocks if b.get("source") == "journal" and policy._journal_explain_overlap(b, ctx.query)]
        journal_hits.sort(
            key=lambda b: (policy.journal_overlap_score(b, ctx.query), int(b.get("score") or 0)),
            reverse=True,
        )
        if journal_hits:
            top = policy.journal_overlap_score(journal_hits[0], ctx.query)
            if top >= 2:
                journal_hits = [
                    b for b in journal_hits if policy.journal_overlap_score(b, ctx.query) >= top - 1
                ]
        ordered = journal_hits + [b for b in ctx.blocks if b not in journal_hits]
        strong_journal = bool(journal_hits)

        for block in ordered:
            if strong_journal and block.get("source") != "journal":
                continue
            score = int(block.get("score") or 0)
            journal_hit = block.get("source") == "journal" and policy._journal_explain_overlap(block, ctx.query)
            if score < budget.score_floor and not journal_hit:
                break
            if not policy.eligible(block, ctx):
                continue
            cid = str(block.get("concept_id") or "")
            if block.get("source") == "journal":
                for c in journal.realize(block, ctx):
                    if policy.journal_overlap_score({"text": " ".join(c.pieces)}, ctx.query) == 0:
                        continue
                    clauses.append(c)
                    clause_scores.append(score + 6)
            elif cid.startswith("ru.dialog."):
                for c in dialog.narrative_clauses(block, ctx.query) or dialog.realize(block, ctx):
                    clauses.append(c)
                    clause_scores.append(score)
            elif cid.startswith("lang.word."):
                c = lexeme.gloss_clause(block) or lexeme._lexeme_clause(block, ctx)
                if c:
                    if clauses and not c.linker:
                        c.linker = "Это" if c.pieces and c.pieces[0].startswith("«") else ""
                    clauses.append(c)
                    clause_scores.append(score)
            elif block.get("source") == "wm_prism":
                for c in wm.realize(block, ctx, allow_tail=not ctx.partner_is_brief()):
                    clauses.append(c)
                    clause_scores.append(score)
            elif cid.startswith("ru.grammar."):
                for c in grammar.realize(block, ctx):
                    clauses.append(c)
                    clause_scores.append(score)

        cmp = _realize_compare(ctx.query, plan.atoms)
        if cmp and not clauses:
            clauses.append(ClauseSketch(cmp.rstrip(".!?").split(), closing="."))
            clause_scores.append(90)

        if not clauses:
            from casa.prisms.tick.passage import has_passage_context

            if has_passage_context(ctx.query):
                return composer.field_text(ctx.with_intent("discuss"))
            return None
        return composer._render_discourse(clauses, clause_scores)
