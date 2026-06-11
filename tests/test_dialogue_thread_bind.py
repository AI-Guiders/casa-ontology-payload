#!/usr/bin/env python3
"""Dialogue thread hubs elevate bind on overlap — no compose branches."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from casa.domain.dialogue_bind.blocks import block_dict
from casa.domain.dialogue_bind.scoring import reweight_blocks_for_reply
from casa.domain.dialogue_bind.thread_scoring import dialogue_thread_hub_ids
from casa.domain.dialogue_turn import append_subject_turn


def test_dialog_hubs_from_provenance() -> None:
    store = Path(tempfile.mkdtemp(prefix="casa-thread-"))
    (store / "agent_session.json").write_text("{}\n", encoding="utf-8")
    append_subject_turn(
        store,
        "Осторожно говорю, что чувствую в диалоге.",
        kind="reply",
        provenance={
            "dialog_hubs": ["ru.dialog.affect"],
            "concept_hints": ["ru.dialog.affect"],
        },
    )
    assert dialogue_thread_hub_ids(store) == ["ru.dialog.affect"]


def test_thread_overlap_boosts_affect_on_mirror() -> None:
    store = Path(tempfile.mkdtemp(prefix="casa-thread-"))
    (store / "agent_session.json").write_text(json.dumps({"dialogue_turns": []}) + "\n", encoding="utf-8")
    append_subject_turn(
        store,
        "Осторожно говорю, что чувствую в диалоге.",
        kind="reply",
        provenance={"dialog_hubs": ["ru.dialog.affect"]},
    )
    affect = block_dict(
        "ru.dialog.affect",
        "Осторожный ответ про переживания.",
        source="kb",
        score=30,
        slots={
            "clause_1": "осторожно говорю, что чувствую в диалоге",
            "clause_2": "не знаю, совпадает ли мой опыт с человеческим",
        },
    )
    mirror = "Хорошо, я тоже не знаю, но он не обязан совпадать"
    blocks = [affect]
    reweight_blocks_for_reply(
        blocks,
        mirror,
        kb_hits=[],
        intent="social",
        concept_hints=["ru.dialog.affect"],
        store_dir=store,
    )
    assert int(affect["score"]) > 30
