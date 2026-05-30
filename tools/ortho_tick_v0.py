#!/usr/bin/env python3
"""Ortho hot-path: predict → act → critic → extract on surprise (ADR-0003 §7)."""

from __future__ import annotations

from typing import Any
from ortho_field_v0 import (  # type: ignore
    PROC_LOWER,
    PROC_LOWER_WORD,
    PROC_UPPER,
    apply_from_field,
    extract_inverse_after_surprise,
    has_process,
    l3_process_ids,
)
from ortho_process_v0 import (  # type: ignore
    PROC_SENTENCE_CASE,
    apply_word_proc,
    sentence_case_word,
    upper_word,
)
from sss_vocab_v0 import norm_word  # type: ignore

from ortho_critic_v0 import critic_ortho_surface, critic_ortho_undo  # type: ignore


def expect_display_for_context(context: str, canonical: str) -> str:
    ctx = (context or "plain").strip().lower()
    if ctx == "shout":
        return upper_word(canonical)
    if ctx in ("title", "sentence"):
        return sentence_case_word(canonical)
    return canonical


def predict_ortho(
    state: dict,  # noqa: ARG001 — future: proc hints from L3 decode
    canonical: str,
    *,
    context: str = "plain",
) -> dict[str, Any]:
    """Read-mostly prediction: canonical + context → expected display."""
    canon = norm_word(canonical) or canonical
    expect = expect_display_for_context(context, canon)
    expected_proc: str | None = None
    ctx = (context or "plain").strip().lower()
    if ctx == "shout":
        expected_proc = PROC_UPPER
    elif ctx in ("title", "sentence"):
        expected_proc = PROC_SENTENCE_CASE
    return {
        "schema_version": 1,
        "modality": "ortho",
        "cue": canon,
        "canonical": canon,
        "context": ctx,
        "expect_display": expect,
        "expected_proc": expected_proc,
        "hypothesis": expect,
        "confidence": 1.0,
        "lattice_ids": ["L3_phrase", "L0_grapheme"],
        "provenance": {"engine": "ortho_context_rule"},
    }


def select_act_proc_naive(
    state: dict,
    context: str,
    *,
    base: str | None = None,
    canonical: str | None = None,
) -> str | None:
    """
    v0 learner: only Upper imprinted → over-applies in plain context.
    After Lower on field, wrong upper surface → auto inverse in plain.
    """
    ctx = (context or "plain").strip().lower()
    if ctx == "plain" and base and canonical:
        expect = expect_display_for_context(ctx, canonical)
        if base != expect and has_process(state, PROC_LOWER_WORD):
            uppered = apply_from_field(state, canonical, PROC_UPPER)
            if uppered == base:
                return PROC_LOWER_WORD
    if ctx == "shout" and has_process(state, PROC_UPPER):
        return PROC_UPPER
    if ctx in ("title", "sentence") and has_process(state, PROC_SENTENCE_CASE):
        return PROC_SENTENCE_CASE
    if ctx == "plain":
        if has_process(state, PROC_LOWER):
            return None
        if has_process(state, PROC_UPPER):
            return PROC_UPPER
    return None


def act_ortho(
    state: dict,
    base: str,
    *,
    context: str = "plain",
    act_proc: str | None = None,
    canonical: str | None = None,
) -> dict[str, Any]:
    """Apply imprinted word proc or identity."""
    proc = act_proc
    if proc is None:
        proc = select_act_proc_naive(state, context, base=base, canonical=canonical)
    if proc is None:
        surface = base
    else:
        from_field = apply_from_field(state, base, proc)
        surface = from_field if from_field is not None else apply_word_proc(base, proc)
    return {
        "base": base,
        "applied_proc": proc,
        "surface": surface,
    }


def ortho_tick(
    state: dict,
    canonical: str,
    *,
    context: str = "plain",
    input_surface: str | None = None,
    act_proc: str | None | object = ...,  # ... = auto naive
    auto_extract: bool = True,
) -> dict[str, Any]:
    """
    One hot-path tick: predict → act → critic; extract inverse on ortho surprise.
    Mutates state when extract runs.
    """
    canon = norm_word(canonical) or canonical
    base = input_surface if input_surface is not None else canon
    pred = predict_ortho(state, canon, context=context)
    expect_display = pred["expect_display"]

    if act_proc is ...:
        act = act_ortho(state, base, context=context, canonical=canon)
    else:
        act = act_ortho(state, base, context=context, act_proc=act_proc, canonical=canon)  # type: ignore[arg-type]

    surface = act.get("surface") or base
    crit = critic_ortho_surface(
        canonical=canon,
        surface=surface,
        expect_display=expect_display,
        context=context,
    )

    extract_rep: dict[str, Any] | None = None
    if (
        auto_extract
        and not crit["ok"]
        and crit.get("lexeme_ok")
        and not crit.get("display_ok")
        and act.get("applied_proc")
    ):
        extract_rep = extract_inverse_after_surprise(
            state,
            applied_proc=str(act["applied_proc"]),
            canonical=canon,
            surface_wrong=surface,
            surface_correct=expect_display,
        )

    verdict = crit["verdict"]
    if extract_rep and extract_rep.get("extracted"):
        verdict = "extracted"

    return {
        "schema_version": 1,
        "modality": "ortho",
        "canonical": canon,
        "context": context,
        "predict": pred,
        "act": act,
        "critic": crit,
        "extract": extract_rep,
        "clarify": bool(crit.get("ok") is False and not extract_rep),
        "verdict": verdict,
        "processes": sorted(l3_process_ids(state)),
    }


def simulate_ortho_plain_surprise(
    state: dict,
    *,
    word: str = "мама",
    context: str = "plain",
) -> dict[str, Any]:
    """
    Full recovery loop without explicit extract call:
    tick1 surprise+extract, tick2 undo upper surface via Lower from field.
    """
    ticks: list[dict[str, Any]] = []

    t1 = ortho_tick(state, word, context=context, auto_extract=True)
    ticks.append({"step": "surprise", **t1})
    wrong = t1["act"].get("surface")
    expect = word

    t2 = ortho_tick(
        state,
        word,
        context=context,
        input_surface=wrong,
        auto_extract=False,
    )
    undone = t2["act"].get("surface")
    undo_crit = critic_ortho_undo(before=wrong or "", after=undone or "", expect=expect)
    t2["undo_critic"] = undo_crit
    ticks.append({"step": "undo", **t2})

    surprise_ok = (
        not t1["critic"]["ok"]
        and t1["critic"].get("lexeme_ok")
        and t1.get("extract")
        and t1["extract"].get("extracted")
        and has_process(state, PROC_LOWER)
    )
    undo_ok = bool(undo_crit.get("ok"))
    return {
        "schema_version": 1,
        "word": word,
        "context": context,
        "ticks": ticks,
        "surprise_ok": surprise_ok,
        "undo_ok": undo_ok,
        "passed": surprise_ok and undo_ok,
    }
