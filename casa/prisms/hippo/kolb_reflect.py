#!/usr/bin/env python3
"""Kolb phase 2: reflective observation after concrete experience."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.prisms.memory.segment import RULES, format_segment, segment_vowel_nuclei, verify_segment


def reflect_on_segment(
    hyp: dict,
    ver: dict,
    *,
    active_rules: dict[str, int] | list[str] | None = None,
) -> dict[str, Any]:
    """Turn verify output into structured reflection (RO)."""
    field_votes: dict[str, int] = {}
    if isinstance(active_rules, dict):
        field_votes = active_rules
    elif active_rules:
        field_votes = {str(r): 1 for r in active_rules}

    checks = ver.get("checks") or {}
    observations: list[str] = []
    questions: list[str] = []

    if hyp.get("intuition_source") == "field":
        comp = hyp.get("competition") or {}
        if comp:
            observations.append(
                f"На поле {comp.get('planted')} H:-гипотез: viable={comp.get('viable_count')}, "
                f"babble «{comp.get('babble_segment')}», focus «{comp.get('field_focus_segment')}» "
                f"({comp.get('winner_votes_after')} votes)."
            )
        fv = hyp.get("field_rule_votes") or {}
        top = max(fv, key=lambda k: fv[k], default=None) if fv else None
        if top:
            observations.append(f"Интуиция с поля: R:{top} ({fv.get(top, 0)} votes).")
        else:
            observations.append("На поле пока нет сильного R: — слабая врождённая эвристика.")

    if not checks.get("join_ok"):
        observations.append("Сегменты не склеиваются в исходное слово — разрез сломан.")
    if not checks.get("count_matches_vowels"):
        vc = hyp.get("vowel_count")
        sc = hyp.get("syllable_count")
        observations.append(f"Слогов {sc}, гласных {vc} — числа не совпали.")
        questions.append("Может, одна гласная = один слог?")
    if checks.get("join_ok") and checks.get("count_matches_vowels"):
        observations.append("Внутренняя проверка прошла: слоги склеиваются, гласных столько же.")

    rule_id = str(hyp.get("rule_id") or "")
    if rule_id and rule_id in RULES and rule_id not in ("rule.segment.vowel_nuclei",):
        spec = RULES[rule_id]
        observations.append(f"На поле активна эвристика: {spec.get('title')}.")
    if "rule.segment.vowel_nuclei" in field_votes:
        observations.append(
            f"Правило «гласных = слогов» на поле ({field_votes['rule.segment.vowel_nuclei']} votes)."
        )
    elif not checks.get("count_matches_vowels"):
        observations.append("Явного правила слогоделения в памяти ещё нет.")

    needs_teacher = not ver.get("ok")
    return {
        "phase": "reflective_observation",
        "observations": observations,
        "questions": questions,
        "needs_teacher": needs_teacher,
        "verify": ver,
        "attempt": format_segment(hyp.get("syllables") or []),
        "internal_ok": bool(ver.get("ok")),
    }


def reflect_on_experiment(
    word: str,
    attempt: str,
    *,
    inner_ok: bool,
    gold: str | None = None,
    matched: bool | None = None,
) -> dict[str, Any]:
    obs = [f"Слово «{word}»: попытка «{attempt}»."]
    if inner_ok:
        obs.append("Внутренняя проверка прошла — можно продолжать без внешней подсказки.")
    else:
        obs.append("Внутренняя проверка не прошла — нужен ещё цикл или услышать собеседника.")
    if gold is not None and matched is not None:
        obs.append(f"(lab eval: эталон «{gold}», совпало={matched})")
    return {
        "phase": "reflective_observation",
        "word": word,
        "observations": obs,
        "inner_ok": inner_ok,
    }
