#!/usr/bin/env python3
"""Unified macro-turn: script → T9 → optional ortho (ADR-0003 lab pipeline)."""

from __future__ import annotations

from typing import Any, Literal

from ambiguous_prefix_v0 import predict_ambiguous_prefix  # type: ignore
from critic_v0 import critic_validate  # type: ignore
from homoglyph_v0 import dual_script_readings  # type: ignore
from hub_neighbors_v0 import hub_neighbors  # type: ignore
from merge_preview_v0 import merge_preview_anchors, preview_words  # type: ignore
from ortho_tick_v0 import ortho_tick  # type: ignore
from predictor_v0 import predict_t9  # type: ignore
from preview_critic_v0 import apply_preview_expectations  # type: ignore
from script_detect_v0 import predict_script  # type: ignore
from surface_error_v0 import classify_surface_error  # type: ignore
from sss_vocab_v0 import norm_word  # type: ignore

ScriptMode = Literal["ambiguous", "commit"]


def _script_layer(state: dict, prefix: str, *, top_k: int) -> tuple[ScriptMode, dict[str, Any]]:
    readings = dual_script_readings(prefix)
    if len(readings) >= 2:
        return "ambiguous", predict_ambiguous_prefix(state, prefix, top_k=top_k)
    return "commit", predict_script(state, prefix)


def _t9_for_branch(state: dict, grapheme_string: str, *, top_k: int) -> dict[str, Any]:
    return predict_t9(state, grapheme_string, top_k=top_k)


def unified_tick(
    state: dict,
    prefix: str,
    *,
    context: str = "plain",
    surface_attempt: str | None = None,
    scene: str | None = None,
    expect_lang: str | None = None,
    expect_word: str | None = None,
    expect_in: list[str] | None = None,
    expect_en_in: list[str] | None = None,
    expect_ru_in: list[str] | None = None,
    expect_preview_in: list[str] | None = None,
    expect_preview_en_any: list[str] | None = None,
    expect_preview_ru_any: list[str] | None = None,
    with_ortho: bool = False,
    with_hub: bool = False,
    top_k: int = 8,
) -> dict[str, Any]:
    """
    One macro tick: script (pre-commit or commit) → T9 per branch → optional ortho/hub.
    """
    mode, script_pred = _script_layer(state, prefix, top_k=top_k)

    t9_branches: list[dict[str, Any]] = []
    if mode == "ambiguous":
        for branch in script_pred.get("branches") or []:
            gstr = str(branch.get("grapheme_string") or "")
            pred = _t9_for_branch(state, gstr, top_k=top_k)
            t9_branches.append(
                {
                    "language": branch.get("language"),
                    "script": branch.get("script"),
                    "grapheme_string": gstr,
                    "predict": pred,
                    "anchors": [a.get("word") for a in pred.get("anchors") or []][:top_k],
                }
            )
    else:
        pred = _t9_for_branch(state, prefix, top_k=top_k)
        lang = script_pred.get("hypothesis_lang")
        t9_branches.append(
            {
                "language": lang,
                "script": script_pred.get("hypothesis_script"),
                "grapheme_string": prefix,
                "predict": pred,
                "anchors": [a.get("word") for a in pred.get("anchors") or []][:top_k],
            }
        )

    preview = merge_preview_anchors(t9_branches, state=state, top_k=top_k, hub_boost=True)

    ortho: dict[str, Any] | None = None
    target = expect_word or prefix
    is_final = expect_word is not None and (
        norm_word(prefix) == norm_word(expect_word) or prefix.strip().lower() == expect_word.strip().lower()
    )
    if with_ortho and is_final:
        ortho = ortho_tick(state, target, context=context, auto_extract=False)

    hub: dict[str, Any] | None = None
    if with_hub and is_final and expect_word:
        hub = hub_neighbors(state, expect_word)

    # Critic summary
    checks: list[dict[str, Any]] = []
    ok = True

    if expect_lang is not None:
        if mode == "ambiguous":
            langs = {b.get("language") for b in t9_branches}
            lang_ok = expect_lang in langs and script_pred.get("commitment") == "ambiguous"
            if expect_lang == "en" or expect_lang == "ru":
                # commit-mode expectation on ambiguous cue → fail
                if script_pred.get("commitment") != "ambiguous":
                    lang_ok = script_pred.get("hypothesis_lang") == expect_lang
        else:
            lang_ok = script_pred.get("hypothesis_lang") == expect_lang
        checks.append({"name": "lang", "pass": lang_ok, "detail": script_pred.get("hypothesis_lang")})
        ok = ok and lang_ok

    if mode == "ambiguous" and (
        expect_en_in or expect_ru_in or expect_preview_in or expect_preview_en_any or expect_preview_ru_any
    ):
        amb_ok = script_pred.get("commitment") == "ambiguous"
        checks.append({"name": "ambiguous", "pass": amb_ok, "detail": script_pred.get("commitment")})
        ok = ok and amb_ok

    if expect_en_in or expect_ru_in:
        en_words: list[str] = []
        ru_words: list[str] = []
        for tb in t9_branches:
            if tb.get("language") == "en":
                en_words.extend(tb.get("anchors") or [])
            if tb.get("language") == "ru":
                ru_words.extend(tb.get("anchors") or [])
        if expect_en_in:
            found = set(expect_en_in) & set(en_words)
            e_ok = len(found) >= 1
            checks.append({"name": "en_branch", "pass": e_ok, "detail": {"found": sorted(found)}})
            ok = ok and e_ok
        if expect_ru_in:
            found = set(expect_ru_in) & set(ru_words)
            r_ok = len(found) >= 1
            checks.append({"name": "ru_branch", "pass": r_ok, "detail": {"found": sorted(found)}})
            ok = ok and r_ok

    preview_ok = apply_preview_expectations(
        checks,
        branches=t9_branches,
        top_k=top_k,
        state=state,
        expect_preview_in=expect_preview_in,
        expect_preview_en_any=expect_preview_en_any,
        expect_preview_ru_any=expect_preview_ru_any,
    )
    ok = ok and preview_ok

    if expect_in:
        all_anchors: list[str] = []
        for tb in t9_branches:
            all_anchors.extend(tb.get("anchors") or [])
        found = set(expect_in) & set(all_anchors)
        in_ok = len(found) >= 1
        checks.append({"name": "t9_expect_in", "pass": in_ok, "detail": {"found": sorted(found)}})
        ok = ok and in_ok
    elif expect_word and is_final:
        crit = critic_validate(
            t9_branches[0]["predict"],
            expect=expect_word,
        )
        t9_ok = crit["verdict"] in ("pass", "provisional")
        checks.append({"name": "t9_focus", "pass": t9_ok, "detail": crit})
        ok = ok and t9_ok

    if with_ortho and ortho:
        ortho_ok = ortho.get("critic", {}).get("ok", False) or ortho.get("verdict") in ("pass", "extracted")
        checks.append({"name": "ortho", "pass": ortho_ok, "detail": ortho.get("verdict")})
        ok = ok and ortho_ok

    commitment = script_pred.get("commitment") if mode == "ambiguous" else "resolved"

    teacher_routing: dict[str, Any] | None = None
    if surface_attempt:
        fork_n = 0
        for tb in t9_branches:
            fork_n = max(fork_n, len(tb.get("anchors") or []))
        teacher_routing = classify_surface_error(
            prefix,
            surface_attempt,
            correct=expect_word or "",
            scene=scene,
            fork_count=fork_n,
        )
        if teacher_routing.get("surprise") and teacher_routing.get("correction_kind"):
            checks.append(
                {
                    "name": "teacher_routing",
                    "pass": True,
                    "detail": teacher_routing,
                }
            )

    return {
        "schema_version": 1,
        "modality": "unified",
        "cue": prefix,
        "context": context,
        "surface_attempt": surface_attempt,
        "scene": scene,
        "script_mode": mode,
        "commitment": commitment,
        "script": script_pred,
        "t9_branches": t9_branches,
        "preview": preview,
        "preview_words": preview_words(preview),
        "ortho": ortho,
        "hub": hub,
        "teacher_routing": teacher_routing,
        "critic": {"verdict": "pass" if ok else "fail", "ok": ok, "checks": checks},
        "verdict": "pass" if ok else "fail",
    }


