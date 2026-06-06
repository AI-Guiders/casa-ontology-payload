#!/usr/bin/env python3
"""Smoke: dialogue organ ADR-0045 (no full field tick required)."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.domain.dialogue_tick import process_dialogue_on_tick
from casa.domain.dialogue_turn import load_dialogue_turns
from casa.domain.subject_agency import SubjectAction, SubjectDisposition
from casa.domain.subject_mode import is_subject_mode
from casa.domain.subject_voice import compose_subject_partner_reply, verbalize_disposition
from casa.prisms.control.fpn_state import WorkingMemory, write_session_meta
from casa.prisms.control.sn_cen_runtime import TaskEmit


def _tmp_store() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="casa-dialogue-"))
    (tmp / "store_profile.json").write_text(
        json.dumps({"subject_mode": True, "display_name": "von-neumann-test"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_session_meta(tmp, {"schema_version": 2, "journal": "agent_journal.db", "wm": {}})
    return tmp


def main() -> int:
    tmp = _tmp_store()
    try:
        from casa.prisms.memory.agent_journal import append_journal_entry

        append_journal_entry(
            tmp,
            {
                "kind": "note",
                "text": "Я — von-neumann-test. Журнал Self tier на поле CASA.",
                "tags": ["bootstrap", "notebook:self"],
                "meta": {"notebook": "self"},
            },
            domain="self",
        )
        state = {"field_version": 42, "store": {"store_id": "von-neumann-test"}, "subject": {}}
        from casa.domain.subject_mode import apply_subject_profile

        apply_subject_profile(tmp, state)
        assert is_subject_mode(state, tmp)

        defer_text = verbalize_disposition(
            SubjectDisposition(SubjectAction.DEFER, "cognitive_overload", "load_governor")
        )
        refuse_text = verbalize_disposition(
            SubjectDisposition(SubjectAction.REFUSE, "explicit_refusal", "")
        )
        greeting = compose_subject_partner_reply(
            "Привет!",
            None,
            state,
            WorkingMemory(),
            store_dir=tmp,
        )
        assert "language store нет болтовни" not in greeting
        assert "помощник по русскому" not in greeting.lower()
        assert "von-neumann-test" in greeting
        assert "не paste claim" in greeting
        assert "headless worker" not in greeting

        mem_prep = {
            "goal_arbiter": {
                "subject_disposition": {
                    "action": "defer",
                    "reason": "own_practice_first",
                    "competing_source": "deliberate_practice",
                },
                "load": {"overloaded": False},
            }
        }
        rep1 = process_dialogue_on_tick(
            tmp,
            state,
            wm=WorkingMemory(),
            wm_next=WorkingMemory(tick=1, goal_id="goal.inbox.test"),
            user_query=None,
            task=None,
            mem_prep=mem_prep,
        )
        assert rep1.get("disposition_verbalized") == "defer"

        task = TaskEmit(
            intent="query",
            action="answer_from_memory",
            concepts=[],
            edges=[],
            targets=[],
            query_to_dmn=None,
            confidence=0.5,
            answer_blocks=(),
            answer_text="",
        )
        rep2 = process_dialogue_on_tick(
            tmp,
            state,
            wm=WorkingMemory(),
            wm_next=WorkingMemory(tick=2),
            user_query="Привет, как дела?",
            task=task,
            mem_prep={"goal_arbiter": {"load": {}}},
        )
        turns = load_dialogue_turns(tmp)
        subjects = [t for t in turns if t.speaker == "subject"]
        partners = [t for t in turns if t.speaker == "partner"]

        ok = bool(
            "откладываю" in defer_text.lower()
            and "отклоняю" in refuse_text.lower()
            and rep1.get("disposition_verbalized") == "defer"
            and len(partners) >= 1
            and len(subjects) >= 2
            and rep2.get("reply_text")
        )
        report = {
            "ok": ok,
            "defer_sample": defer_text[:120],
            "greeting_sample": greeting[:160],
            "turns": [t.to_dict() for t in turns],
            "rep2_last_outbound": rep2.get("last_outbound"),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
