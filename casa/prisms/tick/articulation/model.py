#!/usr/bin/env python3
"""Articulation value objects — plan and grammar atoms."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GrammarAtom:
    """Короткая норма, выжатая из claim — не весь абзац."""

    kind: str  # rule | compare | example
    headline: str
    detail: str = ""


@dataclass
class UtterancePlan:
    act: str
    intent: str
    lexemes: dict[str, str] = field(default_factory=dict)
    atoms: list[GrammarAtom] = field(default_factory=list)
    concept_ids: list[str] = field(default_factory=list)
