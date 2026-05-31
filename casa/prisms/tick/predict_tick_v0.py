#!/usr/bin/env python3
"""Predict tick v0 — one predict → critic step (T9 typing loop)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.prisms.tick.critic_v0 import critic_validate
from casa.prisms.tick.predictor_v0 import predict
from casa.prisms.memory.sss_segment_v0 import norm_word


def predict_tick(
    state: dict,
    cue: str,
    *,
    modality: str = "t9",
    observation: str | None = None,
    expect: str | None = None,
    expect_in: list[str] | None = None,
    bundle: dict | None = None,
    top_k: int = 8,
) -> dict[str, Any]:
    """Single hot-path tick: predict → critic. clarify=True when critic fails."""
    pred = predict(
        state,
        cue,
        modality=modality,
        bundle=bundle,
        top_k=top_k,
    )
    crit = critic_validate(
        pred,
        observation=observation,
        expect=expect,
        expect_in=expect_in,
        state=state,
    )
    return {
        "schema_version": 1,
        "cue": norm_word(cue),
        "modality": modality,
        "predict": pred,
        "critic": crit,
        "clarify": bool(crit.get("clarify")),
        "focus": crit.get("focus"),
        "verdict": crit.get("verdict"),
    }


def simulate_t9_type(
    state: dict,
    word: str,
    *,
    top_k: int = 8,
    min_prefix_for_target: int | None = None,
) -> dict[str, Any]:
    """Letter-by-letter T9: prefix grows until full word; final tick must pass."""
    target = norm_word(word)
    if not target:
        return {"word": word, "ticks": [], "passed": False, "reason": "empty word"}

    target_check_from = min_prefix_for_target
    if target_check_from is None:
        target_check_from = max(3, len(target) - 2)

    ticks: list[dict[str, Any]] = []
    all_ok = True
    for i in range(1, len(target) + 1):
        cue = target[:i]
        is_final = i == len(target)
        tick = predict_tick(
            state,
            cue,
            modality="t9",
            expect=target,
            observation=target if is_final else None,
            top_k=top_k,
        )
        anchor_words = [a.get("word") for a in tick["predict"].get("anchors") or []]
        in_anchors = target in anchor_words
        tick["target_in_anchors"] = in_anchors
        if is_final:
            tick["step_ok"] = tick["verdict"] in ("pass", "provisional")
        elif len(cue) >= len(target) - 1 or len(cue) >= target_check_from:
            tick["step_ok"] = in_anchors
        else:
            tick["step_ok"] = len(anchor_words) >= 2
        all_ok = all_ok and tick["step_ok"]
        ticks.append(tick)

    return {
        "schema_version": 1,
        "word": target,
        "ticks": len(ticks),
        "trace": ticks,
        "passed": all_ok,
        "final_focus": ticks[-1].get("focus") if ticks else None,
    }
