#!/usr/bin/env python3
"""Critic v0 — validate Prediction vs expect/observation."""

from __future__ import annotations

import unicodedata
from typing import Any

from sss_segment_v0 import norm_word, verify_segment  # type: ignore


def _norm(s: str | None) -> str:
    return unicodedata.normalize("NFC", (s or "").strip().lower())


def _anchor_words(prediction: dict) -> list[str]:
    anchors = prediction.get("anchors") or []
    if anchors:
        out: list[str] = []
        for a in anchors:
            w = a.get("word") or a.get("concept_id")
            if w:
                out.append(_norm(str(w)))
        return out
    ranked = prediction.get("ranked") or []
    return [_norm(str(x[0] if isinstance(x, (list, tuple)) else x)) for x in ranked]


def critic_validate(
    prediction: dict,
    *,
    observation: str | None = None,
    expect: str | None = None,
    expect_in: list[str] | None = None,
    state: dict | None = None,  # noqa: ARG001 — v1 coherence checks
    checks: list[str] | None = None,
) -> dict[str, Any]:
    """Returns verdict pass|fail|provisional and per-check details."""
    checks = checks or ["match"]
    target = expect if expect is not None else observation
    hyp = prediction.get("hypothesis")
    modality = str(prediction.get("modality") or "")
    anchor_words = _anchor_words(prediction)
    details: list[dict[str, Any]] = []
    all_ok = True

    if "match" in checks:
        if expect_in:
            wanted = {_norm(w) for w in expect_in if w}
            found = wanted & set(anchor_words)
            ok = len(found) >= 1 and len(anchor_words) >= 2
            detail = f"anchors={anchor_words[:8]!r} expect_any={sorted(wanted)!r} found={sorted(found)!r}"
        elif target is None:
            ok = False
            detail = "no expect/observation"
        elif modality == "segment":
            ok = _norm(hyp) == _norm(target)
            detail = f"hyp={hyp!r} target={target!r}"
        elif modality in ("t9", "prefix_word", "prefix"):
            cue_len = len(_norm(str(prediction.get("cue") or "")))
            tgt_len = len(_norm(str(target)))
            if cue_len < tgt_len:
                ok = _norm(target) in anchor_words
                detail = f"anchor_set hyp={hyp!r} target={target!r} in_anchors={ok}"
            else:
                ok = _norm(hyp) == _norm(target)
                detail = f"focus hyp={hyp!r} target={target!r}"
        elif modality == "schema":
            ok = _norm(str(hyp)) == _norm(str(target))
            detail = f"schema focus concept={hyp!r} target={target!r}"
        else:
            ok = hyp == target or _norm(str(hyp)) == _norm(str(target))
            detail = f"hyp={hyp!r} target={target!r}"
        details.append({"name": "match", "pass": ok, "detail": detail})
        all_ok = all_ok and ok

    if "confidence" in checks:
        conf = float(prediction.get("confidence") or 0)
        ok = conf >= 0.2 or hyp is None
        details.append({"name": "confidence", "pass": ok, "detail": f"confidence={conf}"})
        all_ok = all_ok and ok

    if "verify_internal" in checks and modality == "segment":
        digest = prediction.get("digest") or {}
        ver = digest.get("verify") or {}
        ok = bool(ver.get("ok"))
        details.append({"name": "verify_internal", "pass": ok, "detail": ver})
        all_ok = all_ok and ok

    verdict = "pass" if all_ok else "fail"
    if prediction.get("confidence") is not None and float(prediction["confidence"]) < 0.5 and verdict == "pass":
        verdict = "provisional"

    focus = prediction.get("focus")
    if verdict in ("pass", "provisional") and focus is None and modality in ("t9", "prefix_word", "prefix"):
        cue = _norm(str(prediction.get("cue") or ""))
        tgt = _norm(str(target)) if target else ""
        if tgt and cue == tgt:
            for a in prediction.get("anchors") or []:
                if _norm(str(a.get("word") or "")) == tgt:
                    focus = a
                    break

    return {
        "schema_version": 1,
        "verdict": verdict,
        "score": float(prediction.get("confidence") or (1.0 if verdict == "pass" else 0.0)),
        "checks": details,
        "focus": focus,
        "clarify": verdict == "fail",
        "unit_candidate": prediction if verdict == "pass" else None,
    }
