#!/usr/bin/env python3
"""Critic v0 — validate Prediction vs expect/observation."""

from __future__ import annotations

import unicodedata
from typing import Any

from sss_segment_v0 import norm_word, verify_segment  # type: ignore


def _norm(s: str | None) -> str:
    return unicodedata.normalize("NFC", (s or "").strip().lower())


def critic_validate(
    prediction: dict,
    *,
    observation: str | None = None,
    expect: str | None = None,
    state: dict | None = None,  # noqa: ARG001 — v1 coherence checks
    checks: list[str] | None = None,
) -> dict[str, Any]:
    """Returns verdict pass|fail|provisional and per-check details."""
    checks = checks or ["match"]
    target = expect if expect is not None else observation
    hyp = prediction.get("hypothesis")
    modality = str(prediction.get("modality") or "")
    details: list[dict[str, Any]] = []
    all_ok = True

    if "match" in checks:
        if target is None:
            ok = False
            detail = "no expect/observation"
        elif modality == "segment":
            ok = _norm(hyp) == _norm(target)
        elif modality in ("t9", "prefix_word", "prefix"):
            ok = _norm(hyp) == _norm(target)
        else:
            ok = hyp == target or _norm(str(hyp)) == _norm(str(target))
        details.append({"name": "match", "pass": ok, "detail": f"hyp={hyp!r} target={target!r}"})
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

    return {
        "schema_version": 1,
        "verdict": verdict,
        "score": float(prediction.get("confidence") or (1.0 if verdict == "pass" else 0.0)),
        "checks": details,
        "unit_candidate": prediction if verdict == "pass" else None,
    }
