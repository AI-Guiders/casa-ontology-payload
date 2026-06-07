#!/usr/bin/env python3
"""Journal entries composed from field — same path as dialogue."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from casa.domain.subject_journal import compose_journal_entry_text, fixate_dialogue_turn_to_journal
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.memory.agent_journal import search_journal_entries
from casa.prisms.memory.memory_prisms import ensure_prisms


def _store() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="casa-journal-compose-"))
    (tmp / "store_profile.json").write_text(
        json.dumps({"subject_mode": True, "display_name": "Нейманн"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return tmp


def test_journal_compose_from_passage_cue() -> None:
    store = _store()
    bundle = {
        "claims": [
            {
                "concept_id": "ru.meta.discourse.from_text",
                "text": "linkers",
                "slots": {"linker_2": "при этом", "linker_3": "и"},
            }
        ]
    }
    cue = (
        "В последние годы говорят о раннем старте второго языка. "
        "Одни педагоги настаивают, что мозг ребёнка гибче. "
        "Другие предупреждают о перегрузке. "
        "Автор склоняется к осторожности: сначала грамотность, потом второй язык.\n\n"
        "Записываю в журнал своими словами, что понял о позиции автора."
    )
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    text = compose_journal_entry_text(cue, state, WorkingMemory(), store, bundle=bundle)
    assert text
    assert len(text) > 24
    assert "слышу:" not in text.lower()


def test_fixate_dialogue_writes_entries_jsonl() -> None:
    store = _store()
    bundle = {
        "claims": [
            {
                "concept_id": "ru.meta.discourse.from_text",
                "text": "linkers",
                "slots": {"linker_2": "и"},
            }
        ]
    }
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    wm = WorkingMemory()
    result = fixate_dialogue_turn_to_journal(
        store,
        state,
        wm,
        partner_text="Привет!",
        subject_text="Привет.",
        bundle=bundle,
    )
    assert result.get("journal_id")
    rows = search_journal_entries(store, domain="self", limit=5)
    assert rows
    last = rows[-1]
    assert last.get("text")
    assert "проснулся" not in str(last.get("text")).lower()
