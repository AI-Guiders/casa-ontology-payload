#!/usr/bin/env python3
"""Script/lang tick: letter-by-letter L0 basin → en|ru (ADR-0003)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from script_detect_v0 import infer_language, predict_script  # type: ignore


def script_tick(
    state: dict,
    prefix: str,
    *,
    expect_lang: str | None = None,
    expect_script: str | None = None,
) -> dict[str, Any]:
    """One tick: predict script/lang from prefix; optional critic vs expect."""
    pred = predict_script(state, prefix)
    inf = infer_language(state, prefix)

    lang_ok = expect_lang is None or pred.get("hypothesis_lang") == expect_lang
    script_ok = expect_script is None or pred.get("hypothesis_script") == expect_script
    ok = lang_ok and script_ok and pred.get("hypothesis_lang") not in ("unknown", "mixed")

    checks: list[dict[str, Any]] = [
        {
            "name": "lang",
            "pass": lang_ok,
            "detail": f"hyp={pred.get('hypothesis_lang')!r} expect={expect_lang!r}",
        },
        {
            "name": "script",
            "pass": script_ok,
            "detail": f"hyp={pred.get('hypothesis_script')!r} expect={expect_script!r}",
        },
    ]

    return {
        "schema_version": 1,
        "modality": "script",
        "cue": prefix,
        "predict": pred,
        "infer": inf,
        "critic": {
            "verdict": "pass" if ok else "fail",
            "ok": ok,
            "checks": checks,
            "clarify": not ok,
        },
        "verdict": "pass" if ok else "fail",
        "hypothesis_lang": pred.get("hypothesis_lang"),
        "hypothesis_script": pred.get("hypothesis_script"),
    }


def simulate_script_prefix(
    state: dict,
    text: str,
    *,
    expect_lang: str,
    expect_script: str | None = None,
) -> dict[str, Any]:
    """Grow prefix one letter at a time; each step must keep expected lang."""
    if not text:
        return {"text": text, "ticks": [], "passed": False, "reason": "empty"}

    ticks: list[dict[str, Any]] = []
    all_ok = True
    for i in range(1, len(text) + 1):
        prefix = text[:i]
        tick = script_tick(
            state,
            prefix,
            expect_lang=expect_lang,
            expect_script=expect_script,
        )
        ticks.append(tick)
        all_ok = all_ok and tick["verdict"] == "pass"

    return {
        "schema_version": 1,
        "text": text,
        "expect_lang": expect_lang,
        "expect_script": expect_script,
        "ticks": len(ticks),
        "trace": ticks,
        "passed": all_ok,
        "first_char_lang": ticks[0].get("hypothesis_lang") if ticks else None,
    }
