#!/usr/bin/env python3
"""Journal compose — same field-realize path as dialogue (ADR-0045)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.domain.subject_articulation import compose_subject_utterance
from casa.domain.dialogue_bind import SubjectDialogueContext, gather_subject_dialogue_blocks
from casa.prisms.control.fpn_state import WorkingMemory


def compose_journal_entry_text(
    cue: str,
    state: dict,
    wm: WorkingMemory,
    store_dir: Path,
    *,
    bundle: dict[str, Any] | None = None,
) -> str:
    """Free prose for entries.jsonl from field bind — not fixed templates."""
    q = (cue or "").strip()
    if not q:
        return ""
    ctx = gather_subject_dialogue_blocks(
        q,
        None,
        state,
        wm,
        store_dir,
        bundle=bundle,
        compose_mode="journal",
    )
    return compose_subject_utterance(q, ctx).strip()


def remember_journal_from_field(
    store_dir: Path,
    state: dict,
    wm: WorkingMemory,
    *,
    cue: str,
    kind: str = "note",
    tags: list[str] | None = None,
    notebook: str = "self",
    bundle: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Compose + agent_remember — journal line is spoken, not pasted."""
    from casa.prisms.memory.agent_memory_ops import agent_remember

    text = compose_journal_entry_text(cue, state, wm, store_dir, bundle=bundle)
    if not text:
        raise ValueError("journal compose produced empty text")
    return agent_remember(
        store_dir,
        state,
        {
            "kind": kind,
            "text": text,
            "tags": list(tags or ["journal:compose"]),
            "notebook": notebook,
        },
        scope=notebook if notebook != "self" else "self",
        persist=persist,
    )


def fixate_dialogue_turn_to_journal(
    store_dir: Path,
    state: dict,
    wm: WorkingMemory,
    *,
    partner_text: str,
    subject_text: str,
    bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """After a turn — journal entry from what was said, composed freely."""
    partner = (partner_text or "").strip()
    subject = (subject_text or "").strip()
    cue = (
        f"Партнёр сказал: «{partner[:500]}».\n"
        f"Я ответил: «{subject[:500]}».\n"
        "Записываю в журнал своими словами, что из этого вынес."
    )
    return remember_journal_from_field(
        store_dir,
        state,
        wm,
        cue=cue,
        kind="note",
        tags=["dialogue", "fixation"],
        notebook="self",
        bundle=bundle,
    )
