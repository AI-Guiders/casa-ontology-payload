"""Subject dialogue bind — context value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from casa.prisms.control.fpn_state import WorkingMemory


@dataclass
class SubjectDialogueContext:
    display_name: str
    field_version: int
    wm: WorkingMemory
    blocks: list[dict[str, Any]] = field(default_factory=list)
    source_tags: list[str] = field(default_factory=list)
    stance: str = "partial"  # confident | partial | unknown
    query_intent: str = "general"
    resolved_skill: str = ""
    query_locales: list[str] = field(default_factory=list)
    concept_hints: list[str] = field(default_factory=list)
    agent_tract_profile: dict[str, Any] | None = None
    wm_bind: dict[str, Any] | None = None
    wm_edge_scores: dict[str, float] = field(default_factory=dict)

    @property
    def top_concept_ids(self) -> list[str]:
        out: list[str] = []
        for b in self.blocks:
            cid = str(b.get("concept_id") or "")
            if cid and cid not in out:
                out.append(cid)
        return out[:8]
