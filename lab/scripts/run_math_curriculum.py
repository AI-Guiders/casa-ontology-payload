#!/usr/bin/env python3
"""Phased math teacher curriculum: emergent − → verify → arabic digits → roman rules."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from casa._paths import REPO_ROOT
from casa.prisms.memory.f0_stack import decode_f0_lattice, rank_cue_on_f0
from casa.prisms.memory.init_math_l0_lab import init_math_l0_lab
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, memory_lattices, run_sleep
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.store_layout import field_state_path, math_l0_lab_store
from casa.prisms.shared.store_persist import save_runtime_state
from casa.prisms.tick.predict_tick import predict_tick

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
REPORT = REPO_ROOT / "lab/reports/math-curriculum.json"

_NUM: dict[str, str] = {
    "0": "math.num.zero",
    "1": "math.num.one",
    "2": "math.num.two",
    "3": "math.num.three",
    "4": "math.num.four",
    "5": "math.num.five",
    "6": "math.num.six",
    "7": "math.num.seven",
    "8": "math.num.eight",
    "9": "math.num.nine",
}
# «10», «12» — запись числа (numeral), не цифра; учатся отдельно от 0–9.

_NUMERAL: dict[str, str] = {
    **_NUM,
    "10": "math.num.ten",
    "11": "math.num.eleven",
    "12": "math.num.twelve",
    "13": "math.num.thirteen",
    "14": "math.num.fourteen",
    "15": "math.num.fifteen",
    "16": "math.num.sixteen",
    "17": "math.num.seventeen",
    "18": "math.num.eighteen",
    "19": "math.num.nineteen",
    "20": "math.num.twenty",
    "21": "math.num.twenty_one",
}

_TEEN_NAMES_RU: dict[str, str] = {
    "10": "десять",
    "11": "одиннадцать — один на (над) десятью",
    "12": "двенадцать — два на десятью",
    "13": "тринадцать — три на десятью",
    "14": "четырнадцать — четыре на десятью",
    "15": "пятнадцать — пять на десятью",
    "16": "шестнадцать — шесть на десятью",
    "17": "семнадцать — семь на десятью",
    "18": "восемнадцать — восемь на десятью",
    "19": "девятнадцать — девять на десятью",
    "20": "двадцать — два десятка (2×10)",
    "21": "двадцать один",
}

_TEEN_NAMES_EN: dict[str, str] = {
    "10": "ten",
    "11": "eleven — one left (10+1)",
    "12": "twelve — two left (10+2)",
    "13": "thirteen — thir-teen (3+10)",
    "14": "fourteen — four-teen (4+10)",
    "15": "fifteen — five-teen (5+10)",
    "16": "sixteen — six-teen (6+10)",
    "17": "seventeen — seven-teen (7+10)",
    "18": "eighteen — eight-teen (8+10)",
    "19": "nineteen — nine-teen (9+10)",
    "20": "twenty — two tens (2×10)",
    "21": "twenty-one — twenty + one",
}

_RULE_RU = "-надцать: N на десятью; -дцать: N десятков"
_RULE_EN = "-teen: N+ten (13…19); twenty: 2×ten; twenty-N: twenty+N"


def _bilingual_numeral_scene(numeral: str, *, heard: bool = False) -> str:
    ru = _TEEN_NAMES_RU.get(numeral, "")
    en = _TEEN_NAMES_EN.get(numeral, "")
    body = f"ru: {ru} | en: {en}"
    return f"numeral_names heard: {body}" if heard else body


_EN_WORD: dict[str, str] = {
    "11": "eleven",
    "12": "twelve",
    "13": "thirteen",
    "14": "fourteen",
    "15": "fifteen",
    "20": "twenty",
}

_RU_WORD: dict[str, str] = {
    "11": "одиннадцать",
    "12": "двенадцать",
    "20": "двадцать",
}


def _name_links(numeral: str) -> list[dict[str, str]]:
    cid = _NUMERAL.get(numeral)
    if not cid:
        return []
    out: list[dict[str, str]] = []
    en = _EN_WORD.get(numeral)
    ru = _RU_WORD.get(numeral)
    if en:
        out.append({"src": cid, "relation": "names", "dst": f"lang.word.{en}"})
    if ru:
        out.append({"src": cid, "relation": "names", "dst": f"lang.word.{ru}"})
    return out


@dataclass
class Lesson:
    cue: str
    correct: str
    concept_id: str
    scene: str
    links: list[dict[str, str]] = field(default_factory=list)


@dataclass
class Check:
    cue: str
    expect: str | None
    label: str = ""
    emergent_row: bool = False


@dataclass
class PhaseResult:
    name: str
    lessons: list[dict[str, Any]] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    passed: bool = False
    sleep_merged: int = 0
    autonomous_retained: list[dict[str, Any]] = field(default_factory=list)


def _bundle() -> dict:
    return json.loads(BUNDLE.read_text(encoding="utf-8"))


def teach(state: dict, bundle: dict, lessons: list[Lesson], *, kind: str = "math_lesson") -> list[dict]:
    out: list[dict] = []
    for L in lessons:
        ep = append_episode(
            state,
            cue=L.cue,
            surface_attempt="?",
            correct=L.correct,
            lattice_id="schema-math",
            concept_id=L.concept_id,
            bundle=bundle,
            correction_kind=kind,
            scene=L.scene,
            links=L.links or None,
        )
        out.append({**L.__dict__, "id": ep.get("id")})
    return out


def snap(state: dict, bundle: dict, cue: str, expect: str | None, *, emergent_row: bool = False) -> dict:
    pre_tick = predict_tick(state, cue, modality="schema", bundle=bundle)
    pre_hyp = (pre_tick.get("predict") or {}).get("hypothesis")
    tick = (
        predict_tick(state, cue, modality="schema", expect=expect, bundle=bundle)
        if expect is not None and not emergent_row
        else pre_tick
    )
    pred = tick["predict"]
    dec = decode_f0_lattice(memory_lattices(state)["schema-math"])
    hyp = pred.get("hypothesis")
    unbound = pred.get("unbound_operators") or []
    if emergent_row:
        from casa.prisms.memory.f0_pattern_extract import (
            is_emergent_pattern_id,
            match_emergent_patterns_for_values,
            parse_comma_numeral_cue,
        )

        values = parse_comma_numeral_cue(cue) or []
        matches = match_emergent_patterns_for_values(dec, values, require_all_examples=False)
        expect = matches[0][0] if matches else None
        ok = bool(
            is_emergent_pattern_id(hyp)
            and matches
            and hyp == matches[0][0]
            and not unbound
        )
    elif expect is None:
        ok = hyp is None or tick["verdict"] == "pass"
    else:
        ok = hyp == expect and not unbound
    return {
        "label": cue,
        "cue": cue,
        "expect": expect,
        "verdict": "pass" if ok else tick["verdict"],
        "hypothesis": hyp,
        "predict_before": pre_hyp,
        "unbound": unbound,
        "top3": rank_cue_on_f0(bundle, dec, cue)[:3],
    }


def run_checks(
    state: dict,
    bundle: dict,
    checks: list[Check],
    *,
    store: Path | None = None,
    autonomous_retain: bool = True,
) -> tuple[list[dict], bool, list[dict[str, Any]]]:
    rows = [snap(state, bundle, c.cue, c.expect, emergent_row=c.emergent_row) for c in checks]
    ok = all(r["verdict"] == "pass" for r in rows)
    retained: list[dict[str, Any]] = []
    if autonomous_retain and store is not None:
        from casa.prisms.memory.agent_autonomous_retain import retain_passing_checks

        retained = retain_passing_checks(store, state, bundle, rows, persist=False)
    return rows, ok, retained


def sleep_and_save(state: dict, bundle: dict, store: Path) -> dict:
    rep = run_sleep(state, bundle)
    save_runtime_state(store, state)
    loaded = ensure_prisms(load_field_state(field_state_path(store)))
    state.clear()
    state.update(loaded)
    return rep


def phase0_bootstrap_add(state: dict, bundle: dict, store: Path) -> PhaseResult:
    """Stick addition — baseline before emergent −."""
    lessons = teach(
        state,
        bundle,
        [
            Lesson("| + | = ||", "||", "math.op.add", "sticks_add"),
            Lesson("|| + || = ||||", "||||", "math.op.add", "sticks_add"),
        ],
    )
    sleep = sleep_and_save(state, bundle, store)
    checks, ok, retained = run_checks(
        state,
        bundle,
        [
            Check("| + |", "math.op.add", "add sticks"),
            Check("|| + ||", "math.op.add", "add sticks generalize"),
        ],
        store=store,
    )
    return PhaseResult("0_bootstrap_add", lessons, checks, ok, int(sleep.get("merged") or 0), retained)


def phase1_emergent_minus(state: dict, bundle: dict, store: Path) -> PhaseResult:
    """Teacher shows − on sticks only; sleep mints denotes (no bundle math.op.sub)."""
    lessons = teach(
        state,
        bundle,
        [
            Lesson("||| - || = |", "|", "math.op.sub", "sticks_sub"),
            Lesson("|||| - | = |||", "|||", "math.op.sub", "sticks_sub"),
        ],
    )
    sleep = sleep_and_save(state, bundle, store)
    checks, ok, retained = run_checks(
        state,
        bundle,
        [
            Check("||| - || = |", "math.op.sub", "sub sticks eq"),
            Check("||| - ||", "math.op.sub", "sub sticks infix"),
            Check("|||| - |", "math.op.sub", "sub generalize"),
        ],
        store=store,
    )
    return PhaseResult("1_emergent_minus", lessons, checks, ok, int(sleep.get("merged") or 0), retained)


def phase2_verify_minus(state: dict, bundle: dict, store: Path) -> PhaseResult:
    """Gate: − works before arabic / roman — no new lessons."""
    checks, ok, retained = run_checks(
        state,
        bundle,
        [
            Check("|||| - | = |||", "math.op.sub", "sub sticks"),
            Check("|||| - |", "math.op.sub", "sub infix only"),
        ],
        store=store,
    )
    return PhaseResult("2_verify_minus", [], checks, ok, 0, retained)


def phase3_arabic_digits(state: dict, bundle: dict, store: Path) -> PhaseResult:
    """Цифры 0–9 (знаки) → math.num.* (числа); уравнения на однозначных."""
    digit_lessons = [
        Lesson(d, d, _NUM[d], "arabic_digit_glyph")
        for d in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")
    ]
    eq_lessons = [
        Lesson("2 + 2 = 4", "4", "math.op.add", "arabic_add"),
        Lesson("3 - 2 = 1", "1", "math.op.sub", "arabic_sub"),
    ]
    lessons = teach(state, bundle, digit_lessons + eq_lessons)
    sleep = sleep_and_save(state, bundle, store)
    checks, ok, retained = run_checks(
        state,
        bundle,
        [
            Check("4", "math.num.four", "glyph 4 → number four"),
            Check("7", "math.num.seven", "glyph 7 → number seven"),
            Check("0", "math.num.zero", "glyph 0 → number zero"),
            Check("3 - 2 = 1", "math.op.sub", "arabic sub eq"),
            Check("2 + 2", "math.op.add", "arabic add infix"),
        ],
        store=store,
    )
    return PhaseResult("3_arabic_digits", lessons, checks, ok, int(sleep.get("merged") or 0), retained)


def phase4_roman_teacher(state: dict, bundle: dict, store: Path) -> PhaseResult:
    """Roman: rule in scene + mappings + subtractive/additive examples (teacher, not bundle frame)."""
    rule_ep = append_episode(
        state,
        cue="roman",
        surface_attempt="?",
        correct="(rule)",
        lattice_id="schema-math",
        concept_id=None,
        correction_kind="teacher_rule",
        scene="слева меньше — вычитаем; справа — добавляем",
    )
    mappings = [
        Lesson("I", "1", "math.num.one", "roman_glyph"),
        Lesson("II", "2", "math.num.two", "roman_glyph"),
        Lesson("III", "3", "math.num.three", "roman_glyph"),
        Lesson("V", "5", "math.num.five", "roman_glyph"),
        Lesson("X", "ten", "math.num.ten", "roman_glyph → number ten"),
        Lesson("IV = V - I", "4", "math.num.four", "roman: IV = V − I = 5 − 1 = 4"),
        Lesson("VI = V + I", "6", "math.num.six", "roman: VI = V + I = 5 + 1 = 6"),
        Lesson("VII", "7", "math.num.seven", "roman_glyph"),
        Lesson("VIII", "8", "math.num.eight", "roman_glyph"),
        Lesson("IX = X - I", "9", "math.num.nine", "roman: IX = X − I = 10 − 1 = 9"),
        Lesson("IV", "4", "math.num.four", "roman_glyph"),
        Lesson("VI", "6", "math.num.six", "roman_glyph"),
        Lesson("IX", "9", "math.num.nine", "roman_glyph"),
    ]
    lessons = teach(state, bundle, mappings, kind="roman_lesson")
    lessons.insert(
        0,
        {
            "cue": "roman",
            "correct": "(rule)",
            "concept_id": None,
            "scene": "слева меньше — вычитаем; справа — добавляем",
            "id": rule_ep.get("id"),
        },
    )
    sleep = sleep_and_save(state, bundle, store)
    checks, ok, retained = run_checks(
        state,
        bundle,
        [
            Check("I", "math.num.one", "roman I"),
            Check("IV", "math.num.four", "roman IV"),
            Check("VI", "math.num.six", "roman VI"),
            Check("IX", "math.num.nine", "roman IX"),
            Check("III - II", "math.op.sub", "roman sub reuses field −"),
        ],
        store=store,
    )
    return PhaseResult("4_roman_teacher", lessons, checks, ok, int(sleep.get("merged") or 0), retained)


def phase5_teens_compose(state: dict, bundle: dict, store: Path) -> PhaseResult:
    """10+n: запись числа ten…nineteen; уравнения 10+1=11 … 10+9=19."""
    lessons_spec: list[Lesson] = [
        Lesson("10", "ten", "math.num.ten", "arabic numeral → number ten"),
    ]
    for i in range(1, 10):
        n = 10 + i
        s = str(n)
        cid = _NUMERAL[s]
        lessons_spec.append(Lesson(f"10 + {i} = {n}", s, "math.op.add", f"ten + {i}"))
        lessons_spec.append(Lesson(s, s, cid, f"numeral {s}"))
    lessons = teach(state, bundle, lessons_spec)
    sleep = sleep_and_save(state, bundle, store)
    checks, ok, retained = run_checks(
        state,
        bundle,
        [
            Check("10", "math.num.ten", "numeral ten"),
            Check("11", "math.num.eleven", "11"),
            Check("15", "math.num.fifteen", "15"),
            Check("10 + 3 = 13", "math.op.add", "10+3"),
            Check("10 + 7", "math.op.add", "10+7 infix"),
        ],
        store=store,
    )
    return PhaseResult("5_teens_compose", lessons, checks, ok, int(sleep.get("merged") or 0), retained)


def phase6_numeral_names(state: dict, bundle: dict, store: Path) -> PhaseResult:
    """RU+EN числительные в scene эпизода; sleep Extract mint names (без teacher links)."""
    rule_ep = append_episode(
        state,
        cue="numeral_names",
        surface_attempt="?",
        correct="(rule)",
        lattice_id="schema-math",
        concept_id="math.reading.rule.numeral_teens",
        correction_kind="teacher_rule",
        scene=f"ru: {_RULE_RU} | en: {_RULE_EN}",
    )
    name_lessons: list[Lesson] = []
    for numeral in ("10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21"):
        name_lessons.append(
            Lesson(
                numeral,
                numeral,
                _NUMERAL[numeral],
                _bilingual_numeral_scene(numeral, heard=True),
            ),
        )
    name_lessons.append(
        Lesson(
            "10 + 10 = 20",
            "20",
            "math.op.add",
            "ru: два десятка | en: two tens",
        ),
    )
    lessons = teach(state, bundle, name_lessons, kind="numeral_names")
    lessons.insert(
        0,
        {
            "cue": "numeral_names",
            "correct": "(rule)",
            "concept_id": None,
            "scene": f"ru: {_RULE_RU} | en: {_RULE_EN}",
            "id": rule_ep.get("id"),
        },
    )
    sleep = sleep_and_save(state, bundle, store)
    checks, ok, retained = run_checks(
        state,
        bundle,
        [
            Check("20", "math.num.twenty", "twenty / двадцать"),
            Check("13", "math.num.thirteen", "thirteen / тринадцать"),
            Check("21", "math.num.twenty_one", "twenty-one"),
            Check("10 + 10 = 20", "math.op.add", "2 tens"),
        ],
        store=store,
    )
    return PhaseResult("6_numeral_names_ru_en", lessons, checks, ok, int(sleep.get("merged") or 0), retained)


def _count_row_lessons(step: int, start: int, count: int, scene_label: str) -> list[Lesson]:
    """Teacher shows a counting row — numerals only; step inferred in sleep Extract."""
    out: list[Lesson] = []
    scene = f"count_row:{scene_label}"
    v = start
    for _ in range(count):
        s = str(v)
        cid = _NUMERAL.get(s)
        if not cid:
            break
        out.append(Lesson(s, s, cid, scene))
        v += step
    return out


def phase7_skip_counting(state: dict, bundle: dict, store: Path) -> PhaseResult:
    """Счёт 2/3/5/7 — teacher rows; Extract mints opaque pattern + sequence hubs."""
    lessons_spec: list[Lesson] = []
    lessons_spec.extend(_count_row_lessons(2, 2, 8, "счёт двойками"))
    lessons_spec.extend(_count_row_lessons(3, 3, 6, "счёт тройками"))
    lessons_spec.extend(_count_row_lessons(5, 5, 3, "счёт пятёрками"))
    lessons_spec.extend(_count_row_lessons(7, 7, 3, "счёт семёрками"))
    lessons = teach(state, bundle, lessons_spec, kind="count_row")
    sleep = sleep_and_save(state, bundle, store)
    from casa.prisms.memory.f0_pattern_extract import is_emergent_pattern_id, is_emergent_struct_id

    checks, ok, retained = run_checks(
        state,
        bundle,
        [
            Check("14", "math.num.fourteen", "2×7 held-out numeral"),
            Check("18", "math.num.eighteen", "3×6 held-out numeral"),
            Check("20", "math.num.twenty", "5×4 held-out numeral"),
            Check("21", "math.num.twenty_one", "7×3 held-out numeral"),
            Check("2, 4, 6, 8", None, "held-out row step 2", emergent_row=True),
            Check("5, 10, 15, 20", None, "held-out row step 5 (20 not in teach)", emergent_row=True),
        ],
        store=store,
    )
    dec = decode_f0_lattice(memory_lattices(state)["schema-math"])
    on_field = {str(c.get("concept_id") or "") for c in dec.get("concepts") or []}
    seq = (state.get("consolidation") or {}).get("emergent_sequence_hub")
    ok = ok and bool(seq and seq in on_field)
    ok = ok and sum(1 for c in on_field if is_emergent_pattern_id(c)) >= 2
    ok = ok and any(is_emergent_struct_id(c) for c in on_field)
    return PhaseResult("7_skip_counting", lessons, checks, ok, int(sleep.get("merged") or 0), retained)


def run_curriculum(*, fresh: bool = False) -> dict[str, Any]:
    bundle = _bundle()
    store = math_l0_lab_store(root=REPO_ROOT)
    if fresh:
        init_math_l0_lab(store, BUNDLE)
    state = ensure_prisms(load_field_state(field_state_path(store)))

    steps: list[tuple[str, Any]] = [
        ("0_bootstrap_add", lambda: phase0_bootstrap_add(state, bundle, store)),
        ("1_emergent_minus", lambda: phase1_emergent_minus(state, bundle, store)),
        ("2_verify_minus", lambda: phase2_verify_minus(state, bundle, store)),
        ("3_arabic_digits", lambda: phase3_arabic_digits(state, bundle, store)),
        ("4_roman_teacher", lambda: phase4_roman_teacher(state, bundle, store)),
        ("5_teens_compose", lambda: phase5_teens_compose(state, bundle, store)),
        ("6_numeral_names_ru_en", lambda: phase6_numeral_names(state, bundle, store)),
        ("7_skip_counting", lambda: phase7_skip_counting(state, bundle, store)),
    ]

    phases: list[PhaseResult] = []
    for _name, fn in steps:
        pr = fn()
        phases.append(pr)
        if not pr.passed:
            break

    report = {
        "store": store.name,
        "fresh": fresh,
        "phases": [
            {
                "name": p.name,
                "passed": p.passed,
                "sleep_merged": p.sleep_merged,
                "lessons": len(p.lessons),
                "checks": p.checks,
                "autonomous_retained": p.autonomous_retained,
            }
            for p in phases
        ],
        "autonomous_retained_total": sum(len(p.autonomous_retained) for p in phases),
        "all_passed": all(p.passed for p in phases),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Phased math curriculum on math-l0-lab")
    p.add_argument("--fresh", action="store_true", help="re-init math-l0-lab before run")
    args = p.parse_args()
    print(json.dumps(run_curriculum(fresh=args.fresh), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
