#!/usr/bin/env python3
"""Non-unit counting examples: skip / groups / numerals vs stick units on math-l0-lab."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from casa._paths import REPO_ROOT
from casa.prisms.memory.f0_pattern_extract import is_emergent_pattern_id, match_emergent_patterns_for_values, parse_comma_numeral_cue
from casa.prisms.memory.f0_stack import decode_f0_lattice, rank_cue_on_f0
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, memory_lattices, run_sleep
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.store_persist import save_runtime_state
from casa.prisms.shared.store_layout import field_state_path, math_l0_lab_store
from casa.prisms.tick.predict_tick import predict_tick

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
REPORT = REPO_ROOT / "lab/reports/skip-count-examples.json"


@dataclass
class Example:
    cue: str
    expect: str | None
    label: str
    kind: str  # unit | numeral | skip | group | mul | row
    emergent_row: bool = False


# Teacher rows (Extract mints pattern hubs — no designer pattern slots).
GROUP_LESSONS: list[dict[str, Any]] = [
    {"cue": "2", "correct": "2", "concept_id": "math.num.two", "scene": "count_row:seven twos"},
    {"cue": "4", "correct": "4", "concept_id": "math.num.four", "scene": "count_row:seven twos"},
    {"cue": "6", "correct": "6", "concept_id": "math.num.six", "scene": "count_row:seven twos"},
    {"cue": "7", "correct": "7", "concept_id": "math.num.seven", "scene": "count_row:two sevens"},
    {"cue": "14", "correct": "14", "concept_id": "math.num.fourteen", "scene": "count_row:two sevens"},
    {"cue": "5", "correct": "5", "concept_id": "math.num.five", "scene": "count_row:three fives"},
    {"cue": "10", "correct": "10", "concept_id": "math.num.ten", "scene": "count_row:three fives"},
    {"cue": "15", "correct": "15", "concept_id": "math.num.fifteen", "scene": "count_row:three fives"},
    {"cue": "3", "correct": "3", "concept_id": "math.num.three", "scene": "count_row:six threes"},
    {"cue": "6", "correct": "6", "concept_id": "math.num.six", "scene": "count_row:six threes"},
    {"cue": "9", "correct": "9", "concept_id": "math.num.nine", "scene": "count_row:six threes"},
    {"cue": "12", "correct": "12", "concept_id": "math.num.twelve", "scene": "count_row:six threes"},
    {"cue": "15", "correct": "15", "concept_id": "math.num.fifteen", "scene": "count_row:six threes"},
    {"cue": "18", "correct": "18", "concept_id": "math.num.eighteen", "scene": "count_row:six threes"},
]

PROBE_EXAMPLES: list[Example] = [
    # skip-count sequences (teacher phase 7): each step is the numeral concept
    Example("2", "math.num.two", "skip by 2: 2", "skip2"),
    Example("4", "math.num.four", "skip by 2: 4", "skip2"),
    Example("6", "math.num.six", "skip by 2: 6", "skip2"),
    Example("8", "math.num.eight", "skip by 2: 8", "skip2"),
    Example("3", "math.num.three", "skip by 3: 3", "skip3"),
    Example("6", "math.num.six", "skip by 3: 6", "skip3"),
    Example("9", "math.num.nine", "skip by 3: 9", "skip3"),
    Example("12", "math.num.twelve", "skip by 3: 12", "skip3"),
    Example("15", "math.num.fifteen", "skip by 3: 15", "skip3"),
    # composition: seven twos → 14 (curriculum check «2×7»)
    Example("14", "math.num.fourteen", "2×7 = 14", "mul"),
    Example("18", "math.num.eighteen", "3×6 = 18", "mul"),
    Example("21", "math.num.twenty_one", "7×3 = 21", "mul"),
    Example("2, 4, 6, 8", None, "row: count by 2", "row2", emergent_row=True),
    Example("5, 10, 15, 20", None, "row: count by 5", "row5", emergent_row=True),
    # unit sticks (separate from skip-count — still weak on long runs)
    Example("|", "math.num.one", "one stick", "unit"),
    Example("||||", "math.num.four", "four sticks", "unit"),
]


def _probe(state: dict, bundle: dict, ex: Example) -> dict[str, Any]:
    tick = predict_tick(state, ex.cue, modality="schema", expect=ex.expect, bundle=bundle)
    pred = tick.get("predict") or {}
    dec = decode_f0_lattice(memory_lattices(state)["schema-math"])
    top = rank_cue_on_f0(bundle, dec, ex.cue)[:6]
    count_mul = [(k, v) for k, v in top if is_emergent_pattern_id(k) or k == "math.op.mul"]
    hyp = pred.get("hypothesis")
    if ex.emergent_row:
        values = parse_comma_numeral_cue(ex.cue) or []
        matches = match_emergent_patterns_for_values(dec, values)
        expect = matches[0][0] if matches else None
        verdict = (
            "pass"
            if is_emergent_pattern_id(hyp) and matches and hyp == matches[0][0]
            else tick.get("verdict")
        )
    else:
        expect = ex.expect
        verdict = tick.get("verdict")
    return {
        "kind": ex.kind,
        "label": ex.label,
        "cue": ex.cue,
        "expect": expect,
        "verdict": verdict,
        "hypothesis": hyp,
        "count_or_mul_in_top": count_mul,
        "top3": top[:3],
    }


def teach_group_lessons(state: dict, bundle: dict) -> dict[str, Any]:
    eps = []
    for L in GROUP_LESSONS:
        ep = append_episode(
            state,
            cue=L["cue"],
            surface_attempt="?",
            correct=L["correct"],
            lattice_id="schema-math",
            concept_id=L["concept_id"],
            bundle=bundle,
            correction_kind="group_count",
            scene=L["scene"],
        )
        eps.append({**L, "id": ep.get("id")})
    sleep = run_sleep(state, bundle)
    return {"lessons": eps, "sleep_merged": sleep.get("merged")}


def run(*, teach: bool = False) -> dict[str, Any]:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    store = math_l0_lab_store(root=REPO_ROOT)
    state = ensure_prisms(load_field_state(field_state_path(store)))

    taught: dict[str, Any] | None = None
    if teach:
        taught = teach_group_lessons(state, bundle)
        save_runtime_state(store, state)
        state = ensure_prisms(load_field_state(field_state_path(store)))

    probes = [_probe(state, bundle, ex) for ex in PROBE_EXAMPLES]

    by_kind: dict[str, list[dict]] = {}
    for row in probes:
        by_kind.setdefault(row["kind"], []).append(row)

    summary = {
        kind: {
            "pass": sum(1 for r in rows if r["verdict"] == "pass"),
            "total": len(rows),
        }
        for kind, rows in by_kind.items()
    }

    report = {
        "store": store.name,
        "extra_teach": teach,
        "taught": taught,
        "summary_by_kind": summary,
        "probes": probes,
        "group_lessons_for_teacher": GROUP_LESSONS,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Skip / group counting examples on math-l0-lab")
    p.add_argument("--teach", action="store_true", help="Append group-count teacher episodes + sleep")
    args = p.parse_args()
    print(json.dumps(run(teach=args.teach), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
