#!/usr/bin/env python3
"""Preflight teacher/sleep cues — enforce lab/kb/teacher_correction_cards.v1.json."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.prisms.tick.surface_error_v0 import classify_surface_error, is_mixed_script
from casa.prisms.memory.sss_vocab_v0 import norm_word

VALID_MODES = frozenset(
    {
        "surface_only",
        "teacher_rule_only",
        "teacher_two_phase",
        "teacher_contextual_surface",
        "teacher_lexical_ask",
        "teacher_wait_prefix",
    }
)

_SURFACE_STRENGTHEN_MODES = frozenset(
    {"surface_only", "teacher_two_phase", "teacher_contextual_surface"}
)


def _is_strict_prefix(shorter: str, longer: str) -> bool:
    s, lg = norm_word(shorter), norm_word(longer)
    if not s or not lg or s == lg:
        return False
    return lg.startswith(s)


def _pos_collapse_risk(attempt: str, correct: str) -> bool:
    """коровий → корова style collapse."""
    a, c = norm_word(attempt), norm_word(correct)
    if not a or not c or a == c:
        return False
    if a.endswith("ий") or a.endswith("ый") or a.endswith("ая"):
        if c.endswith("а") and not c.endswith("ий") and a[:4] == c[:4]:
            return True
    return False


def preflight_teacher_cue(
    *,
    cue: str,
    surface_attempt: str,
    correct: str = "",
    mode: str,
    correction_kind: str | None = None,
    scene: str | None = None,
    fork_count: int | None = None,
    min_fork: int = 3,
    question: str | None = None,
) -> dict[str, Any]:
    """
    Returns { ok, failures[], axis, classification, suggested_kind }.
    failures entries: { id, message } matching teacher_correction_cards ids.
    """
    failures: list[dict[str, str]] = []
    teacher_mode = mode if mode in VALID_MODES else "teacher_rule_only"
    cue_n = norm_word(cue)
    correct_n = norm_word(correct)
    attempt = (surface_attempt or "").strip()
    has_scene = bool((scene or "").strip())
    mixed = is_mixed_script(attempt)

    classification = classify_surface_error(
        cue,
        surface_attempt,
        correct=correct,
        scene=scene,
        fork_count=fork_count,
        min_fork_for_prefix=min_fork,
    )
    axis = str(classification.get("axis") or "")
    suggested_kind = classification.get("correction_kind")

    # L0: classify_error_axis — mode/kind mismatch on mixed script
    if mixed and teacher_mode in _SURFACE_STRENGTHEN_MODES and not has_scene:
        failures.append(
            {
                "id": "critic.script_before_lexical",
                "message": "mixed script: use teacher_rule_only before surface strengthen",
            }
        )

    # L0: no_oracle_on_prefix
    if (
        correct_n
        and _is_strict_prefix(cue_n, correct_n)
        and int(fork_count or 0) >= min_fork
        and teacher_mode in _SURFACE_STRENGTHEN_MODES
        and not has_scene
    ):
        failures.append(
            {
                "id": "preflight.no_oracle_on_prefix",
                "message": f"oracle lemma {correct_n!r} on prefix {cue_n!r} without scene",
            }
        )

    if (
        correct_n
        and _is_strict_prefix(cue_n, correct_n)
        and teacher_mode == "surface_only"
        and not has_scene
    ):
        failures.append(
            {
                "id": "preflight.no_oracle_on_prefix",
                "message": f"surface_only oracle on prefix {cue_n!r} → {correct_n!r}",
            }
        )

    # L0: pos_not_collapsed
    if correct_n and (_pos_collapse_risk(attempt, correct_n) or _pos_collapse_risk(cue, correct)):
        if not has_scene or correction_kind not in ("morph_surface", "lexical_ask"):
            failures.append(
                {
                    "id": "preflight.pos_not_collapsed",
                    "message": f"POS collapse risk attempt={attempt!r} correct={correct!r}",
                }
            )

    # contextual modes require scene
    if teacher_mode in ("teacher_contextual_surface", "teacher_lexical_ask") and not has_scene:
        failures.append(
            {
                "id": "critic.lexical_ask_without_scene",
                "message": f"{teacher_mode} requires scene",
            }
        )

    if teacher_mode == "teacher_contextual_surface":
        if not correct_n:
            failures.append({"id": "critic.surface_only_after_commitment", "message": "missing correct"})
        if correction_kind not in (None, "ortho_surface", "morph_surface"):
            failures.append(
                {
                    "id": "critic.surface_only_after_commitment",
                    "message": f"bad correction_kind={correction_kind!r}",
                }
            )

    if teacher_mode == "teacher_lexical_ask":
        if not (question or "").strip():
            failures.append({"id": "critic.lexical_ask_without_scene", "message": "lexical_ask requires question"})
        if correction_kind not in (None, "lexical_ask"):
            failures.append(
                {"id": "critic.lexical_ask_without_scene", "message": f"expected lexical_ask, got {correction_kind!r}"}
            )

    if teacher_mode == "teacher_rule_only" and not mixed:
        failures.append(
            {
                "id": "critic.script_before_lexical",
                "message": "teacher_rule_only expects mixed-script babble",
            }
        )

    # Explicit correction_kind vs axis
    if correction_kind and suggested_kind and correction_kind != suggested_kind:
        if not (correction_kind == "script_rule" and mixed):
            if teacher_mode not in ("teacher_contextual_surface", "teacher_lexical_ask"):
                failures.append(
                    {
                        "id": "preflight.classify_error_axis",
                        "message": f"correction_kind={correction_kind!r} vs axis→{suggested_kind!r}",
                    }
                )

    return {
        "ok": len(failures) == 0,
        "failures": failures,
        "axis": axis,
        "classification": classification,
        "suggested_kind": suggested_kind,
        "mode": teacher_mode,
    }
