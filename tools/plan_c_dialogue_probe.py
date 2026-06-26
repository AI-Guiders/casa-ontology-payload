#!/usr/bin/env python3
"""Compose dialogue with real store continuity (Plan C validation)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.dialogue_turn import append_partner_turn, append_subject_turn
from casa.domain.subject_mode import apply_subject_profile
from casa.domain.subject_voice import compose_subject_partner_reply_with_ctx
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.sn_cen_runtime import TaskEmit
from casa.prisms.shared.store_layout import default_agent_store

TURNS = [
    "Привет!",
    "Как ты?",
    "А про переживания — ты как? Не знаешь, совпадает ли твой опыт с человеческим?",
    "Хорошо, я тоже не знаю, но он не обязан совпадать",
    "А что ты думаешь про это?",
]


def main() -> int:
    store = default_agent_store()
    state = resolve_ingest_state(store, None)
    apply_subject_profile(store, state)
    wm = WorkingMemory(tick=int(state.get("field_version") or 0))
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
    print("=== Compose with thread carry (store ring) ===\n")
    for partner in TURNS:
        append_partner_turn(store, partner, provenance={"source": "plan_c_probe"})
        ctx, reply = compose_subject_partner_reply_with_ctx(
            partner, task, state, wm, store_dir=store
        )
        prov = ctx.blocks  # noqa: debug
        from casa.domain.dialogue_provenance import meaning_provenance

        mp = meaning_provenance(ctx)
        hub = (mp.get("bind_trace") or {}).get("winner_bind_hub") or "—"
        acts = mp.get("partner_speech_acts") or []
        has_focus = any(
            str(b.get("concept_id") or "") == "dialog.context.focus_recent" for b in ctx.blocks
        )
        print(f"AGENT: {partner}")
        print(f"NEUMANN: {reply}")
        print(f"  [acts={acts}, hub={hub}, focus_recent={has_focus}]")
        print()
        append_subject_turn(store, reply, kind="reply", provenance=mp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
