#!/usr/bin/env python3
"""Journal and dialogue priors for passage meaning (ADR-0052 v2)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from casa.prisms.tick.passage.meaning import PropositionRow


def _split_cues(raw: str) -> list[str]:
    return [c.strip().lower() for c in re.split(r"[|,;]", raw) if c.strip()]


def _cues_all(text: str, raw: str) -> bool:
    cues = _split_cues(raw)
    if not cues:
        return True
    tl = text.lower()
    return all(c in tl for c in cues)


def _cues_any(text: str, raw: str) -> bool:
    cues = _split_cues(raw)
    if not cues:
        return True
    tl = text.lower()
    return any(c in tl for c in cues)


def _prior_context(store_dir: Path | None) -> tuple[str, set[str]]:
    """Recent dialogue + journal text and concept ids for prior boost."""
    if store_dir is None:
        return "", set()
    store_dir = store_dir.resolve()
    chunks: list[str] = []
    concept_ids: set[str] = set()

    try:
        from casa.domain.dialogue_turn import recent_dialogue

        for turn in recent_dialogue(store_dir, limit=8):
            chunks.append(turn.text)
            prov = turn.provenance if isinstance(turn.provenance, dict) else {}
            if prov.get("resolved_skill"):
                concept_ids.add(str(prov["resolved_skill"]))
            for cid in prov.get("prop_ids") or []:
                concept_ids.add(str(cid))
            for cid in prov.get("concept_hints") or []:
                concept_ids.add(str(cid))
            if prov.get("query_intent"):
                concept_ids.add(f"tract.{prov['query_intent']}")
    except Exception:
        pass

    try:
        from casa.prisms.memory.agent_journal import search_journal_entries

        for row in search_journal_entries(store_dir, domain="self", limit=12):
            text = str(row.get("text") or "")
            if text:
                chunks.append(text)
            for cid in row.get("concepts") or []:
                concept_ids.add(str(cid))
    except Exception:
        pass

    return " ".join(chunks).lower(), concept_ids


def _question_fits_frame_slots(slots: dict[str, object], ql: str) -> bool:
    """Journal prior must not revive a prop when the new question no longer fits the frame."""
    if slots.get("deny_question_any") and _cues_any(ql, str(slots["deny_question_any"])):
        return False
    if slots.get("match_question_all") and not _cues_all(ql, str(slots["match_question_all"])):
        return False
    if slots.get("match_question_any") and not _cues_any(ql, str(slots["match_question_any"])):
        return False
    return True


def apply_journal_prior(
    rows: list[PropositionRow],
    *,
    store_dir: Path | None,
    query: str,
) -> None:
    """Boost prop activation when recent dialogue/journal overlaps (ADR-0052 v2)."""
    ctx_text, concept_ids = _prior_context(store_dir)
    if not ctx_text and not concept_ids:
        return
    ql = query.lower()
    for row in rows:
        boost = 0
        slots = row.slots if isinstance(row.slots, dict) else {}
        has_q_slots = bool(slots.get("match_question_all") or slots.get("match_question_any"))
        if row.concept_id in concept_ids:
            if not has_q_slots or _question_fits_frame_slots(slots, ql):
                boost += 10
        blob = " ".join(row.slots.values()).lower()
        for cue in _split_cues(blob):
            if len(cue) > 3 and cue in ctx_text:
                boost += 4
        for cue in _split_cues(ql):
            if len(cue) > 3 and cue in ctx_text and cue in blob:
                boost += 3
        if boost:
            row.score += min(16, boost)


def dialogue_tract_prior(
    store_dir: Path | None,
    *,
    query: str,
) -> dict[str, int]:
    """Tract score nudge from recent dialogue intent / topic continuity."""
    _, concept_ids = _prior_context(store_dir)
    boosts: dict[str, int] = {}
    for cid in concept_ids:
        if cid.startswith("tract."):
            tid = cid.rsplit(".", 1)[-1]
            boosts[tid] = boosts.get(tid, 0) + 6
        if cid.startswith("ru.prop."):
            if "inference" in cid or "stance" in cid or "argument" in cid:
                boosts["discuss"] = boosts.get("discuss", 0) + 4
            if "event" in cid or "constraint.shift" in cid:
                boosts["rewrite"] = boosts.get("rewrite", 0) + 4
    ql = query.lower()
    if "привет" in ql and "tract.social" in concept_ids:
        boosts["social"] = boosts.get("social", 0) + 4
    return boosts
