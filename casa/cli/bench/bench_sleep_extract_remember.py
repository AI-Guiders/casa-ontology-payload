#!/usr/bin/env python3
"""Minimal UC sleep tick: Extract (hippo episode) → Remember (run_sleep) → Use."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import copy
import json
import sys
import time
from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import save_field_state
from casa.prisms.tick.preflight_teacher import VALID_MODES, preflight_teacher_cue
from casa.prisms.tick.predictor import predict_t9
from casa.prisms.tick.surface_error import classify_surface_error, is_mixed_script
from casa.domain.prism_wire import prism_hippo
from casa.prisms.memory.memory_prisms import (
    append_episode,
    append_hint_episode,
    append_question_episode,
    append_rule_episode,
    ensure_prisms,
    memory_lattices,
    run_sleep,
)
from casa.prisms.memory.lexicon_shard import route_l2_lattice
from casa.prisms.shared.store_boot import boot_store


def _concept_token(concept_id: str) -> str:
    return concept_id if str(concept_id).startswith("C:") else f"C:{concept_id}"


def count_concept_copies(lattice: dict, concept_id: str) -> int:
    tok = _concept_token(concept_id)
    n = 0
    for cell in lattice.get("cells") or []:
        for t in cell:
            if str(t) == tok:
                n += 1
    return n


def fork_count_for_prefix(state: dict, prefix: str, *, top_k: int = 12) -> int:
    pfx = (prefix or "").strip()
    if not pfx:
        return 0
    pred = predict_t9(state, pfx, top_k=top_k, t9_policy="lab")  # type: ignore[arg-type]
    return len(list(pred.get("ranked") or []))


def run_sleep_tick(
    state: dict,
    *,
    cue: str,
    surface_attempt: str,
    correct: str = "",
    strength: int = 4,
    skip_nca: bool = True,
    mode: str = "teacher_rule_only",
    rule_id: str | None = None,
    rule_hint: str = "",
    expect_lang: str | None = None,
    correction_kind: str | None = None,
    scene: str | None = None,
    question: str | None = None,
    options: list[str] | None = None,
    structure_tag: str | None = None,
    min_recurrence: int = 1,
    skip_preflight: bool = False,
    top_k_fork: int = 12,
) -> dict[str, Any]:
    state = ensure_prisms(copy.deepcopy(state))
    teacher_mode = mode if mode in VALID_MODES else "teacher_rule_only"
    mixed = is_mixed_script(surface_attempt)
    rule_ep: dict[str, Any] | None = None
    ep: dict[str, Any] | None = None
    question_ep: dict[str, Any] | None = None
    hint_ep: dict[str, Any] | None = None
    extract_steps: list[dict[str, Any]] = []
    rid = str(rule_id or "script.no_mixed_alphabet")

    shard: str | None = None
    concept_id: str | None = None
    copies_before = 0
    copies_after = 0

    surface_correct = (correct or "").strip()
    fork_n = fork_count_for_prefix(state, cue, top_k=top_k_fork)

    classification = classify_surface_error(
        cue,
        surface_attempt,
        correct=surface_correct,
        scene=scene,
        fork_count=fork_n,
    )

    preflight: dict[str, Any] | None = None
    if not skip_preflight:
        preflight = preflight_teacher_cue(
            cue=cue,
            surface_attempt=surface_attempt,
            correct=surface_correct,
            mode=teacher_mode,
            correction_kind=correction_kind,
            scene=scene,
            fork_count=fork_n,
            question=question,
        )
        if not preflight["ok"]:
            return _fail(
                state,
                teacher_mode,
                cue,
                surface_attempt,
                surface_correct,
                mixed,
                "; ".join(f["message"] for f in preflight["failures"]),
                preflight=preflight,
                classification=classification,
                fork_count=fork_n,
            )

    do_surface = teacher_mode in ("surface_only", "teacher_two_phase", "teacher_contextual_surface")
    do_rule = teacher_mode in ("teacher_rule_only", "teacher_two_phase", "teacher_contextual_surface")

    ck = correction_kind or classification.get("correction_kind")

    if do_surface and surface_correct:
        shard = route_l2_lattice(state, surface_correct)
        concept_id = f"lang.word.{surface_correct.lower()}"
        copies_before = count_concept_copies(copy.deepcopy(memory_lattices(state).get(shard) or {}), concept_id)

    if teacher_mode == "teacher_lexical_ask":
        question_ep = append_question_episode(
            state,
            cue=cue,
            surface_attempt=surface_attempt,
            question=str(question or ""),
            scene=str(scene or ""),
            options=options,
            correction_kind=str(ck or "lexical_ask"),
        )
        extract_steps.append({"kind": "question", "episode_id": question_ep.get("id")})

    elif teacher_mode == "teacher_wait_prefix":
        hint_ep = append_hint_episode(
            state,
            cue=cue,
            surface_attempt=surface_attempt,
            hint=rule_hint or "Wait for full word before lexical choice.",
            correction_kind=str(ck or "wait_prefix"),
        )
        extract_steps.append({"kind": "hint", "episode_id": hint_ep.get("id")})

    elif do_rule and mixed:
        rule_ep = append_rule_episode(
            state,
            word=cue,
            attempt=surface_attempt,
            correct=surface_correct or cue,
            rule_id=rid,
            rule_hint=rule_hint,
        )
        extract_steps.append({"kind": "rule", "episode_id": rule_ep.get("id"), "rule_id": rid})

    if do_surface and surface_correct and shard and concept_id and teacher_mode != "teacher_lexical_ask":
        ep = append_episode(
            state,
            cue=cue,
            surface_attempt=surface_attempt,
            correct=surface_correct,
            lattice_id=shard,
            concept_id=concept_id,
            scene=str(scene or ""),
            correction_kind=ck,
            pending=False,
            structure_tag=structure_tag,
            min_recurrence=min_recurrence,
        )
        extract_steps.append({"kind": "surface", "episode_id": ep.get("id"), "concept_id": concept_id})

    fv_after_extract = int(state.get("field_version") or 0)

    sleep = run_sleep(
        state,
        {},
        strength=strength,
        nca_model_path=None if skip_nca else None,
        nca_lattice_id=shard or "words-ru-00",
    )
    merged = list(sleep.get("items") or [])
    rule_merged = [m for m in merged if isinstance(m, dict) and m.get("kind") == "rule"]
    surface_merged = [m for m in merged if isinstance(m, dict) and m.get("kind") == "surface"]

    if do_surface and surface_correct and shard and concept_id:
        copies_after = count_concept_copies(memory_lattices(state).get(shard) or {}, concept_id)

    strengthened = copies_after > copies_before if do_surface and surface_correct else False

    hip = prism_hippo(state)
    pending_eps = [e for e in (hip.get("episodes") or []) if not e.get("consolidated")]

    if teacher_mode == "teacher_rule_only":
        all_passed = mixed and len(rule_merged) >= 1 and any(m.get("rule_id") == rid for m in rule_merged) and len(surface_merged) == 0
    elif teacher_mode == "teacher_lexical_ask":
        all_passed = question_ep is not None and len(surface_merged) == 0 and len(pending_eps) >= 1
    elif teacher_mode == "teacher_wait_prefix":
        all_passed = hint_ep is not None and len(surface_merged) == 0 and len(rule_merged) == 0
    elif teacher_mode == "teacher_two_phase":
        all_passed = mixed and len(rule_merged) >= 1 and strengthened and len(surface_merged) >= 1
    elif teacher_mode == "surface_only":
        all_passed = strengthened and len(surface_merged) >= 1
    elif teacher_mode == "teacher_contextual_surface":
        all_passed = (
            bool(scene)
            and strengthened
            and len(surface_merged) >= 1
            and (not mixed or len(rule_merged) >= 1)
        )
    else:
        all_passed = len(rule_merged) >= 1 and strengthened and len(surface_merged) >= 1

    return {
        "schema_version": 1,
        "bench": "sleep_extract_remember",
        "mode": teacher_mode,
        "correction_kind": ck,
        "scene": scene,
        "cue": cue,
        "surface_attempt": surface_attempt,
        "correct": surface_correct or None,
        "expect_lang": expect_lang,
        "mixed_script_detected": mixed,
        "fork_count": fork_n,
        "error_axis": classification.get("axis"),
        "classification": classification,
        "preflight": preflight,
        "lattice_id": shard,
        "concept_id": concept_id,
        "rule_id": rid if do_rule and mixed else None,
        "copies_before": copies_before,
        "copies_after": copies_after,
        "field_version_after_extract": fv_after_extract,
        "field_version_after_sleep": int(state.get("field_version") or 0),
        "extract_steps": extract_steps,
        "episode_id": ep.get("id") if ep else None,
        "question_episode_id": question_ep.get("id") if question_ep else None,
        "hint_episode_id": hint_ep.get("id") if hint_ep else None,
        "rule_episode_id": rule_ep.get("id") if rule_ep else None,
        "sleep_merged_count": len(merged),
        "sleep_merged": merged,
        "rule_merged_count": len(rule_merged),
        "surface_merged_count": len(surface_merged),
        "hippo_pending_count": len(pending_eps),
        "strengthened": strengthened,
        "all_passed": all_passed,
        "state": state,
    }


def _fail(
    state: dict,
    mode: str,
    cue: str,
    surface_attempt: str,
    correct: str,
    mixed: bool,
    reason: str,
    *,
    preflight: dict[str, Any] | None = None,
    classification: dict[str, Any] | None = None,
    fork_count: int = 0,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "bench": "sleep_extract_remember",
        "mode": mode,
        "cue": cue,
        "surface_attempt": surface_attempt,
        "correct": correct,
        "mixed_script_detected": mixed,
        "fork_count": fork_count,
        "classification": classification,
        "preflight": preflight,
        "all_passed": False,
        "fail_reason": reason,
        "state": state,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Bench sleep Extract→Remember on one cue")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--cues", type=Path, default=Path("lab/exp_sleep/sleep_tick_cues.v1.json"))
    p.add_argument("--cue-index", type=int, default=0)
    p.add_argument("--write", action="store_true", help="Persist field_state.json after sleep")
    p.add_argument("--compact", action="store_true")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--skip-preflight", action="store_true")
    args = p.parse_args()

    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    if not isinstance(cues, list) or not cues:
        raise SystemExit(f"empty cues: {args.cues}")
    item = cues[min(max(0, args.cue_index), len(cues) - 1)]

    t0 = time.perf_counter()
    boot = boot_store(args.store_dir, prefer_field_state=True)
    boot_ms = round((time.perf_counter() - t0) * 1000)

    report = run_sleep_tick(
        boot["state"],
        cue=str(item.get("cue") or ""),
        surface_attempt=str(item.get("surface_attempt") or item.get("babble") or ""),
        correct=str(item.get("correct") or item.get("word") or ""),
        strength=int(item.get("strength") or 4),
        mode=str(item.get("mode") or "teacher_rule_only"),
        rule_id=item.get("rule_id"),
        rule_hint=str(item.get("rule_hint") or ""),
        expect_lang=item.get("expect_lang"),
        correction_kind=item.get("correction_kind"),
        scene=item.get("scene"),
        question=item.get("question"),
        options=item.get("options") if isinstance(item.get("options"), list) else None,
        structure_tag=item.get("structure_tag"),
        min_recurrence=int(item.get("min_recurrence") or 1),
        skip_preflight=args.skip_preflight,
    )
    if item.get("expect_preflight_fail"):
        report["all_passed"] = not report.get("all_passed") and bool(report.get("fail_reason") or (report.get("preflight") or {}).get("failures"))
    state = report.pop("state")
    report["cue_id"] = item.get("id")
    report["boot_ms"] = boot_ms
    report["store"] = str(args.store_dir)

    if args.write:
        save_field_state(args.store_dir / "field_state.json", state, compact=args.compact)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    print(
        f"\nSUMMARY: sleep_tick mode={report.get('mode')} ok={report['all_passed']} "
        f"axis={report.get('error_axis')} fork={report.get('fork_count')} "
        f"copies {report.get('copies_before')}→{report.get('copies_after')} "
        f"merged rule={report.get('rule_merged_count', 0)} surface={report.get('surface_merged_count', 0)} "
        f"pending={report.get('hippo_pending_count', 0)} boot={boot_ms}ms",
        file=sys.stderr,
    )
    raise SystemExit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
