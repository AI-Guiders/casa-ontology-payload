#!/usr/bin/env python3
"""Discourse domain model — sketches and bind context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from casa.prisms.tick.discourse.budget import DiscourseBudget, discourse_budget_from_blocks


@dataclass
class ClauseSketch:
    pieces: list[str] = field(default_factory=list)
    closing: str = "."
    linker: str = ""


@dataclass
class DiscourseSketch:
    clauses: list[ClauseSketch] = field(default_factory=list)
    paragraph_after: set[int] = field(default_factory=set)


@dataclass
class PhraseSketch:
    pieces: list[str] = field(default_factory=list)
    closing: str = "."


@dataclass
class DiscourseContext:
    """Bind snapshot for one subject turn — query, intent, blocks, emergent budget."""

    query: str
    query_intent: str
    stance: str
    blocks: list[dict[str, Any]]
    focus_query: str | None = None
    concept_hints: list[str] = field(default_factory=list)
    agent_tract_profile: dict[str, Any] | None = None
    state: dict | None = None

    @classmethod
    def bind(
        cls,
        query: str,
        blocks: list[dict[str, Any]],
        *,
        query_intent: str = "general",
        stance: str = "partial",
        focus_query: str | None = None,
        agent_tract_profile: dict[str, Any] | None = None,
        concept_hints: list[str] | None = None,
        state: dict | None = None,
    ) -> DiscourseContext:
        return cls(
            query=query,
            query_intent=query_intent,
            stance=stance,
            blocks=blocks,
            focus_query=focus_query or query,
            agent_tract_profile=agent_tract_profile,
            concept_hints=list(concept_hints or []),
            state=state,
        )

    @property
    def tokens(self) -> set[str]:
        from casa.prisms.tick.discourse.render import query_tokens

        return query_tokens(self.focus_query or self.query)

    @property
    def budget(self) -> DiscourseBudget:
        return discourse_budget_from_blocks(
            self.blocks,
            stance=self.stance,
            query_intent=self.query_intent,
            state=self.state,
        )

    def partner_is_brief(self) -> bool:
        from casa.prisms.tick.discourse.render import partner_turn_is_brief

        return partner_turn_is_brief(self.query)

    def with_intent(self, query_intent: str, *, focus_query: str | None = None) -> DiscourseContext:
        return DiscourseContext(
            query=self.query,
            query_intent=query_intent,
            stance=self.stance,
            blocks=self.blocks,
            focus_query=focus_query if focus_query is not None else self.focus_query,
            agent_tract_profile=self.agent_tract_profile,
            concept_hints=list(self.concept_hints),
            state=self.state,
        )
