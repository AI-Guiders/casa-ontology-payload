#!/usr/bin/env python3
"""ADR-0081: materialize is a no-op — no clause_* competition at bind."""

from __future__ import annotations

from casa.domain.dialogue_bind.utterance_materialize import materialize_dialog_utterances


def _affect_hub(score: int = 50) -> dict:
    return {
        "concept_id": "ru.dialog.affect",
        "text": "Осторожный ответ про переживания в диалоге.",
        "source": "kb",
        "score": score,
        "slots": {
            "clause_1": "осторожно говорю, что чувствую в диалоге",
            "clause_2": "не знаю, совпадает ли мой опыт с человеческим",
            "clause_3": "скажу, когда уверен, а когда нет",
        },
    }


def test_materialize_does_not_split_dialog_hubs() -> None:
    blocks = [_affect_hub(), {"concept_id": "subject.dialog.self_recent", "score": 20}]
    before = [dict(b) for b in blocks]
    materialize_dialog_utterances(blocks, "я тоже не знаю", intent="social")
    assert blocks == before
    assert not any(str(b.get("bind_hub") or "") for b in blocks)
