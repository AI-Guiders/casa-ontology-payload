#!/usr/bin/env python3
"""Dialog hub slots compete at bind — compose only renders bind winners."""

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


def test_replayed_preamble_loses_at_bind() -> None:
    blocks = [
        _affect_hub(),
        {
            "concept_id": "subject.dialog.self_recent",
            "text": "Я недавно: «Осторожно говорю, что чувствую в диалоге.».",
            "source": "dialogue",
            "score": 20,
        },
    ]
    materialize_dialog_utterances(blocks, "я тоже не знаю", intent="social")
    winners = [b for b in blocks if str(b.get("bind_hub") or "") == "ru.dialog.affect"]
    assert winners
    top = max(winners, key=lambda b: int(b.get("score") or 0))
    assert "не знаю" in str(top.get("text") or "").lower()
    assert all("осторожно" not in str(b.get("text") or "").lower() or int(b.get("score") or 0) == 0 for b in winners)


def test_fresh_turn_keeps_open_variant() -> None:
    blocks = [_affect_hub()]
    materialize_dialog_utterances(blocks, "Как ты?", intent="social")
    winners = [b for b in blocks if str(b.get("bind_hub") or "") == "ru.dialog.affect"]
    assert any("осторожно" in str(b.get("text") or "").lower() for b in winners)