def simulate_unified_type(
    state: dict,
    word: str,
    *,
    expect_lang: str,
    context: str = "plain",
    with_ortho: bool = False,
    with_hub: bool = False,
    top_k: int = 8,
) -> dict[str, Any]:
    """Letter-by-letter unified pipeline until full word."""
    target = word.strip()
    if not target:
        return {"word": word, "trace": [], "passed": False, "reason": "empty"}

    trace: list[dict[str, Any]] = []
    all_ok = True
    for i in range(1, len(target) + 1):
        prefix = target[:i]
        is_final = i == len(target)
        tick = unified_tick(
            state,
            prefix,
            context=context,
            expect_lang=expect_lang,
            expect_word=target if is_final else None,
            with_ortho=with_ortho and is_final,
            with_hub=with_hub and is_final,
            top_k=top_k,
        )
        trace.append(tick)
        if is_final:
            all_ok = tick["verdict"] == "pass"
        elif len(prefix) >= max(1, len(target) - 1):
            merged = tick.get("preview_words") or []
            for tb in tick.get("t9_branches") or []:
                merged.extend(tb.get("anchors") or [])
            step_ok = target in merged or norm_word(target) in {norm_word(a) for a in merged}
            all_ok = all_ok and step_ok
            tick["step_ok"] = step_ok
        else:
            tick["step_ok"] = len(tick.get("t9_branches") or []) >= 1

    return {
        "schema_version": 1,
        "word": target,
        "expect_lang": expect_lang,
        "ticks": len(trace),
        "trace": trace,
        "passed": all_ok,
    }
