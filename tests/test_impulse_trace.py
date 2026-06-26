"""Impulse trace recorder tests (CASA-ADR-0080)."""

from __future__ import annotations

import json
from pathlib import Path

from casa.field_bus.bus import drain_log
from casa.field_bus.events import ImpulseSummaryEvent
from casa.nervous.channels import ImpulseChannel, ImpulseOutcome
from casa.nervous.impulse import DebugLevel, ImpulseRecorder, activate_impulse_trace, read_impulse_trace


def test_impulse_off_writes_nothing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("CASA_IMPULSE_TRACE", raising=False)
    rec = ImpulseRecorder(level=DebugLevel.OFF)
    rec.begin_tick(7, tmp_path)
    with rec.channel(ImpulseChannel.PARTNER_DIALOGUE, store_dir=tmp_path) as imp:
        imp.select("dialogue_bind", selected=["ru.dialog.thanks"])
        imp.finish(ImpulseOutcome.SPOKEN)
    rec.end_tick()
    trace = tmp_path / "nervous" / "impulse_trace.jsonl"
    assert not trace.exists()


def test_impulse_summary_writes_jsonl_and_fieldbus(tmp_path: Path) -> None:
    rec = ImpulseRecorder(level=DebugLevel.SUMMARY)
    rec.begin_tick(12, tmp_path)
    with rec.channel(ImpulseChannel.CONTROL_ROUTING, store_dir=tmp_path) as imp:
        imp.route("sn_route", selected=["wake"])
        imp.select("cen_plan", selected=["answer_from_memory"])
        summary = imp.finish(ImpulseOutcome.MODE_CHANGED, zones_touched=["executive"])
    summaries = rec.end_tick()
    assert summaries and summaries[0]["channel"] == ImpulseChannel.CONTROL_ROUTING
    assert summary["winners"]

    trace = tmp_path / "nervous" / "impulse_trace.jsonl"
    assert trace.is_file()
    row = json.loads(trace.read_text(encoding="utf-8").strip())
    assert row["schema"] == "casa.impulse.v1"
    assert row["tick_id"] == 12
    assert row["channel"] == ImpulseChannel.CONTROL_ROUTING
    assert row["outcome"] == ImpulseOutcome.MODE_CHANGED
    assert any(event.get("kind") == "select" for event in row.get("events") or [])

    events = drain_log()
    assert any(isinstance(item, ImpulseSummaryEvent) for item in events)

    replay = read_impulse_trace(tmp_path, tick_id=12, channel=ImpulseChannel.CONTROL_ROUTING)
    assert replay and replay[0]["impulse_id"] == row["impulse_id"]


def test_activate_impulse_trace_sets_env_and_recorder(monkeypatch) -> None:
    monkeypatch.delenv("CASA_IMPULSE_TRACE", raising=False)
    level = activate_impulse_trace("summary", only_if_unset=False)
    assert level == DebugLevel.SUMMARY
    assert activate_impulse_trace("off", only_if_unset=True) == DebugLevel.SUMMARY


def test_bind_trace_ranked_winner_and_runners() -> None:
    from casa.domain.dialogue_bind import SubjectDialogueContext
    from casa.domain.dialogue_provenance import bind_trace, bind_trace_ranked
    from casa.prisms.control.fpn_state import WorkingMemory

    ctx = SubjectDialogueContext(
        display_name="test",
        field_version=1,
        wm=WorkingMemory(tick=1),
        blocks=[
            {
                "concept_id": "ru.dialog.thanks.a",
                "bind_hub": "ru.dialog.thanks",
                "score": 50,
                "source": "discourse",
            },
            {
                "concept_id": "ru.dialog.affect.cautious",
                "bind_hub": "ru.dialog.affect.cautious",
                "score": 40,
                "source": "affect",
            },
        ],
        query_intent="social",
    )
    winner = bind_trace(ctx)
    ranked = bind_trace_ranked(ctx, top=2)
    assert winner["winner_bind_hub"] == "ru.dialog.thanks"
    assert ranked["candidate_count"] == 2
    assert ranked["winner"]["winner_bind_hub"] == "ru.dialog.thanks"
    assert len(ranked["runner_up"]) == 1
