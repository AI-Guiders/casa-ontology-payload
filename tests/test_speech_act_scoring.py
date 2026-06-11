#!/usr/bin/env python3
"""Speech-act bind deltas from bundle slots — not Python act tables."""

from __future__ import annotations

import json
from pathlib import Path

from casa.domain.dialogue_bind.scoring import reweight_blocks_for_reply
from casa.domain.dialogue_bind.speech_act_scoring import apply_speech_act_bind_deltas


def _design_claim(act: str) -> dict:
    raw = json.loads((Path("design") / "kb-partner-speech-acts.v1.json").read_text(encoding="utf-8"))
    for claim in raw.get("claims") or []:
        slots = claim.get("slots") or {}
        if slots.get("speech_act") == act:
            return claim
    raise KeyError(act)


def _speech_block(act: str, *, cue_score: int = 6) -> dict:
    claim = _design_claim(act)
    slots = dict(claim.get("slots") or {})
    slots["cue_score"] = cue_score
    return {
        "concept_id": str(claim.get("concept_id")),
        "text": str(claim.get("text") or act),
        "source": "speech_act",
        "score": 30,
        "slots": slots,
    }


def _block(cid: str, score: int) -> dict:
    return {"concept_id": cid, "text": cid, "source": "kb", "score": score}


def test_how_are_you_routes_to_state_hub_not_affect() -> None:
    blocks = [
        _block("ru.dialog.affect", 40),
        _block("ru.dialog.how_are_you", 38),
        _block("ru.dialog.capabilities", 40),
        _speech_block("how_are_you"),
    ]
    apply_speech_act_bind_deltas(blocks, "Как ты?", intent="social")
    by_id = {b["concept_id"]: int(b["score"]) for b in blocks}
    assert by_id["ru.dialog.how_are_you"] > by_id["ru.dialog.affect"]
    assert by_id["ru.dialog.how_are_you"] > by_id["ru.dialog.capabilities"]


def test_thanks_boosts_thanks_hub() -> None:
    blocks = [
        _block("ru.dialog.thanks", 35),
        _block("ru.dialog.affect", 45),
        _speech_block("thanks", cue_score=5),
    ]
    apply_speech_act_bind_deltas(blocks, "Спасибо", intent="social")
    by_id = {b["concept_id"]: int(b["score"]) for b in blocks}
    assert by_id["ru.dialog.thanks"] > 35
    assert by_id["ru.dialog.affect"] < 45


def test_reweight_orders_thanks_over_affect() -> None:
    blocks = [
        {
            "concept_id": "ru.dialog.affect",
            "text": "affect",
            "source": "kb",
            "score": 50,
            "slots": {"clause_1": "осторожно"},
        },
        {
            "concept_id": "ru.dialog.thanks",
            "text": "thanks",
            "source": "kb",
            "score": 44,
            "slots": {"clause_1": "пожалуйста"},
        },
        _speech_block("thanks", cue_score=6),
    ]
    reweight_blocks_for_reply(
        blocks,
        "Спасибо",
        kb_hits=[],
        intent="social",
        concept_hints=["ru.dialog.thanks"],
    )
    assert str(blocks[0].get("bind_hub") or blocks[0]["concept_id"]).startswith("ru.dialog.thanks")
