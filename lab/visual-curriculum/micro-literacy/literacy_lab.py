"""Совместимость: используй curriculum_lab + literacy_steps."""

from __future__ import annotations

import _ensure_paths  # noqa: F401

from curriculum_lab import CurriculumLabSession, IngestJob, ensure_repo_paths
from literacy_steps import lex_step

LiteracyLabSession = CurriculumLabSession

__all__ = [
    "CurriculumLabSession",
    "IngestJob",
    "LiteracyLabSession",
    "ensure_repo_paths",
    "lex_step",
]
